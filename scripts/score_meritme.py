"""MeritMe-Scoring: jedes Dokument gegen jede Stelle, mit der Methode aus matching.py.

Eingabe   data/processed/scoring_docs.parquet, data/processed/scoring_jobs.parquet
Ausgabe   data/processed/scores_meritme.parquet   doc_id, job_id, score, methode, matched, missing, extra
          data/processed/scores_meritme_manifest.json

Aufruf (im Ordner scripts):  python score_meritme.py
"""
import hashlib
import importlib.metadata
import json
from datetime import date
from pathlib import Path

import pandas as pd

from matching import ESCO_SKILLS, ESCOX_MODEL, SIMILARITY_THRESHOLD, compare_skills, extract_skills

ROOT = Path(__file__).resolve().parents[1]
DOCS_FILE = ROOT / "data/processed/scoring_docs.parquet"
JOBS_FILE = ROOT / "data/processed/scoring_jobs.parquet"
SCORES_FILE = ROOT / "data/processed/scores_meritme.parquet"
MANIFEST_FILE = ROOT / "data/processed/scores_meritme_manifest.json"
METHOD_NAME = "meritme"

SKILL_NAME_BY_URI = dict(zip(ESCO_SKILLS["conceptUri"], ESCO_SKILLS["preferredLabel"]))


def skill_names(skill_uris):
    return sorted(SKILL_NAME_BY_URI[uri] for uri in skill_uris)


def extract_skills_per_id(ids, texts):
    """Jeder Text wird nur einmal extrahiert."""
    skills_by_id = {}
    for number, (text_id, text) in enumerate(zip(ids, texts), start=1):
        skills_by_id[text_id] = extract_skills(text)
        print(f"\r{number}/{len(ids)} Texte extrahiert", end="")
    print()
    return skills_by_id


def score_all_pairs(skills_by_doc, skills_by_job):
    rows = []
    for doc_id, offered in skills_by_doc.items():
        for job_id, required in skills_by_job.items():
            result = compare_skills(required, offered)
            rows.append({
                "doc_id": doc_id,
                "job_id": job_id,
                "score": result["score"],
                "methode": METHOD_NAME,
                "matched": skill_names(result["matched"]),
                "missing": skill_names(result["missing"]),
                "extra": skill_names(result["extra"]),
            })
    return pd.DataFrame(rows)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest(docs, jobs):
    manifest = {
        "methode": METHOD_NAME,
        "esco_skill_extractor": importlib.metadata.version("esco-skill-extractor"),
        "escox_modell": ESCOX_MODEL,
        "aehnlichkeitsschwelle": SIMILARITY_THRESHOLD,
        "anzahl_dokumente": len(docs),
        "anzahl_stellen": len(jobs),
        "eingabe_docs_sha256": sha256(DOCS_FILE),
        "eingabe_jobs_sha256": sha256(JOBS_FILE),
        "erstellt": str(date.today()),
    }
    MANIFEST_FILE.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    docs = pd.read_parquet(DOCS_FILE)
    jobs = pd.read_parquet(JOBS_FILE)
    skills_by_job = extract_skills_per_id(jobs["job_id"].tolist(), jobs["text"].tolist())
    skills_by_doc = extract_skills_per_id(docs["doc_id"].tolist(), docs["text"].tolist())

    scores = score_all_pairs(skills_by_doc, skills_by_job)
    scores.to_parquet(SCORES_FILE, index=False)
    write_manifest(docs, jobs)
    print(f"{len(scores)} Zeilen geschrieben: {SCORES_FILE}")


if __name__ == "__main__":
    main()
