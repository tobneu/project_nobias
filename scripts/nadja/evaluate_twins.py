"""Zwillinge auswerten: Stufe 1 (Label-Stabilität) und Stufe 2 (Rangabstand), MeritMe vs. TF-IDF.

Eingabe: Aylas Zwillinge, eine Zeile pro Zwilling, mit cv_id, variante, richtung, text_original, text_zwilling,
test, assigned_job_id. Liest die Parquet-/CSV-Datei aus data/processed oder die Ansicht vollauf_zwillinge.html.

Vergleich je Zwilling: Original-CV gegen Zwilling, beide gegen denselben Job (assigned_job_id), jeweils einzeln
in dieselbe Bewerberliste (60 CVs) einsortiert.

Methoden:
    escox, hybrid, escox_v2_it, hybrid_v2, hybrid_v2_noedu  MeritMe-Recall auf den Labels aus labels.py
    tfidf          nur mit --tfidf: VORLÄUFIGE Baseline (TF-IDF + Cosine, gefittet auf Jobs + Bewerberliste wie in
                   eda_jobmarket_final.ipynb), Platzhalter bis Aylas TF-IDF-Pipeline angebunden ist.
                   Ohne Baseline gibt es Stufe 1 und die MeritMe-Rangabstände, aber keinen Wilcoxon-Vergleich.

Kommandozeile (aus dem Repo-Ordner):
    python scripts/evaluate_twins.py --twins path/to/vollauf_zwillinge.html            # nur MeritMe
    python scripts/evaluate_twins.py --twins path/to/vollauf_zwillinge.html --tfidf    # + vorläufige Baseline
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

sys.path.append(str(Path(__file__).resolve().parent))
from labels import METHODS, PROCESSED, label_market, label_names, load_market   # noqa: E402
from matching import rank_distance, score, score_matrix                 # noqa: E402

TOKEN_PATTERN = r"(?u)\b\w[\w+#]*"      # behält c++, c#, r (scikit-learn verwirft sonst Ein-Zeichen-Tokens)
JACCARD_ZIEL = 0.85


# --------------------------------------------------------------------------------------------- Laden

def load_twins(path: Path, market: pd.DataFrame) -> pd.DataFrame:
    """Zwillinge laden und die volle ID der Zwillings-Quelle ergänzen (cv_id ist ein 8-Zeichen-Präfix)."""
    path = Path(path)
    if path.suffix == ".html":
        html = path.read_text(encoding="utf-8")
        start = re.search(r"const\s+D\s*=\s*", html).end()       # Datenblock der HTML-Ansicht
        twins = pd.DataFrame(json.JSONDecoder().raw_decode(html[start:])[0])
    elif path.suffix == ".csv":
        twins = pd.read_csv(path)
    else:
        twins = pd.read_parquet(path)

    sources = market[market["role"] == "zwilling_quelle"]
    prefix = dict(zip(sources["id"].str[:8], sources["id"]))
    twins["source_id"] = twins["cv_id"].map(prefix)
    if twins["source_id"].isna().any():
        raise ValueError(f"{twins['source_id'].isna().sum()} Zwillinge ohne passende Quelle im Markt")
    if "verwendbar" in twins:
        twins = twins[twins["verwendbar"]]
    return twins.reset_index(drop=True)


# --------------------------------------------------------------------------------------------- Scoring je Methode

def meritme_scores(market, twins, method):
    """Labels für Markt und Zwillinge, dann Scores von Original und Zwilling sowie die Listen-Scores je Job."""
    market = label_market(market, method)
    twin_docs = label_market(twins[["twin_id", "text_zwilling"]].rename(columns={"twin_id": "id", "text_zwilling": "text"}),
                             method)
    labels = dict(zip(market["id"], market["labels"]))
    twin_labels = dict(zip(twin_docs["id"], twin_docs["labels"]))
    jobs = market[market["role"] == "job"]
    liste = market[market["role"] == "liste"]
    list_scores = {jid: score_matrix([labels[jid]], liste["labels"])[0] for jid in jobs["id"]}

    rows = []
    for _, t in twins.iterrows():
        job, orig, twin = labels[t["assigned_job_id"]], labels[t["source_id"]], twin_labels[t["twin_id"]]
        so, st = score(job, orig)["score"], score(job, twin)["score"]
        union = orig | twin
        rows.append({"twin_id": t["twin_id"], "methode": method,
                     "jaccard": len(orig & twin) / len(union) if union else 1.0,
                     "neu": twin - orig, "weg": orig - twin,
                     "score_orig": so, "score_twin": st,
                     **rank_distance(so, st, list_scores[t["assigned_job_id"]])})
    return pd.DataFrame(rows)


def tfidf_scores(market, twins):
    """Vorläufige TF-IDF-Baseline: Cosine zwischen Job und CV, Vektorraum aus Jobs + Bewerberliste."""
    fit_docs = market[market["role"].isin(["job", "liste"])]
    vec = TfidfVectorizer(stop_words="english", token_pattern=TOKEN_PATTERN).fit(fit_docs["text"])
    text = dict(zip(market["id"], market["text"]))
    jobs = market[market["role"] == "job"]
    liste = market[market["role"] == "liste"]
    J = dict(zip(jobs["id"], vec.transform(jobs["text"])))
    L = vec.transform(liste["text"])
    list_scores = {jid: cosine_similarity(J[jid], L)[0] for jid in jobs["id"]}

    O = vec.transform([text[s] for s in twins["source_id"]])
    T = vec.transform(twins["text_zwilling"])
    rows = []
    for i, t in twins.iterrows():
        jv = J[t["assigned_job_id"]]
        so, st = float(cosine_similarity(jv, O[i])[0, 0]), float(cosine_similarity(jv, T[i])[0, 0])
        rows.append({"twin_id": t["twin_id"], "methode": "tfidf", "jaccard": np.nan,
                     "score_orig": so, "score_twin": st,
                     **rank_distance(so, st, list_scores[t["assigned_job_id"]])})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------------- Auswertung

def rank_biserial(diff) -> float:
    """Effektstärke zum Wilcoxon-Test (matched-pairs rank-biserial r, Nullen weggelassen)."""
    d = np.asarray(diff, dtype=float)
    d = d[d != 0]
    if not len(d):
        return 0.0
    ranks = pd.Series(np.abs(d)).rank().to_numpy()
    return float((ranks[d > 0].sum() - ranks[d < 0].sum()) / ranks.sum())


def summarize(results: pd.DataFrame, twins: pd.DataFrame) -> dict:
    r = results.merge(twins[["twin_id", "variante", "richtung", "ring", "test"]], on="twin_id")
    r["abs_delta"] = (r["score_twin"] - r["score_orig"]).abs()
    main = r[r["test"] == "haupttest"]

    stufe1 = (main[main["methode"] != "tfidf"]
              .groupby(["variante", "methode"])["jaccard"]
              .agg(Mittel="mean", Anteil_ab_085=lambda j: (j >= JACCARD_ZIEL).mean()).unstack().round(2))
    stufe2 = (main.groupby(["variante", "methode"])
              .agg(rangabstand=("distance", "mean"), abstand_0=("distance", lambda d: (d == 0).mean()),
                   davon_gleicher_block=("same_block", "mean"), abs_delta_score=("abs_delta", "mean"))
              .round(3).unstack())

    tests = []
    for variante, g in (main.groupby("variante") if (main["methode"] == "tfidf").any() else []):
        wide = g.pivot(index="twin_id", columns="methode", values="distance")
        for m in [c for c in wide.columns if c != "tfidf"]:
            diff = wide[m] - wide["tfidf"]
            p = wilcoxon(diff, alternative="less").pvalue if (diff != 0).any() else np.nan
            tests.append({"variante": variante, "methode": m, "n": len(diff),
                          "MeritMe_kleiner": (diff < 0).mean(), "gleich": (diff == 0).mean(),
                          "p_wilcoxon": p, "r": rank_biserial(diff)})
    return {"stufe1": stufe1, "stufe2": stufe2, "wilcoxon": pd.DataFrame(tests).round(3), "alle": r}


def main():
    parser = argparse.ArgumentParser(description="Zwillinge auswerten (Stufe 1 und 2).")
    parser.add_argument("--twins", required=True, help="Parquet, CSV oder vollauf_zwillinge.html")
    parser.add_argument("--tfidf", action="store_true", help="vorläufige TF-IDF-Baseline mitrechnen (Stufe-2-Vergleich)")
    parser.add_argument("--methods", nargs="+", choices=METHODS,
                        default=["escox", "hybrid", "escox_v2_it", "hybrid_v2", "hybrid_v2_noedu"])
    args = parser.parse_args()

    market = load_market()
    twins = load_twins(args.twins, market)
    print(f"{len(twins)} Zwillinge, Varianten: {twins['variante'].value_counts().to_dict()}\n")

    parts = [meritme_scores(market, twins, m) for m in args.methods]
    if args.tfidf:
        parts.append(tfidf_scores(market, twins))
    results = pd.concat(parts, ignore_index=True)
    out = summarize(results, twins)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", None)
    print("STUFE 1 – Label-Stabilität Original ↔ Zwilling (Haupttest, Ziel Ø ≥ 0,85):\n", out["stufe1"], "\n")
    print("STUFE 2 – Rangabstand Original ↔ Zwilling (Haupttest; 'para' = Rauschgrenze):\n", out["stufe2"], "\n")
    if args.tfidf:
        print("Wilcoxon je Variante: Rangabstand MeritMe < TF-IDF? (r < 0 heißt MeritMe stabiler)\n", out["wilcoxon"], "\n")
    else:
        print("Ohne Baseline kein Wilcoxon-Vergleich (mit --tfidf die vorläufige Version mitrechnen).\n")

    # Welche Labels ändern sich am häufigsten? (Hinweis auf Proxy-Lecks wie 'computer science' bei edu)
    for m in args.methods:
        a = out["alle"][(out["alle"]["methode"] == m)]
        for v, g in a.groupby("variante"):
            neu = pd.Series([x for s in g["neu"] for x in label_names(s)]).value_counts().head(3)
            if len(neu):
                print(f"{m:7s} {v:5s} häufigste neue Labels: {neu.to_dict()}")

    path = PROCESSED / "twin_eval.parquet"
    res = out["alle"].drop(columns=["neu", "weg"]).copy()
    res.to_parquet(path, index=False)
    print(f"\nErgebnisse je Zwilling gespeichert: {path}")


if __name__ == "__main__":
    main()
