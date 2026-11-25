"""TF-IDF-Scoring: jedes Dokument gegen jede Stelle.

Schnittstelle, die alle Methoden (TF-IDF, MeritMe, SBERT) einhalten:
  Eingabe   data/processed/scoring_docs.parquet   (doc_id, doc_typ, text, ...)
            data/processed/scoring_jobs.parquet   (job_id, text, ...)
  Ausgabe   data/processed/scores_<methode>.parquet   Langform mit den Spalten
              doc_id   ID des Dokuments (wie in scoring_docs)
              job_id   ID der Stelle (wie in scoring_jobs)
              score    Zahl, höher heißt bessere Passung
              methode  Name der Methode
            data/processed/scores_<methode>_manifest.json   Einstellungen und Prüfsummen der Eingabe

Eine andere Methode muss nur die Funktion score(docs, jobs, ...) -> Tabelle mit diesen vier Spalten liefern.

Hauptkonfiguration: Baseline aus Tobis EDA (Preset "baseline"). Die weiteren Presets dienen der Sensitivitätsanalyse
und sind identisch mit denen in notebooks/vor_tfidf_methodenwahl.ipynb.

Aufrufe (im Repo-Hauptordner):
  python skripte/score_tfidf.py                         Baseline, schreibt scores_tfidf.parquet
  python skripte/score_tfidf.py --alle                  alle Presets (scores_tfidf_<preset>.parquet)
  python skripte/score_tfidf.py --preset sublinear_tf   ein Preset
  python skripte/score_tfidf.py --docs neue.parquet --vektorisierer data/processed/tfidf_vektorisierer.pkl --out neue_scores.parquet
      bewertet neue CVs mit dem gespeicherten Vektorisierer (ohne neue Anpassung)
"""
import argparse
import hashlib
import json
import pickle
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parents[1]   # Skripte liegen in <Repo>/skripte/, ROOT ist der Repo-Ordner
PROC = ROOT / "data/processed"

TOKEN_PATTERN = r"(?u)(?<![\w.])\.?\w(?:[\w.]*\w)?[+#]*"
BASIS = dict(stop_words="english", token_pattern=TOKEN_PATTERN)

# fit: aus welchen Texten die Gewichte (IDF) berechnet werden. Zwillinge gehen nie in die Anpassung ein.
PRESETS = {
    "baseline": dict(vec=dict(BASIS), fit="jobs+liste"),
    "sublinear_tf": dict(vec=dict(BASIS, sublinear_tf=True), fit="jobs+liste"),
    "ngram_1_2": dict(vec=dict(BASIS, ngram_range=(1, 2)), fit="jobs+liste"),
    "ohne_stoppwoerter": dict(vec=dict(token_pattern=TOKEN_PATTERN), fit="jobs+liste"),
    "fit_nur_jobs": dict(vec=dict(BASIS), fit="jobs"),
    "fit_mit_originalen": dict(vec=dict(BASIS), fit="jobs+liste+originale"),
}


def methodenname(preset):
    return "tfidf" if preset == "baseline" else f"tfidf_{preset}"


def sha256(pfad):
    h = hashlib.sha256()
    with open(pfad, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def anpassen(docs, jobs, config):
    texte = list(jobs["text"])
    if "liste" in config["fit"]:
        texte += list(docs.loc[docs["doc_typ"] == "liste", "text"])
    if "originale" in config["fit"]:
        texte += list(docs.loc[docs["doc_typ"] == "original", "text"])
    return TfidfVectorizer(**config["vec"]).fit(texte)


def score(docs, jobs, config=None, vektorisierer=None, methode="tfidf"):
    # Schnittstelle: liefert doc_id, job_id, score, methode (jedes Dokument gegen jede Stelle)
    if vektorisierer is None:
        vektorisierer = anpassen(docs, jobs, config or PRESETS["baseline"])
    D = vektorisierer.transform(docs["text"])
    J = vektorisierer.transform(jobs["text"])
    S = (D @ J.T).toarray()   # Zeilen sind L2-normiert, das Skalarprodukt ist die Cosinus-Ähnlichkeit
    out = pd.DataFrame({"doc_id": np.repeat(docs["doc_id"].to_numpy(), len(jobs)),
                        "job_id": np.tile(jobs["job_id"].to_numpy(), len(docs)),
                        "score": S.ravel(), "methode": methode})
    return out, vektorisierer


def kurzpruefung(docs, scores):
    # Zeigt Kennzahlen zum Gegenprüfen mit dem Vor-Notebook (Median Score von Original und Zwilling zur zugeordneten Stelle)
    z = docs.loc[docs["assigned_job_id"] != "", ["doc_id", "doc_typ", "assigned_job_id"]]
    m = z.merge(scores, left_on=["doc_id", "assigned_job_id"], right_on=["doc_id", "job_id"])
    print("Median Score zur zugeordneten Stelle:", m.groupby("doc_typ")["score"].median().round(4).to_dict())
    print(f"Score-Bereich: {scores['score'].min():.4f} bis {scores['score'].max():.4f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preset", default="baseline", choices=list(PRESETS))
    ap.add_argument("--alle", action="store_true", help="alle Presets rechnen")
    ap.add_argument("--docs", default=str(PROC / "scoring_docs.parquet"))
    ap.add_argument("--jobs", default=str(PROC / "scoring_jobs.parquet"))
    ap.add_argument("--vektorisierer", default=None, help="gespeicherten Vektorisierer laden statt neu anzupassen")
    ap.add_argument("--out", default=None, help="Ausgabedatei (nur mit einem Preset)")
    args = ap.parse_args()

    docs = pd.read_parquet(args.docs)
    jobs = pd.read_parquet(args.jobs)
    for spalte in ("doc_id", "text"):
        if spalte not in docs.columns:
            raise SystemExit(f"Spalte {spalte} fehlt in {args.docs}")
    if "assigned_job_id" not in docs.columns:
        docs["assigned_job_id"] = ""
    if "doc_typ" not in docs.columns:
        docs["doc_typ"] = "unbekannt"
    if docs["doc_id"].duplicated().any():
        raise SystemExit("doc_id ist nicht eindeutig")

    presets = list(PRESETS) if args.alle else [args.preset]
    for preset in presets:
        config = PRESETS[preset]
        methode = methodenname(preset)
        gespeichert = None
        if args.vektorisierer:
            gespeichert = pickle.load(open(args.vektorisierer, "rb"))
        scores, vec = score(docs, jobs, config, vektorisierer=gespeichert, methode=methode)

        out = Path(args.out) if (args.out and not args.alle) else PROC / f"scores_{methode}.parquet"
        out.parent.mkdir(parents=True, exist_ok=True)
        scores.to_parquet(out, index=False)
        if gespeichert is None:
            pickle.dump(vec, open(PROC / f"{methode}_vektorisierer.pkl", "wb"))

        manifest = {
            "methode": methode, "preset": preset,
            "vektorisierer": {k: (list(v) if isinstance(v, tuple) else v) for k, v in config["vec"].items()},
            "anpassung_auf": config["fit"] if gespeichert is None else "gespeicherter Vektorisierer",
            "vokabular_groesse": len(vec.vocabulary_),
            "anzahl_dokumente": int(len(docs)), "anzahl_stellen": int(len(jobs)),
            "dokumente_je_typ": docs["doc_typ"].value_counts().to_dict(),
            "eingabe_docs": Path(args.docs).name, "eingabe_docs_sha256": sha256(args.docs),
            "eingabe_jobs": Path(args.jobs).name, "eingabe_jobs_sha256": sha256(args.jobs),
            "scikit_learn": sklearn.__version__, "erstellt": str(date.today()),
        }
        mpfad = out.with_name(out.stem + "_manifest.json")
        mpfad.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"\n[{methode}] {len(scores)} Zeilen, Vokabular {len(vec.vocabulary_)} Wörter")
        kurzpruefung(docs, scores)
        print("Geschrieben:", out)


if __name__ == "__main__":
    main()
