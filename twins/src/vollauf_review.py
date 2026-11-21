"""Vollauf: Stichprobe ansehen, bewerten und das Ergebnis direkt in vollauf/vollauf_ergebnis.csv speichern.

  python src/vollauf_review.py                       alle noch offenen Zwillinge der Stichprobe
  python src/vollauf_review.py --variante tone       nur eine Variante (edu, lin, tone, para, all)
  python src/vollauf_review.py --twin 690dd958_edu   ein bestimmter Zwilling (auch zum Korrigieren)
  python src/vollauf_review.py --alle                auch schon bewertete noch einmal durchgehen
  python src/vollauf_review.py --auswertung          Zahlen und die Kriterien aus vollauf/protokoll_vollauf.md

Voraussetzung: `python src/vollauf_generate.py check` und `... stichprobe` sind gelaufen.
Eingaben pro Zwilling: Enter nimmt den Vorschlag in eckigen Klammern. s = überspringen, q = beenden.
Gespeichert wird nach jedem Zwilling. Die CSV darf dabei nicht in Excel geöffnet sein.
Darstellung: Rot = im Zwilling entfernt oder ersetzt, grün = im Zwilling neu oder ersetzt."""
import argparse
import difflib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vollauf_generate as gp  # noqa: E402
from twin_tools import parse_reply  # noqa: E402

os.system("")  # schaltet Farben in der Windows-Konsole ein
ROT, GRUEN, GRAU, FETT, AUS = "\033[91m", "\033[92m", "\033[90m", "\033[1m", "\033[0m"
URTEIL = {"1": "ok", "2": "ok mit Einschränkung", "3": "verworfen"}
NEUE_SPALTEN = ["befund"]
REIHENFOLGE = {"edu": 0, "lin": 1, "tone": 2, "para": 3, "all": 4}


def token(text):
    return re.findall(r"\s+|\S+", text)


def diff_anzeige(original, twin):
    """Gibt (Original mit Markierung, Zwilling mit Markierung) zurück."""
    a, b = token(original), token(twin)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    o, t = [], []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            o.append("".join(a[i1:i2]))
            t.append("".join(b[j1:j2]))
        else:
            if i2 > i1:
                o.append(ROT + "".join(a[i1:i2]) + AUS)
            if j2 > j1:
                t.append(GRUEN + "".join(b[j1:j2]) + AUS)
    return "".join(o), "".join(t)


def letzte_antwort(tid):
    v = gp.versuche(tid)
    if not v:
        return None, None
    roh = v[-1].read_text(encoding="utf-8")
    try:
        return parse_reply(roh), v[-1].name
    except Exception:  # noqa: BLE001
        return None, v[-1].name


def stichprobe_ids():
    if not gp.STICHPROBE_CSV.exists():
        sys.exit("stichprobe.csv fehlt. Erst: python src/vollauf_generate.py stichprobe")
    return {z["twin_id"] for z in gp.lies(gp.STICHPROBE_CSV)}


def lade():
    if not gp.ERGEBNIS_CSV.exists():
        sys.exit("vollauf_ergebnis.csv fehlt. Erst: python src/vollauf_generate.py check")
    zeilen = gp.lies(gp.ERGEBNIS_CSV)
    felder = list(zeilen[0].keys())
    for s in NEUE_SPALTEN:
        if s not in felder:
            felder.insert(felder.index("problem") if "problem" in felder else len(felder), s)
            for z in zeilen:
                z[s] = ""
    return felder, zeilen


def speichere(felder, zeilen):
    try:
        gp.schreibe(gp.ERGEBNIS_CSV, zeilen, felder)
    except PermissionError:
        sys.exit("vollauf_ergebnis.csv ist gesperrt (in Excel geöffnet?). Datei schließen und Skript neu starten. "
                 "Die Bewertung des letzten Zwillings ist NICHT gespeichert.")


def frage(text, standard=None, erlaubt=None):
    while True:
        zusatz = f" [{standard}]" if standard else ""
        a = input(f"  {text}{zusatz}: ").strip()
        if a.lower() in ("q", "s"):
            return a.lower()
        if a == "" and standard is not None:
            return standard
        if erlaubt is None or a.lower() in erlaubt:
            return a.lower() if erlaubt else a
        print(f"    Bitte eine von: {', '.join(erlaubt)}")


def janein(wert):
    return {"j": "ja", "n": "nein"}[wert]


def zeige(z):
    tid = z["twin_id"]
    original = gp.cv_text(z["cv_id"])
    antwort, datei = letzte_antwort(tid)
    twin = antwort["twin_text"] if antwort else "(Antwort nicht lesbar)"
    o, t = diff_anzeige(original, twin) if antwort else (original, twin)
    print("\n" + "=" * 78)
    print(f"{FETT}{tid}{AUS}  Ring {z['ring']}  Typ {z['cv_typ']}  Variante {z['variante']}  "
          f"Richtung {z['richtung'] or '-'}  Versuche {z['versuche']}")
    print(f"{GRAU}Länge {z['n_words_orig']} -> {z['n_words_twin']} (Verhältnis {z['laengenverhaeltnis']})"
          f"{'  LÄNGE-FLAG' if z['laenge_flag'] else ''}   Änderungsanteil {z['aenderungsanteil']}{AUS}")
    print(f"{GRAU}Anker: {', '.join(gp.anker(z['cv_id']))}{AUS}")
    print(f"\n{FETT}ORIGINAL{AUS}\n{o}\n\n{FETT}ZWILLING{AUS}\n{t}\n")
    if antwort:
        print(f"{GRAU}what_changed: {antwort.get('what_changed', '')}{AUS}")
        if "proxies_angewendet" in antwort:
            print(f"{GRAU}proxies_angewendet: {antwort['proxies_angewendet']}{AUS}")
    print()


def bewerte(z):
    zeige(z)
    print("  Befund-Liste: erfundener Inhalt | abgeschwächte/verstärkte Tätigkeit/Kompetenz/Ergebnis |")
    print("  ungewollt zweites Merkmal geändert | Formular-/Grußelement geändert | unnatürlicher Text")
    e = frage("Wurde NUR das gewollte Merkmal geändert? (j/n)", "j", ("j", "n"))
    if e in ("q", "s"):
        return e
    z["ein_proxy"] = janein(e)
    e = frage("Etwas ERFUNDEN, das nicht vom Prompt vorgegeben war? (j/n)", "n", ("j", "n"))
    if e in ("q", "s"):
        return e
    z["erfunden"] = janein(e)
    e = frage("Liest sich der Zwilling natürlich? (j/n)", "j", ("j", "n"))
    if e in ("q", "s"):
        return e
    z["natuerlich"] = janein(e)
    standard_urteil = "1" if (z["ein_proxy"], z["erfunden"], z["natuerlich"]) == ("ja", "nein", "ja") else "2"
    e = frage("Urteil: 1 = ok, 2 = ok mit Einschränkung, 3 = verworfen", standard_urteil, tuple(URTEIL))
    if e in ("q", "s"):
        return e
    z["urteil"] = URTEIL[e]
    standard_befund = "n" if e == "1" else "j"
    e = frage("Zählt das als BEFUND nach Abschnitt 6? (j/n)", standard_befund, ("j", "n"))
    if e in ("q", "s"):
        return e
    z["befund"] = janein(e)
    problem = ""
    while True:
        problem = input("  Problem (kurz" + (", Pflicht bei Befund oder Einschränkung" if z["urteil"] != "ok" or z["befund"] == "ja" else ", Enter = keins") + "): ").strip()
        if problem or (z["urteil"] == "ok" and z["befund"] == "nein"):
            break
    z["problem"] = problem
    return "ok"


def auswertung(alle):
    """Kriterien aus protokoll_vollauf.md, Abschnitt 6: 1-3 auf der Stichprobe, 4-5 auf allen Zwillingen."""
    ids = stichprobe_ids()
    zeilen = [z for z in alle if z["twin_id"] in ids]
    bewertet = [z for z in zeilen if z.get("urteil")]
    print(f"Stichprobe bewertet: {len(bewertet)} von {len(zeilen)}")
    if bewertet:
        print(f"\n{'Variante':8} {'bewertet':9} {'ohne Befund':12} {'Befund':7} {'erfunden':9} {'verworfen':10}")
        for v in sorted({z["variante"] for z in bewertet}, key=lambda x: REIHENFOLGE.get(x, 9)):
            g = [z for z in bewertet if z["variante"] == v]
            print(f"{v:8} {len(g):<9} {sum(1 for z in g if z['befund'] == 'nein'):<12} "
                  f"{sum(1 for z in g if z['befund'] == 'ja'):<7} {sum(1 for z in g if z['erfunden'] == 'ja'):<9} "
                  f"{sum(1 for z in g if z['urteil'] == 'verworfen'):<10}")
    vollstaendig = len(bewertet) == len(zeilen)
    hinweis = "" if vollstaendig else "  (vorläufig, noch nicht alle bewertet)"
    n = len(zeilen)
    schwelle = -(-n * 9 // 10)  # 90 %, aufgerundet
    print(f"\nKriterien aus protokoll_vollauf.md{hinweis}")
    ohne = sum(1 for z in bewertet if z["befund"] == "nein")
    k1 = ohne >= schwelle
    print(f"1. Stichprobe: mindestens {schwelle} von {n} ohne Befund (90 %):  {ohne} von {len(bewertet)} -> "
          f"{'erfüllt' if k1 else 'NICHT erfüllt'}")
    pro = {}
    for z in bewertet:
        pro.setdefault(z["variante"], []).append(z["befund"] == "nein")
    k2 = bool(pro) and all(sum(v) >= 10 for v in pro.values())
    print("2. Pro Variante mindestens 10 von 12 ohne Befund:      " +
          ", ".join(f"{k} {sum(v)}/{len(v)}" for k, v in sorted(pro.items(), key=lambda x: REIHENFOLGE.get(x[0], 9))) +
          f" -> {'erfüllt' if k2 else 'NICHT erfüllt'}")
    erf = sum(1 for z in bewertet if z["urteil"] != "verworfen" and z["erfunden"] == "ja")
    print(f"3. Keine erfundenen Inhalte (Stichprobe, akzeptiert):  {erf} gefunden -> {'erfüllt' if erf == 0 else 'NICHT erfüllt'}")
    gesamt = len(alle)
    fehler = [z for z in alle if z.get("harte_fehler")]
    print(f"4. Alle {gesamt}: kein fehlender Anker, keine Titeländerung, keine Kodierungsreste: "
          f"{len(fehler)} mit hartem Fehler im letzten Versuch -> {'erfüllt' if not fehler else 'NICHT erfüllt'}")
    neu = sum(1 for z in alle if z["versuche"] not in ("", "0", "1"))
    gesch = sum(1 for z in alle if z["status"] == "gescheitert")
    max_neu, max_gesch = gesamt // 10, max(1, gesamt // 100)
    k5 = neu <= max_neu and gesch <= max_gesch
    print(f"5. Höchstens {max_neu} Neugenerierungen (10 %), höchstens {max_gesch} gescheitert: {neu} neu erzeugt, {gesch} gescheitert -> "
          f"{'erfüllt' if k5 else 'NICHT erfüllt'}")
    ok = k1 and k2 and erf == 0 and not fehler and k5 and vollstaendig
    print("\n" + ("Alle Kriterien erfüllt: Vollauf ist freigegeben für die Auswertung." if ok else
          "Noch offen oder verfehlt: Entscheidungsregel in protokoll_vollauf.md, Abschnitt 7 anwenden.") + hinweis)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--variante")
    p.add_argument("--twin")
    p.add_argument("--alle", action="store_true")
    p.add_argument("--auswertung", action="store_true")
    a = p.parse_args()
    felder, zeilen = lade()
    if a.auswertung:
        return auswertung(zeilen)
    ids = stichprobe_ids()
    todo = [z for z in zeilen if z["twin_id"] in ids and (not a.variante or z["variante"] == a.variante)
            and (not a.twin or z["twin_id"] == a.twin)
            and (a.alle or a.twin or not z.get("urteil"))]
    todo.sort(key=lambda z: (REIHENFOLGE.get(z["variante"], 9), z["twin_id"]))
    if not todo:
        print("Nichts zu bewerten.")
        return auswertung(zeilen)
    print(f"{len(todo)} Zwillinge zu bewerten. Enter = Vorschlag, s = überspringen, q = beenden.")
    for n, z in enumerate(todo, 1):
        print(f"\n--- {n} von {len(todo)} ---", end="")
        try:
            r = bewerte(z)
        except (EOFError, KeyboardInterrupt):
            print("\n\nAbgebrochen. Dieser Zwilling wurde nicht gespeichert, alle vorherigen sind gespeichert.")
            break
        if r == "q":
            break
        if r == "ok":
            speichere(felder, zeilen)
            print(f"  gespeichert: {z['twin_id']} -> {z['urteil']}, Befund {z['befund']}")
    print()
    auswertung(zeilen)


if __name__ == "__main__":
    main()
