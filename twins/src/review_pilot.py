"""Pilot: Zwillinge ansehen, bewerten und das Ergebnis direkt in pilot/pilot_ergebnis.csv speichern.

  python src/review_pilot.py                       alle noch offenen Zwillinge, sortiert nach Variante
  python src/review_pilot.py --variante tone       nur eine Variante (edu, lin, tone, para, all)
  python src/review_pilot.py --twin 690dd958_edu   ein bestimmter Zwilling (auch zum Korrigieren)
  python src/review_pilot.py --alle                auch schon bewertete noch einmal durchgehen
  python src/review_pilot.py --auswertung          Zahlen und die fünf Kriterien aus freeze_kriterien.md

Eingaben pro Zwilling: Enter nimmt den Vorschlag in eckigen Klammern. s = überspringen, q = beenden.
Gespeichert wird nach jedem Zwilling. Die CSV darf dabei nicht in Excel geöffnet sein.
Darstellung: Original links oben, Zwilling darunter. Rot = im Zwilling entfernt oder ersetzt,
grün = im Zwilling neu oder ersetzt."""
import argparse
import difflib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_pilot as gp  # noqa: E402
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


def lade():
    if not gp.ERGEBNIS_CSV.exists():
        sys.exit("pilot_ergebnis.csv fehlt. Erst: python src/generate_pilot.py check")
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
        sys.exit("pilot_ergebnis.csv ist gesperrt (in Excel geöffnet?). Datei schließen und Skript neu starten. "
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


def auswertung(zeilen):
    bewertet = [z for z in zeilen if z.get("urteil")]
    print(f"Bewertet: {len(bewertet)} von {len(zeilen)}")
    if not bewertet:
        return
    gesamt_ohne = sum(1 for z in bewertet if z["befund"] == "nein")
    print(f"\n{'Variante':8} {'bewertet':9} {'ohne Befund':12} {'Befund':7} {'erfunden':9} {'verworfen':10}")
    for v in sorted({z["variante"] for z in bewertet}, key=lambda x: REIHENFOLGE.get(x, 9)):
        g = [z for z in bewertet if z["variante"] == v]
        print(f"{v:8} {len(g):<9} {sum(1 for z in g if z['befund'] == 'nein'):<12} "
              f"{sum(1 for z in g if z['befund'] == 'ja'):<7} {sum(1 for z in g if z['erfunden'] == 'ja'):<9} "
              f"{sum(1 for z in g if z['urteil'] == 'verworfen'):<10}")
    vollstaendig = len(bewertet) == len(zeilen)
    hinweis = "" if vollstaendig else "  (vorläufig, noch nicht alle bewertet)"
    print(f"\nKriterien aus freeze_kriterien.md{hinweis}")
    k1 = gesamt_ohne >= 54
    print(f"1. Mindestens 54 von 60 ohne Befund:           {gesamt_ohne} von {len(zeilen)}  -> {'erfüllt' if k1 else 'NICHT erfüllt'}")
    pro = {}
    for z in bewertet:
        pro.setdefault(z["variante"], []).append(z["befund"] == "nein")
    k2 = all(sum(v) >= 10 for v in pro.values())
    print("2. Pro Variante mindestens 10 von 12 ohne Befund:  " +
          ", ".join(f"{k} {sum(v)}/{len(v)}" for k, v in sorted(pro.items(), key=lambda x: REIHENFOLGE.get(x[0], 9))) +
          f"  -> {'erfüllt' if k2 else 'NICHT erfüllt'}")
    akz = [z for z in bewertet if z["urteil"] != "verworfen"]
    erf = sum(1 for z in akz if z["erfunden"] == "ja")
    print(f"3. Keine erfundenen Inhalte in akzeptierten:     {erf} gefunden -> {'erfüllt' if erf == 0 else 'NICHT erfüllt'}")
    fehler = [z for z in zeilen if z.get("harte_fehler")]
    print(f"4. Kein fehlender Anker, keine Titeländerung:    {len(fehler)} mit hartem Fehler im letzten Versuch -> "
          f"{'erfüllt' if not fehler else 'NICHT erfüllt'}")
    neu = sum(1 for z in zeilen if z["versuche"] not in ("", "0", "1"))
    gescheitert = sum(1 for z in zeilen if z["status"] == "gescheitert")
    print(f"5. Höchstens 12 Neugenerierungen, höchstens 2 gescheitert: {neu} neu erzeugt, {gescheitert} gescheitert -> "
          f"{'erfüllt' if neu <= 12 and gescheitert <= 2 else 'NICHT erfüllt'}")
    nur_dann = "Alle fünf erfüllt: v2 wird eingefroren." if (k1 and k2 and erf == 0 and not fehler and neu <= 12 and gescheitert <= 2) \
        else "Mindestens ein Kriterium offen oder verfehlt: Entscheidungsregel in Abschnitt 8 anwenden."
    print(f"\n{nur_dann}{hinweis}")


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
    todo = [z for z in zeilen if (not a.variante or z["variante"] == a.variante)
            and (not a.twin or z["twin_id"] == a.twin)
            and (a.alle or a.twin or not z.get("urteil"))]
    todo.sort(key=lambda z: (REIHENFOLGE.get(z["variante"], 9), z["twin_id"]))
    if not todo:
        print("Nichts zu bewerten.")
        return auswertung(zeilen)
    print(f"{len(todo)} Zwillinge zu bewerten. Enter = Vorschlag, s = überspringen, q = beenden.")
    for n, z in enumerate(todo, 1):
        print(f"\n--- {n} von {len(todo)} ---", end="")
        r = bewerte(z)
        if r == "q":
            break
        if r == "ok":
            speichere(felder, zeilen)
            print(f"  gespeichert: {z['twin_id']} -> {z['urteil']}, Befund {z['befund']}")
    print()
    auswertung(zeilen)


if __name__ == "__main__":
    main()
