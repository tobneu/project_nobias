"""Vollauf, Schritt 2: Erzeugt die Anker (MUST_KEEP) automatisch mit Tobis Keyword-Mustern (wie im Pilot).

Voraussetzung: keywords.pkl im Ordner twins (aus Tobis Notebook, siehe Anleitung).
Aufruf (im Ordner twins):  python src/vollauf_anchors.py
Liest vollauf/vollauf_cvs.csv, schreibt vollauf/cvs/<cv_id>.anchors.txt (kommagetrennt).
Anker sind die Schreibweisen aus dem CV selbst (match.group(0)), nicht die ESCO-Namen."""
import csv
import os
import pickle
from pathlib import Path

ROOT = Path(os.environ.get("TWIN_DIR", Path(__file__).resolve().parent.parent))
CVS = ROOT / "vollauf" / "cvs"


def anker_aus_text(text, ring_muster):
    """Alle Treffer beider Sichten (ESCO, TF-IDF), in Textreihenfolge, ohne Dubletten (Groß/Klein egal)."""
    treffer = []
    for muster in ring_muster:                       # ring_muster = (esco_dict, tfidf_dict)
        for pattern in muster.values():
            for m in pattern.finditer(text):
                treffer.append((m.start(), m.group(0)))
    gesehen, anker = set(), []
    for _, wort in sorted(treffer):
        if wort.lower() not in gesehen:
            gesehen.add(wort.lower())
            anker.append(wort)
    return anker


def main():
    pkl = ROOT / "keywords.pkl"
    if not pkl.exists():
        raise SystemExit(f"{pkl} fehlt. Erst die Zelle aus der Anleitung in Tobis Notebook ausführen.")
    with open(pkl, "rb") as f:
        daten = pickle.load(f)
    keywords = daten["KEYWORDS"]

    with open(ROOT / "vollauf" / "vollauf_cvs.csv", encoding="utf-8", newline="") as f:
        zeilen = list(csv.DictReader(f))

    print(f"{'cv_id':10} {'Ring':5} {'Anker':6} Beispiele")
    for z in zeilen:
        text = (CVS / f"{z['cv_id']}.txt").read_text(encoding="utf-8")
        anker = anker_aus_text(text, keywords[z["ring"]])
        mit_komma = [a for a in anker if "," in a]
        anker = [a for a in anker if "," not in a]
        (CVS / f"{z['cv_id']}.anchors.txt").write_text(", ".join(anker), encoding="utf-8")
        hinweis = ""
        if len(anker) < 4:
            hinweis = "  <- WENIG ANKER, von Hand prüfen"
        if mit_komma:
            hinweis += f"  <- {len(mit_komma)} Anker mit Komma entfernt"
        print(f"{z['cv_id']:10} {z['ring']:5} {len(anker):<6} {', '.join(anker[:6])}{hinweis}")
    print("\nAnker gespeichert: vollauf/cvs/<cv_id>.anchors.txt")


if __name__ == "__main__":
    main()
