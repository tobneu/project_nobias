"""Wählt die 12 Pilot-CVs aus (Plan: freeze_kriterien.md, Abschnitt 3).

Aufruf (im Ordner twin_pilot):  python src/select_pilot_cvs.py
Schreibt:  pilot/pilot_cvs.csv  und  pilot/cvs/<cv_id>.txt
Pro Ring 4 CVs: je ein Listen-, Prosa- und kurzer CV plus ein vierter
(Ring A: Liste, Ring B: Prosa, Ring C: kurz) -> insgesamt 4 Liste, 4 Prosa, 4 kurz.
Ausgeschlossen: Job Markt (Jobs und 180 CVs, damit auch die 120 Quell-CVs des Vollaufs),
die drei Test-CVs, kyrillische Texte. Fester Zufallsstartwert."""
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 2026
BASE = Path(os.environ.get("NOBIAS_BASE", r"project_nobias"))
MARKT = BASE / "data/processed/jobmarket_data-engineer_180cv_2026-10-20.parquet"
CV_ROH = BASE / "data/raw/djinni/cv_profiles_en.parquet"
ROOT = Path(os.environ.get("TWIN_DIR", Path(__file__).resolve().parent.parent))
TEST_CVS = ("036d40ed", "e26ee3f2", "222d5f74")

RINGE = {"A": "Data Engineer", "B": "Python", "C": "QA Automation"}
PLAN = {
    "A": ["Liste", "Prosa", "kurz", "Liste"],
    "B": ["Liste", "Prosa", "kurz", "Prosa"],
    "C": ["Liste", "Prosa", "kurz", "kurz"],
}


def lade_pool():
    markt = pd.read_parquet(MARKT)
    cv = pd.read_parquet(CV_ROH)
    cv["text"] = [
        "\n".join(str(x) for x in z if pd.notna(x)).strip()
        for z in cv[["Position", "Highlights", "Moreinfo"]].itertuples(index=False)
    ]
    rest = cv[~cv["id"].isin(markt["id"])].copy()
    rest = rest[~rest["text"].apply(lambda t: bool(re.search("[\u0400-\u04FF]", t)))]
    rest = rest[rest["Primary Keyword"].isin(RINGE.values())].copy()
    rest = rest[~rest["id"].astype(str).str[:8].isin(TEST_CVS)]

    rest["n_words"] = rest["text"].apply(lambda t: len(t.split()))
    s = rest["text"].apply(lambda t: len(re.findall(r"[.!?](?:\s|$)", t)))
    c = rest["text"].apply(lambda t: t.count(","))
    rest["prosa"] = (s >= 4) & (c < rest["n_words"] * 0.12)

    # Gruppen überschneidungsfrei: kurz zuerst, dann Liste (60-100) und Prosa (120-200)
    rest["gruppe"] = ""
    rest.loc[(rest["n_words"] >= 60) & (rest["n_words"] <= 100) & ~rest["prosa"], "gruppe"] = "Liste"
    rest.loc[(rest["n_words"] >= 120) & (rest["n_words"] <= 200) & rest["prosa"], "gruppe"] = "Prosa"
    rest.loc[(rest["n_words"] >= 30) & (rest["n_words"] <= 59), "gruppe"] = "kurz"
    rest["ring"] = rest["Primary Keyword"].map({v: k for k, v in RINGE.items()})
    return rest[rest["gruppe"] != ""]


def main():
    pool = lade_pool()
    print("Kandidaten pro Ring und Gruppe:")
    print(pool.groupby(["ring", "gruppe"]).size().unstack(fill_value=0), "\n")

    gewaehlt = []
    for ring, plan in PLAN.items():
        for gruppe in sorted(set(plan)):
            n = plan.count(gruppe)
            kand = pool[(pool["ring"] == ring) & (pool["gruppe"] == gruppe)]
            if len(kand) < n:
                sys.exit(f"Zu wenige Kandidaten: Ring {ring}, {gruppe}: {len(kand)} < {n}")
            gewaehlt.append(kand.sample(n, random_state=SEED))
    sel = pd.concat(gewaehlt).sort_values(["ring", "gruppe"]).reset_index(drop=True)

    sel["cv_id"] = sel["id"].astype(str).str[:8]
    if sel["cv_id"].duplicated().any():
        sys.exit("Doppelte 8-stellige cv_id, bitte melden.")

    (ROOT / "pilot" / "cvs").mkdir(parents=True, exist_ok=True)
    for _, r in sel.iterrows():
        (ROOT / "pilot" / "cvs" / f"{r['cv_id']}.txt").write_text(r["text"], encoding="utf-8")

    out = sel[["cv_id", "id", "ring", "Primary Keyword", "gruppe", "n_words"]].rename(
        columns={"Primary Keyword": "primary_keyword", "gruppe": "cv_typ"}).assign(seed=SEED)
    out.to_csv(ROOT / "pilot" / "pilot_cvs.csv", index=False, encoding="utf-8")
    print(out.to_string(index=False))
    print(f"\n{len(out)} CVs gespeichert: pilot/pilot_cvs.csv und pilot/cvs/<cv_id>.txt")


main()
