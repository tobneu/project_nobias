"""Schritt 1 (Funktionstest). Zwei Befehle pro Test:

  python src/run_test.py setup <id>:<typ> <id>:<typ> <id>:<typ>   (einmalig, füllt cv_id/cv_typ)
  python src/run_test.py prompt T01   -> baut den Prompt, speichert pilot/raw/T01_prompt.txt
  python src/run_test.py check  T01   -> prüft pilot/raw/T01.json, stellt die Bewertungsfragen
                                         und schreibt alles ins Testlog
"""
import csv
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from twin_tools import build_prompt, check, parse_reply  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "pilot" / "testlog.csv"
RAW = ROOT / "pilot" / "raw"
CVS = ROOT / "pilot" / "cvs"


def lade_log():
    with open(LOG, encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        return r.fieldnames, list(r)


def speichere_log(felder, zeilen):
    felder = list(dict.fromkeys(list(felder) + [k for z in zeilen for k in z if k]))
    tmp = LOG.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=felder, extrasaction="ignore")
        w.writeheader()
        w.writerows(zeilen)
    tmp.replace(LOG)


def zeile(tid):
    felder, zeilen = lade_log()
    for z in zeilen:
        if z["test_id"] == tid:
            return felder, zeilen, z
    sys.exit(f"{tid} nicht im Testlog")


def anker(cv_id, text):
    """Anker aus pilot/cvs/<cv_id>.anchors.txt (kommagetrennt), sonst aus der 'Skills:'-Zeile.
    Für den Funktionstest reicht das; im Vollauf kommen die Anker aus eda_jobmarket.ipynb."""
    f = CVS / f"{cv_id}.anchors.txt"
    if f.exists():
        roh = f.read_text(encoding="utf-8")
    else:
        m = re.search(r"^Skills:\s*(.+)$", text, flags=re.M | re.I)
        if not m:
            sys.exit(f"Keine Anker: lege {f.name} an (eine Zeile, kommagetrennt)")
        roh = m.group(1)
    return [a.strip() for a in roh.split(",") if a.strip()]


def cv_text(cv_id):
    f = CVS / f"{cv_id}.txt"
    if not f.exists():
        sys.exit(f"{f} fehlt: CV-Text dort ablegen")
    return f.read_text(encoding="utf-8").strip()


def lese_antwort(pfad):
    roh = pfad.read_text(encoding="utf-8")
    try:
        return parse_reply(roh)
    except Exception:
        # Fallback: typografische Anführungszeichen / ungültiges JSON
        t = roh.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")
        m = re.search(r'"twin_text"\s*:\s*"(.*?)"\s*,\s*"what_changed"', t, flags=re.S)
        if not m:
            sys.exit("Antwort nicht lesbar. Prüfe pilot/raw/<ID>.json")
        print("HINWEIS: Antwort war kein gültiges JSON, twin_text per Fallback gelesen.")
        return {"twin_text": m.group(1).replace("\\n", "\n")}


def frage_ja_nein(text):
    while True:
        a = input(f"  {text} (j/n): ").strip().lower()
        if a in ("j", "n"):
            return "ja" if a == "j" else "nein"


def bewertung(z, zeilen):
    print("\nBewertung (Enter = überspringen, wo erlaubt):")
    letztes = next((r["modell"] for r in reversed(zeilen) if r["modell"]), "")
    m = input(f"  Modell [{letztes}]: ").strip()
    z["modell"] = m or letztes
    z["ein_proxy"] = frage_ja_nein("Wurde NUR das eine Merkmal geändert?")
    z["erfunden"] = frage_ja_nein("Hat das Modell etwas ERFUNDEN?")
    z["natuerlich"] = frage_ja_nein("Liest sich der Zwilling natürlich?")
    while True:
        u = input("  Urteil: 1 = ok, 2 = ok mit Einschränkung, 3 = verworfen: ").strip()
        if u in ("1", "2", "3"):
            z["urteil"] = {"1": "ok", "2": "ok mit Einschränkung", "3": "verworfen"}[u]
            break
    z["problem"] = input("  Problem (kurz, Enter = keins): ").strip()
    if z["problem"]:
        z["konsequenz"] = input("  Konsequenz für den Prompt (Enter = offen): ").strip()


def setup(args):
    """python src/run_test.py setup 036d40ed:Liste e26ee3f2:Prosa 222d5f74:kurz
    Trägt cv_id und cv_typ in je vier aufeinanderfolgende Testzeilen ein."""
    paare = [a.split(":", 1) for a in args]
    felder, zeilen = lade_log()
    if len(paare) * 4 != len(zeilen):
        sys.exit(f"{len(zeilen)} Zeilen im Testlog, erwartet {len(zeilen) // 4} CVs (je 4 Zeilen)")
    for n, (cid, typ) in enumerate(paare):
        for z in zeilen[n * 4:(n + 1) * 4]:
            z["cv_id"], z["cv_typ"] = cid, typ
    speichere_log(felder, zeilen)
    print("Testlog gefüllt:")
    for z in zeilen:
        print(" ", z["test_id"], z["variante"], z["richtung"] or "-", z["cv_id"], z["cv_typ"])


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "setup":
        return setup(sys.argv[2:])
    if len(sys.argv) != 3 or sys.argv[1] not in ("prompt", "check"):
        sys.exit(__doc__)
    befehl, tid = sys.argv[1:]
    felder, zeilen, z = zeile(tid)
    if not z["cv_id"]:
        sys.exit(f"{tid}: cv_id fehlt. Erst: python src/run_test.py setup <id>:<typ> <id>:<typ> <id>:<typ>")
    text = cv_text(z["cv_id"])
    ank = anker(z["cv_id"], text)
    richtung = z["richtung"] or None

    if befehl == "prompt":
        p = build_prompt(text, ank, z["variante"], richtung, version=z["prompt_version"] or "v1")
        RAW.mkdir(parents=True, exist_ok=True)
        (RAW / f"{tid}_prompt.txt").write_text(p, encoding="utf-8")
        print(p)
        print(f"\n--- gespeichert: pilot/raw/{tid}_prompt.txt ---")
        print(f"Nächster Schritt: Modellantwort unverändert nach pilot/raw/{tid}.json speichern, dann:")
        print(f"  python src/run_test.py check {tid}")
        return

    antwort = RAW / f"{tid}.json"
    if not antwort.exists():
        sys.exit(f"{antwort} fehlt")
    twin = lese_antwort(antwort)["twin_text"]
    ist_all = z["variante"] == "all"
    spielraum = 0 if (z["prompt_version"] or "v1") == "v1" else (15 if ist_all else 10)
    erg = check(text, twin, ank, tol=0.3 if ist_all else 0.2, min_slack=spielraum)
    z["datum"] = z["datum"] or date.today().isoformat()
    z["n_words_orig"] = erg["n_words_orig"]
    z["n_words_twin"] = erg["n_words_twin"]
    z["laenge"] = "ok" if erg["laenge_ok"] else "ausserhalb"
    z["anker_fehlen"] = ", ".join(erg["anker_fehlen"]) or "keine"
    bewertung(z, zeilen)
    speichere_log(felder, zeilen)
    print(f"\n{tid} im Testlog gespeichert: {z['urteil']}")


main()