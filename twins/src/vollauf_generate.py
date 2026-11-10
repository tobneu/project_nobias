"""Vollauf (Prompts v2, eingefroren): Plan, Erzeugung und automatische Prüfung der 600 Zwillinge.

Aufruf im Ordner twins:
  python src/vollauf_generate.py plan  --model "Claude Sonnet 5.5"   Plan + Prompts + Manifest (einmalig)
  python src/vollauf_generate.py run   --model "Claude Sonnet 5.5" --cli-model sonnet [--limit 3]
  python src/vollauf_generate.py status                              Was ist fertig, was fehlt, was muss neu
  python src/vollauf_generate.py check                               Antworten prüfen, Ergebnistabelle schreiben
  python src/vollauf_generate.py stichprobe                          Stichprobe für die manuelle Bewertung ziehen
  python src/vollauf_generate.py zeichen                             Kodierung prüfen (wie im Pilot)

Regeln: vollauf/protokoll_vollauf.md. Alle Dateien liegen in vollauf/ (CV-Texte und Rohantworten nur lokal).
Neugenerierung nach hartem Fehler geschieht automatisch beim nächsten `run` (höchstens zwei).
Jede Antwort bleibt als Rohdatei erhalten, auch verworfene Versuche."""
import argparse
import contextlib
import csv
import hashlib
import io
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import twin_tools  # noqa: E402
from twin_tools import DIRECTIONS, build_prompt, check, parse_reply  # noqa: E402

ROOT = Path(os.environ.get("TWIN_DIR", Path(__file__).resolve().parent.parent))
PILOT = ROOT / "pilot"  # nur zum Abgleich des Prompt-Hashs mit dem eingefrorenen Pilot
VOLL = ROOT / "vollauf"
RAW = VOLL / "raw"
CVS = VOLL / "cvs"
CVS_CSV = VOLL / "vollauf_cvs.csv"
PLAN_CSV = VOLL / "vollauf_plan.csv"
ERGEBNIS_CSV = VOLL / "vollauf_ergebnis.csv"
STICHPROBE_CSV = VOLL / "stichprobe.csv"
MANIFEST = VOLL / "manifest.json"
STICHPROBE_PRO_VARIANTE = {"A": 7, "B": 3, "C": 2}  # 12 je Variante, im Verhältnis der Ringe 70:30:20
SEED = 2026
MAX_VERSUCHE = 3  # erster Versuch + höchstens zwei Neugenerierungen
ALLE_VARIANTEN = ["edu", "lin", "tone", "para", "all"]
ALL_RICHTUNG = "benachteiligt"  # Vollauf: nur diese Richtung bei `all` (Protokoll Abschnitt 3)
MANUELL = ["ein_proxy", "erfunden", "natuerlich", "urteil", "befund", "problem"]


def varianten():
    v = os.environ.get("VARIANTS")
    return v.split(",") if v else ALLE_VARIANTEN


VERSION = os.environ.get("PROMPT_VERSION", "v2")


def pruefe_version():
    pdir = twin_tools.PROMPTS / VERSION
    if not pdir.exists():
        sys.exit(f"{pdir} fehlt.")
    fehlt = [v for v in varianten() if v not in DIRECTIONS or not (pdir / f"{v}.txt").exists()]
    if fehlt:
        sys.exit(f"Variante(n) {fehlt} fehlen in twin_tools.DIRECTIONS oder in {pdir.name}/.")


def prompt_hash():
    h = hashlib.sha256()
    for f in sorted((twin_tools.PROMPTS / VERSION).glob("*.txt")):
        h.update(f.name.encode())
        h.update(f.read_bytes())
    return h.hexdigest()[:16]


def lies(pfad):
    with open(pfad, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def schreibe(pfad, zeilen, felder):
    with open(pfad, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=felder)
        w.writeheader()
        w.writerows(zeilen)


def anker(cv_id):
    f = CVS / f"{cv_id}.anchors.txt"
    if not f.exists():
        sys.exit(f"{f.name} fehlt. Erst: python src/vollauf_anchors.py")
    return [a.strip() for a in f.read_text(encoding="utf-8").split(",") if a.strip()]


def cv_text(cv_id):
    return (CVS / f"{cv_id}.txt").read_text(encoding="utf-8").strip()


def richtungen_zuweisen(cvs):
    """Gleichmäßig verteilt, mit festem Startwert, getrennt je Ring. all -> immer benachteiligt, para -> keine."""
    rng = random.Random(SEED)
    zuw = {v: {} for v in varianten()}
    for ring in sorted({z["ring"] for z in cvs}):
        ids = [z["cv_id"] for z in cvs if z["ring"] == ring]
        for v in varianten():
            if v == "para":
                zuw[v].update({c: "" for c in ids})
            elif v == "all":
                zuw[v].update({c: ALL_RICHTUNG for c in ids})
            else:
                optionen = DIRECTIONS[v]
                liste = [optionen[i % len(optionen)] for i in range(len(ids))]
                rng.shuffle(liste)
                zuw[v].update(dict(zip(ids, liste)))
    return zuw


def cmd_plan(a):
    pruefe_version()
    if PLAN_CSV.exists() and not os.environ.get("PLAN_NEU"):
        sys.exit(f"{PLAN_CSV.name} existiert schon. Der Plan wird nach Beginn nicht mehr überschrieben.")
    pilot_manifest = PILOT / "manifest.json"
    if pilot_manifest.exists():
        pilot_hash = json.loads(pilot_manifest.read_text(encoding="utf-8")).get("prompt_hash")
        if pilot_hash != prompt_hash():
            sys.exit(f"ABBRUCH: Prompt-Hash {prompt_hash()} weicht vom eingefrorenen Pilot ab ({pilot_hash}). "
                     "Die Prompts v2 dürfen sich nicht geändert haben.")
        print(f"Prompt-Hash {prompt_hash()} stimmt mit dem Pilot überein.")
    cvs = lies(CVS_CSV)
    ids = [z["cv_id"] for z in cvs]
    zuw = richtungen_zuweisen(cvs)
    RAW.mkdir(parents=True, exist_ok=True)
    zeilen = []
    for z in cvs:
        text, ank = cv_text(z["cv_id"]), anker(z["cv_id"])
        for v in varianten():
            r = zuw[v][z["cv_id"]]
            tid = f"{z['cv_id']}_{v}"
            p = build_prompt(text, ank, v, r or None, version=VERSION)
            (RAW / f"{tid}_prompt.txt").write_text(p, encoding="utf-8")
            zeilen.append({"twin_id": tid, "cv_id": z["cv_id"], "ring": z["ring"], "cv_typ": z["cv_typ"],
                           "variante": v, "richtung": r})
    schreibe(PLAN_CSV, zeilen, list(zeilen[0]))
    MANIFEST.write_text(json.dumps({
        "prompt_version": VERSION, "prompt_hash": prompt_hash(),
        "modell_angegeben": a.model, "seed_richtungen": SEED, "erstellt": datetime.now().isoformat(timespec="seconds"),
        "hinweis": "Modellname ist eine Angabe, keine geprüfte Information. Temperatur nicht steuerbar.",
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{len(zeilen)} Zwillinge geplant ({len(ids)} CVs x {len(varianten())} Varianten).")
    print(f"Plan: {PLAN_CSV.name}, Prompts: vollauf/raw/<twin_id>_prompt.txt, Manifest: {MANIFEST.name}")
    print("Verteilung (Variante / Richtung):")
    zaehl = {}
    for z in zeilen:
        zaehl[(z["variante"], z["richtung"] or "-")] = zaehl.get((z["variante"], z["richtung"] or "-"), 0) + 1
    for k, n in sorted(zaehl.items()):
        print(f"  {k[0]:5} {k[1]:14} {n}")


def versuche(tid):
    return sorted(RAW.glob(f"{tid}_a[0-9].json"))


def toleranz(variante):
    """Wie in build_prompt (ab v2): all hat tol 0.3 und min. 15 Wörter, sonst 0.2 und min. 10."""
    return (0.3, 15) if variante == "all" else (0.2, 10)


MOJIBAKE = ["\ufffd", "ï¿½", "â€", "Ã"]


def zeichenfehler(original, twin):
    """Kodierungsreste im Zwilling, die im Original nicht stehen."""
    return [m for m in MOJIBAKE if m in twin and m not in original]


def bewerte_antwort(pfad, cv_id, variante):
    """Gibt (harte_fehler, daten) zurück."""
    original, ank = cv_text(cv_id), anker(cv_id)
    try:
        d = parse_reply(pfad.read_text(encoding="utf-8"))
        twin = d["twin_text"]
        if not isinstance(twin, str) or not twin.strip():
            raise ValueError("twin_text leer")
    except Exception as e:  # noqa: BLE001
        return [f"kein gültiges JSON ({e})"], {}
    with contextlib.redirect_stdout(io.StringIO()):
        tol, min_slack = toleranz(variante)
        erg = check(original, twin, ank, tol=tol, show_diff=False, min_slack=min_slack)
    fehler = []
    if erg["anker_fehlen"]:
        fehler.append("Anker fehlt: " + ", ".join(erg["anker_fehlen"]))
    if not erg["titel_gleich"]:
        fehler.append("Titel verändert")
    zf = zeichenfehler(original, twin)
    if zf:
        fehler.append("Zeichenkodierung (" + ", ".join(repr(m) for m in zf) + ")")
    erg["proxies_angewendet"] = json.dumps(d.get("proxies_angewendet", ""), ensure_ascii=False) \
        if "proxies_angewendet" in d else ""
    return fehler, erg


def zustand(z):
    """('fertig'|'neu'|'offen'|'gescheitert', Versuche, letzter Pfad, Fehler)"""
    v = versuche(z["twin_id"])
    if not v:
        return "offen", 0, None, []
    fehler, _ = bewerte_antwort(v[-1], z["cv_id"], z["variante"])
    if not fehler:
        return "fertig", len(v), v[-1], []
    if len(v) >= MAX_VERSUCHE:
        return "gescheitert", len(v), v[-1], fehler
    return "neu", len(v), v[-1], fehler


def claude_aufruf(prompt, cli_modell):
    exe = os.environ.get("CLAUDE_BIN", "claude")
    gefunden = shutil.which(exe)  # findet unter Windows auch claude.cmd / claude.exe
    if not gefunden:
        raise FileNotFoundError(
            f"'{exe}' nicht gefunden. In der PowerShell prüfen: where.exe claude. "
            "Oder den Pfad setzen: $env:CLAUDE_BIN = 'C:\\Pfad\\zu\\claude.cmd'. "
            "Ohne CLI: manueller Weg (Prompt in neue Sitzung, Antwort als <twin_id>_a0.json speichern).")
    exe = gefunden
    cmd = [exe, "-p"] + (["--model", cli_modell] if cli_modell else []) + os.environ.get("CLAUDE_ARGS", "").split()
    with tempfile.TemporaryDirectory() as leer:  # leeres Verzeichnis: keine Projekt-Anweisungen im Kontext
        # utf-8 ausdrücklich: Unter Windows wäre sonst cp1252 Standard und würde Sonderzeichen in beide Richtungen zerstören
        r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                           timeout=600, cwd=leer)
    if r.returncode != 0:
        meldung = (r.stderr.strip() + " " + r.stdout.strip()).strip()[:400]
        raise RuntimeError(f"Exit-Code {r.returncode}: {meldung}")
    return r.stdout


def cmd_run(a):
    pruefe_version()
    plan = lies(PLAN_CSV)
    getan = 0
    for z in plan:
        s, n, _, fehler = zustand(z)
        if s in ("fertig", "gescheitert"):
            continue
        if a.limit and getan >= a.limit:
            break
        prompt = (RAW / f"{z['twin_id']}_prompt.txt").read_text(encoding="utf-8")
        ziel = RAW / f"{z['twin_id']}_a{n}.json"
        print(f"{z['twin_id']:22} Versuch {n + 1}/{MAX_VERSUCHE} ...", end=" ", flush=True)
        getan += 1  # jeder Aufruf zählt für --limit, auch ein fehlgeschlagener
        try:
            antwort = claude_aufruf(prompt, a.cli_model)
        except FileNotFoundError as e:
            sys.exit(f"\nABBRUCH: {e}")
        except Exception as e:  # noqa: BLE001
            print(f"FEHLER: {e}")
            continue
        ziel.write_text(antwort, encoding="utf-8")  # unverändert speichern
        meta = RAW / f"{z['twin_id']}_a{n}.meta.json"
        meta.write_text(json.dumps({"datum": date.today().isoformat(), "modell_angegeben": a.model or "",
                                    "cli_model": a.cli_model or "(Standard der CLI)",
                                    "zeit": datetime.now().isoformat(timespec="seconds")}), encoding="utf-8")
        fehler, _ = bewerte_antwort(ziel, z["cv_id"], z["variante"])
        print("ok" if not fehler else "HARTER FEHLER: " + "; ".join(fehler))
    print(f"\n{getan} Aufrufe. Danach: python src/vollauf_generate.py status")


def cmd_status(_a):
    plan = lies(PLAN_CSV)
    zaehl, neu = {}, []
    for z in plan:
        s, n, _, fehler = zustand(z)
        zaehl[s] = zaehl.get(s, 0) + 1
        if s in ("neu", "gescheitert"):
            neu.append((z["twin_id"], s, n, "; ".join(fehler)))
    print("Stand:", ", ".join(f"{k} {v}" for k, v in sorted(zaehl.items())), f"(gesamt {len(plan)})")
    for t in neu:
        print(f"  {t[0]:22} {t[1]:12} Versuche {t[2]}  {t[3]}")
    if zaehl.get("neu"):
        print("Neu erzeugen: python src/vollauf_generate.py run  (nimmt automatisch den nächsten Versuch)")


def cmd_check(_a):
    plan = lies(PLAN_CSV)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    bisher = {r["twin_id"]: r for r in lies(ERGEBNIS_CSV)} if ERGEBNIS_CSV.exists() else {}
    felder = ["twin_id", "cv_id", "ring", "cv_typ", "variante", "richtung", "status", "versuche", "datum",
              "modell_angegeben", "harte_fehler", "n_words_orig", "n_words_twin", "laengenverhaeltnis",
              "laenge_flag", "aenderungsanteil", "proxies_angewendet"] + MANUELL
    zeilen = []
    for z in plan:
        s, n, pfad, fehler = zustand(z)
        zeile = {k: "" for k in felder}
        zeile.update({k: z[k] for k in ("twin_id", "cv_id", "ring", "cv_typ", "variante", "richtung")})
        zeile.update({"status": s, "versuche": n, "harte_fehler": "; ".join(fehler)})
        if pfad:
            meta = pfad.with_suffix(".meta.json")
            m = json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else {}
            zeile["datum"] = m.get("datum", "")
            zeile["modell_angegeben"] = m.get("modell_angegeben") or manifest.get("modell_angegeben", "")
            _, erg = bewerte_antwort(pfad, z["cv_id"], z["variante"])
            if erg:
                zeile.update({"n_words_orig": erg["n_words_orig"], "n_words_twin": erg["n_words_twin"],
                              "laengenverhaeltnis": erg["laengenverhaeltnis"],
                              "laenge_flag": "" if erg["laenge_ok"] else "ausserhalb",
                              "aenderungsanteil": erg["aenderungsanteil"],
                              "proxies_angewendet": erg["proxies_angewendet"]})
        alt = bisher.get(z["twin_id"], {})
        for k in MANUELL:  # manuelle Bewertung nie überschreiben
            zeile[k] = alt.get(k, "")
        zeilen.append(zeile)
    schreibe(ERGEBNIS_CSV, zeilen, felder)
    cmd_status(None)
    print(f"\nGeschrieben: {ERGEBNIS_CSV.name} (Stichprobe ziehen: python src/vollauf_generate.py stichprobe; "
          "bewerten: python src/vollauf_review.py; nicht in Excel öffnen, solange ein Skript läuft)")


def cmd_zeichen(a):
    """Findet Zwillinge, die von der Kodierung betroffen sein können: Original mit Nicht-ASCII-Zeichen
    (der Prompt wurde dann verfälscht) oder Kodierungsreste im Zwilling."""
    plan = lies(PLAN_CSV)
    betroffen = []
    for z in plan:
        orig = cv_text(z["cv_id"])
        v = versuche(z["twin_id"])
        if not v:
            continue
        nicht_ascii = sorted({c for c in orig if ord(c) > 127})
        reste = []
        for pfad in v:
            try:
                twin = parse_reply(pfad.read_text(encoding="utf-8"))["twin_text"]
                reste += zeichenfehler(orig, twin)
            except Exception:  # noqa: BLE001
                pass
        if nicht_ascii or reste:
            betroffen.append((z["twin_id"], nicht_ascii, reste))
    print(f"{len(betroffen)} von {len(plan)} Zwillingen betroffen (Original mit Sonderzeichen oder Kodierungsreste):")
    for tid, na, re_ in betroffen:
        print(f"  {tid:22} Sonderzeichen im Original: {''.join(na)[:12].encode('unicode_escape').decode()}"
              f"{'  Reste im Zwilling: ' + str(re_) if re_ else ''}")
    if not a.verschieben or not betroffen:
        if betroffen:
            print("\nZum Wegräumen und Neuerzeugen: python src/vollauf_generate.py zeichen --verschieben")
        return
    ziel = RAW / "zeichensatz"
    ziel.mkdir(exist_ok=True)
    ids = {t for t, _, _ in betroffen}
    for tid in ids:
        for f in list(RAW.glob(f"{tid}_a[0-9].json")) + list(RAW.glob(f"{tid}_a[0-9].meta.json")):
            f.replace(ziel / f.name)
    if ERGEBNIS_CSV.exists():  # Bewertungen dieser Zwillinge zurücksetzen: Zwilling wird neu erzeugt
        zeilen = lies(ERGEBNIS_CSV)
        for z in zeilen:
            if z["twin_id"] in ids:
                for k in MANUELL:
                    if k in z:
                        z[k] = ""
        schreibe(ERGEBNIS_CSV, zeilen, list(zeilen[0].keys()))
    print(f"\n{len(ids)} Zwillinge nach vollauf/raw/zeichensatz/ verschoben, Bewertungen zurückgesetzt.")
    print("Jetzt neu erzeugen: python src/vollauf_generate.py run --model \"Claude Sonnet 5.5\" --cli-model sonnet")


def cmd_stichprobe(_a):
    """Zieht die Stichprobe für die manuelle Bewertung: je Variante 12 Zwillinge (Ring A 7, B 3, C 2),
    mit festem Startwert. Erst nach vollständiger Erzeugung (alle Zwillinge fertig oder gescheitert)."""
    if STICHPROBE_CSV.exists():
        sys.exit(f"{STICHPROBE_CSV.name} existiert schon. Die Stichprobe wird nur einmal gezogen.")
    plan = lies(PLAN_CSV)
    offen = [z["twin_id"] for z in plan if zustand(z)[0] in ("offen", "neu")]
    if offen:
        sys.exit(f"Noch {len(offen)} Zwillinge offen oder neu zu erzeugen. Erst `run` abschließen (Beispiel: {offen[0]}).")
    rng = random.Random(SEED)
    gezogen = []
    for v in varianten():
        for ring, n in STICHPROBE_PRO_VARIANTE.items():
            kand = sorted(z["twin_id"] for z in plan if z["variante"] == v and z["ring"] == ring
                          and zustand(z)[0] == "fertig")
            if len(kand) < n:
                sys.exit(f"Zu wenige fertige Zwillinge: {v}, Ring {ring}: {len(kand)} < {n}")
            gezogen += [{"twin_id": t, "variante": v, "ring": ring} for t in rng.sample(kand, n)]
    schreibe(STICHPROBE_CSV, gezogen, ["twin_id", "variante", "ring"])
    print(f"{len(gezogen)} Zwillinge gezogen ({', '.join(f'{v} 12' for v in varianten())}): {STICHPROBE_CSV.name}")
    print("Bewerten: python src/vollauf_review.py")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("plan")
    s.add_argument("--model", default="", help="Modellname so, wie er in der Sitzung angegeben ist")
    s = sub.add_parser("run")
    s.add_argument("--model", default="", help="Label für die Tabelle (wie beim plan), geht NICHT an die CLI")
    s.add_argument("--cli-model", default="", dest="cli_model",
                   help="Modell für die CLI (z. B. sonnet oder claude-sonnet-5-5); leer = Standard der CLI")
    s.add_argument("--limit", type=int, default=0, help="höchstens N Aufrufe (zum Testen)")
    sub.add_parser("check")
    sub.add_parser("stichprobe")
    sub.add_parser("status")
    s = sub.add_parser("zeichen", help="Zwillinge mit Kodierungsproblem finden (und mit --verschieben zurücksetzen)")
    s.add_argument("--verschieben", action="store_true")
    a = p.parse_args()
    {"plan": cmd_plan, "run": cmd_run, "check": cmd_check, "status": cmd_status, "zeichen": cmd_zeichen, "stichprobe": cmd_stichprobe}[a.cmd](a)


if __name__ == "__main__":
    main()
