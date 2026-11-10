"""Vollauf, Schritt 1: Übernimmt die 120 Quell-CVs aus Tobis Markt (role == "zwilling_quelle").

Aufruf (im Ordner twins):  python src/vollauf_select.py
Liest:     ../data/processed/jobmarket_data-engineer_180cv_2026-10-20.parquet
           ../data/raw/djinni/cv_profiles_en.parquet
Schreibt:  vollauf/vollauf_cvs.csv  und  vollauf/cvs/<cv_id>.txt   (CV-Texte nur lokal, nicht in Git)
Es wird nichts gezogen: Tobis Notebook hat die 120 CVs schon festgelegt (A 70, B 30, C 20)."""
import os
import re
import sys
from pathlib import Path

import pandas as pd

BASE = Path(os.environ.get("NOBIAS_BASE", Path(__file__).resolve().parents[2]))
MARKT = BASE / "data/processed/jobmarket_data-engineer_180cv_2026-10-20.parquet"
CV_ROH = BASE / "data/raw/djinni/cv_profiles_en.parquet"
ROOT = Path(os.environ.get("TWIN_DIR", Path(__file__).resolve().parent.parent))
VOLL = ROOT / "vollauf"
ERWARTET = {"A": 70, "B": 30, "C": 20}


def typ(text, n_words):
    """Gleiche Einteilung wie im Pilot (kurz / Liste / Prosa), hier nur zur Beschreibung."""
    s = len(re.findall(r"[.!?](?:\s|$)", text))
    if n_words < 60:
        return "kurz"
    return "Prosa" if (s >= 4 and text.count(",") < n_words * 0.12) else "Liste"


def main():
    if not MARKT.exists():
        sys.exit(f"Tobis Markt fehlt: {MARKT}")
    markt = pd.read_parquet(MARKT)
    quellen = markt[markt["role"] == "zwilling_quelle"].copy()
    zaehl = quellen.groupby("ring").size().to_dict()
    if zaehl != ERWARTET:
        sys.exit(f"Unerwartete Verteilung {zaehl}, erwartet {ERWARTET}. Stand mit Tobi abgleichen.")

    cv = pd.read_parquet(CV_ROH)
    cv["text"] = ["\n".join(str(x) for x in z if pd.notna(x)).strip()
                  for z in cv[["Position", "Highlights", "Moreinfo"]].itertuples(index=False)]
    quellen = quellen.merge(cv[["id", "text"]], on="id", how="left")
    if quellen["text"].isna().any():
        sys.exit("Für einige IDs fehlt der CV-Text in cv_profiles_en.parquet.")

    quellen["cv_id"] = quellen["id"].astype(str).str[:8]
    if quellen["cv_id"].duplicated().any():
        sys.exit("Doppelte 8-stellige cv_id, bitte melden.")
    pilot = ROOT / "pilot" / "pilot_cvs.csv"
    if pilot.exists():
        doppelt = set(quellen["cv_id"]) & set(pd.read_csv(pilot)["cv_id"].astype(str))
        if doppelt:
            sys.exit(f"CVs aus dem Pilot sind auch im Vollauf: {sorted(doppelt)}")
    quellen["n_words_text"] = quellen["text"].apply(lambda t: len(t.split()))
    abw = quellen[(quellen["n_words_text"] - quellen["n_words"]).abs() > 2]
    if len(abw):
        print(f"HINWEIS: {len(abw)} CVs mit anderer Wortzahl als in Tobis Markt "
              f"(Textaufbau prüfen), z. B. {', '.join(abw['cv_id'].head(5))}")
    quellen["cv_typ"] = [typ(t, n) for t, n in zip(quellen["text"], quellen["n_words_text"])]

    (VOLL / "cvs").mkdir(parents=True, exist_ok=True)
    for _, r in quellen.iterrows():
        (VOLL / "cvs" / f"{r['cv_id']}.txt").write_text(r["text"], encoding="utf-8")
    out = quellen.sort_values(["ring", "cv_id"])[
        ["cv_id", "id", "ring", "test", "primary_keyword", "cv_typ", "n_words_text", "n_keywords", "assigned_job_id"]
    ].rename(columns={"n_words_text": "n_words", "n_keywords": "n_hits"})
    out.to_csv(VOLL / "vollauf_cvs.csv", index=False, encoding="utf-8")
    print(out.groupby(["ring", "cv_typ"]).size().unstack(fill_value=0), "\n")
    print(f"{len(out)} CVs gespeichert: vollauf/vollauf_cvs.csv und vollauf/cvs/<cv_id>.txt")


if __name__ == "__main__":
    main()
