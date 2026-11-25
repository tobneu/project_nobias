"""Baut die gemeinsamen Eingabetabellen für alle Scoring-Methoden (TF-IDF, MeritMe, SBERT).

Alle Methoden rechnen auf exakt denselben Dokumenten und Stellen. Jedes Dokument wird später gegen jede Stelle bewertet.

Ausgabe:
  data/processed/scoring_docs.parquet   doc_id, doc_typ, id, cv_id, ring, variante, richtung, assigned_job_id, text
  data/processed/scoring_jobs.parquet   job_id, ring, text

doc_typ:
  liste      die Bewerberliste (Pool für die Ränge)
  original   die Original-CVs der Zwillings-Quellen
  zwilling   die LLM-Zwillinge (doc_id = twin_id)

Aufruf (im Repo-Hauptordner):  python skripte/build_scoring_inputs.py
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]   # Skripte liegen in <Repo>/skripte/, ROOT ist der Repo-Ordner
MARKT = ROOT / "data/processed/jobmarket_data-engineer_180cv_2026-10-20.parquet"
CV_ROH = ROOT / "data/raw/djinni/cv_profiles_en.parquet"
JOB_ROH = ROOT / "data/raw/djinni/job_postings_en.parquet"
ZW_SCHLANK = ROOT / "data/processed/twins_vollauf_v2.parquet"
ZW_VOLL = ROOT / "twins/vollauf/vollauf_zwillinge.parquet"
OUT_DOCS = ROOT / "data/processed/scoring_docs.parquet"
OUT_JOBS = ROOT / "data/processed/scoring_jobs.parquet"


def verketten(df, spalten):
    text = df[spalten[0]].fillna("").astype(str)
    for s in spalten[1:]:
        text = text + "\n" + df[s].fillna("").astype(str)
    return text.str.strip()


def lade_zwillinge(quelle):
    if quelle == "auto":
        quelle = "voll" if ZW_VOLL.exists() else "schlank"
    pfad = ZW_VOLL if quelle == "voll" else ZW_SCHLANK
    if not pfad.exists():
        raise SystemExit(f"Zwillingstabelle fehlt: {pfad}")
    zw = pd.read_parquet(pfad)
    if "verwendbar" in zw.columns:
        zw = zw[zw["verwendbar"]]
    zw = zw.reset_index(drop=True).copy()
    zw["richtung"] = zw["richtung"].fillna("").astype(str).replace({"None": "", "nan": ""})
    return zw, quelle


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zwillinge", choices=["auto", "voll", "schlank"], default="auto",
                    help="voll: lokale Tabelle mit Originaltexten, schlank: Datei fürs Team (Originale aus Djinni)")
    args = ap.parse_args()

    markt = pd.read_parquet(MARKT)
    cv = pd.read_parquet(CV_ROH)
    cv = cv[cv["id"].isin(markt["id"])].drop_duplicates("id").copy()
    jobs = pd.read_parquet(JOB_ROH)
    jobs = jobs[jobs["id"].isin(markt["id"])].drop_duplicates("id").copy()
    cv["text"] = verketten(cv, ["Position", "Highlights", "Moreinfo"])
    jobs["text"] = verketten(jobs, ["Position", "Long Description"])

    # Stellen
    job_docs = markt[markt["role"] == "job"].merge(jobs[["id", "text"]], on="id", how="left")
    if job_docs["text"].isna().any():
        raise SystemExit("Stellentexte fehlen, Rohdaten prüfen")
    job_docs = job_docs.rename(columns={"id": "job_id"})[["job_id", "ring", "text"]].reset_index(drop=True)

    # Bewerberliste
    liste = markt[markt["role"] == "liste"].merge(cv[["id", "text"]], on="id", how="left")
    if liste["text"].isna().any():
        raise SystemExit("CV-Texte der Bewerberliste fehlen, Rohdaten prüfen")
    liste = pd.DataFrame({"doc_id": liste["id"], "doc_typ": "liste", "id": liste["id"], "cv_id": "",
                          "ring": liste["ring"], "variante": "", "richtung": "", "assigned_job_id": "",
                          "text": liste["text"]})

    # Zwillinge und Originale
    zw, quelle = lade_zwillinge(args.zwillinge)
    if "text_original" in zw.columns:
        orig_text = zw.drop_duplicates("id").set_index("id")["text_original"]
        quelle_original = "Zwillingstabelle (Eingabetext des LLM)"
    else:
        orig_text = cv.set_index("id")["text"]
        quelle_original = "Djinni-Rohdaten (rekonstruiert)"
    meta = zw.drop_duplicates("id").set_index("id")
    ids = list(meta.index)
    fehlt = [i for i in ids if i not in orig_text.index or pd.isna(orig_text.get(i))]
    if fehlt:
        raise SystemExit(f"Originaltext fehlt für {len(fehlt)} CVs, z. B. {fehlt[:3]}")
    originale = pd.DataFrame({"doc_id": ids, "doc_typ": "original", "id": ids,
                              "cv_id": [meta.loc[i, "cv_id"] for i in ids],
                              "ring": [meta.loc[i, "ring"] for i in ids], "variante": "", "richtung": "",
                              "assigned_job_id": [meta.loc[i, "assigned_job_id"] for i in ids],
                              "text": [orig_text[i] for i in ids]})
    zwillinge = pd.DataFrame({"doc_id": zw["twin_id"], "doc_typ": "zwilling", "id": zw["id"], "cv_id": zw["cv_id"],
                              "ring": zw["ring"], "variante": zw["variante"], "richtung": zw["richtung"],
                              "assigned_job_id": zw["assigned_job_id"], "text": zw["text_zwilling"]})

    docs = pd.concat([liste, originale, zwillinge], ignore_index=True)

    # Prüfungen
    if docs["doc_id"].duplicated().any():
        raise SystemExit("doc_id ist nicht eindeutig: " + str(docs.loc[docs["doc_id"].duplicated(), "doc_id"].head().tolist()))
    leer = docs["text"].fillna("").str.strip() == ""
    if leer.any():
        raise SystemExit(f"{int(leer.sum())} Dokumente ohne Text")
    zugeordnet = docs.loc[docs["assigned_job_id"] != "", "assigned_job_id"]
    unbekannt = set(zugeordnet) - set(job_docs["job_id"])
    if unbekannt:
        raise SystemExit(f"Zugeordnete Stellen fehlen im Markt: {sorted(unbekannt)[:3]}")

    OUT_DOCS.parent.mkdir(parents=True, exist_ok=True)
    docs.to_parquet(OUT_DOCS, index=False)
    job_docs.to_parquet(OUT_JOBS, index=False)

    print(f"Zwillingsquelle: {quelle}; Originaltexte aus: {quelle_original}")
    print(docs["doc_typ"].value_counts().to_string())
    print(f"{len(job_docs)} Stellen")
    print("Geschrieben:", OUT_DOCS)
    print("Geschrieben:", OUT_JOBS)


if __name__ == "__main__":
    main()
