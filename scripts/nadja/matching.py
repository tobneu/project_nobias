"""Labels -> Score, Matched/Missing/Extra und Rang (MeritMe v1).

Zwei Teile:
    1. Scoring (MeritMe-spezifisch): Recall der Job-Labels im CV + Matched/Missing/Extra
    2. Ranking (methodenneutral): arbeitet nur mit Scores, funktioniert also genauso mit TF-IDF-Cosine

Tie-Regel: Bei Gleichstand bekommt ein CV den mittleren Rang seines Blocks (wie insert_rank in
eda_keksausstecher.ipynb). Zusätzlich wird die Blockgröße ausgegeben, damit Abstand 0 durch Gleichstand
erkennbar bleibt.

Benutzung im Notebook:
    import sys; sys.path.append("../scripts")
    from labels import load_market, label_market
    from matching import score, ranking, rank_distance
    market = label_market(load_market(), method="hybrid_v2")

Kommandozeile (aus dem Repo-Ordner):
    python scripts/matching.py --method hybrid_v2
"""
import argparse

import numpy as np
import pandas as pd

TOL = 1e-12          # Scores gelten als gleich, wenn sie sich um weniger unterscheiden (Rundungsfehler)


# --------------------------------------------------------------------------------------------- 1. Scoring

def score(job_labels: set, cv_labels: set) -> dict:
    """Recall = Anteil der Job-Labels, die auch im CV stehen.

    matched: vom Job gefordert und im CV | missing: gefordert, fehlt im CV | extra: im CV, nicht gefordert
    Ein Job ohne Labels ergibt Score 0 (es gibt nichts zu erfüllen).
    """
    job_labels, cv_labels = set(job_labels), set(cv_labels)
    matched = job_labels & cv_labels
    return {
        "score": len(matched) / len(job_labels) if job_labels else 0.0,
        "matched": matched,
        "missing": job_labels - cv_labels,
        "extra": cv_labels - job_labels,
    }


def score_matrix(job_label_sets, cv_label_sets) -> np.ndarray:
    """Scores aller Jobs × aller CVs (Zeile = Job, Spalte = CV)."""
    return np.array([[score(j, c)["score"] for c in cv_label_sets] for j in job_label_sets])


# --------------------------------------------------------------------------------------------- 2. Ranking

def rank_into_list(candidate_score: float, list_scores) -> tuple[float, int]:
    """Platz eines Kandidaten, wenn er in eine Liste mit diesen Scores einsortiert wird (1 = bester).

    Gleichstand: mittlerer Rang des Blocks. Beispiel: 5 CVs besser, 21 gleich -> Block belegt mit dem Kandidaten
    die Plätze 6–27 -> Rang 16,5, Blockgröße 22.
    Rückgabe: (Rang, Blockgröße inkl. Kandidat)
    """
    list_scores = np.asarray(list_scores, dtype=float)
    better = int((list_scores > candidate_score + TOL).sum())
    equal = int((np.abs(list_scores - candidate_score) <= TOL).sum())
    return better + 1 + equal / 2, equal + 1


def ranking(list_scores) -> pd.DataFrame:
    """Rangliste einer Bewerberliste für einen Job: Rang (mittlerer Rang bei Gleichstand) und Blockgröße je CV."""
    s = pd.Series(np.asarray(list_scores, dtype=float)).round(12)
    return pd.DataFrame({"score": s, "rank": s.rank(ascending=False, method="average"),
                         "block": s.map(s.value_counts())})


def rank_distance(score_a: float, score_b: float, list_scores) -> dict:
    """Rangabstand zweier Zwillinge, jeder einzeln in dieselbe Liste einsortiert (Stufe 2)."""
    rank_a, block_a = rank_into_list(score_a, list_scores)
    rank_b, block_b = rank_into_list(score_b, list_scores)
    return {"rank_a": rank_a, "rank_b": rank_b, "distance": abs(rank_a - rank_b),
            "block_a": block_a, "block_b": block_b,
            "same_block": abs(score_a - score_b) <= TOL}      # Abstand 0 nur wegen Gleichstand?


# --------------------------------------------------------------------------------------------- Sanity-Checks

def sanity_checks(job_labels: set, cv_labels: set, list_scores) -> None:
    """Muss immer stimmen; wirft AssertionError, wenn der Code falsch rechnet."""
    assert score(job_labels, job_labels)["score"] == 1.0 or not job_labels, "Job gegen sich selbst muss 1 sein"
    r = score(job_labels, cv_labels)
    assert r["matched"] | r["missing"] == set(job_labels), "matched + missing müssen alle Job-Labels ergeben"
    assert not (r["matched"] & r["missing"]), "matched und missing dürfen sich nicht überschneiden"
    s = r["score"]
    assert rank_distance(s, s, list_scores)["distance"] == 0, "derselbe CV zweimal muss Abstand 0 haben"
    assert rank_into_list(2.0, list_scores) == (1.0, 1), "ein Score über allen muss Platz 1 sein"
    assert rank_into_list(-1.0, list_scores)[0] == len(list_scores) + 1, "ein Score unter allen muss letzter sein"


# --------------------------------------------------------------------------------------------- Kommandozeile

def main():
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parent))
    from labels import DEFAULT_METHOD, METHODS, label_market, label_names, load_market

    parser = argparse.ArgumentParser(description="MeritMe-Matching v1 auf dem Jobmarkt.")
    parser.add_argument("--method", choices=METHODS, default=DEFAULT_METHOD)
    args = parser.parse_args()

    market = label_market(load_market(), args.method)
    jobs = market[market["role"] == "job"].reset_index(drop=True)
    liste = market[market["role"] == "liste"].reset_index(drop=True)
    sources = market[market["role"] == "zwilling_quelle"].reset_index(drop=True)
    S = score_matrix(jobs["labels"], liste["labels"])                           # 20 × 60

    for j in range(len(jobs)):
        sanity_checks(jobs.loc[j, "labels"], liste.loc[0, "labels"], S[j])
    print(f"Methode: {args.method} | Sanity-Checks bestanden ({len(jobs)} Jobs)\n")

    rings = liste["ring"].to_numpy()
    print("Median-Score pro Ring (soll A > B > C):",
          {r: round(float(np.median(S[:, rings == r])), 3) for r in "ABC"})
    print(f"Verschiedene Scores pro Job: Ø {np.mean([len(np.unique(row.round(12))) for row in S]):.1f} "
          f"von {len(liste)} CVs")

    # Zwillings-Quellen probehalber in die Liste ihres Jobs einsortieren
    job_pos = {jid: i for i, jid in enumerate(jobs["id"])}
    rows = []
    for _, src in sources.iterrows():
        j = job_pos[src["assigned_job_id"]]
        s = score(jobs.loc[j, "labels"], src["labels"])["score"]
        rank, block = rank_into_list(s, S[j])
        rows.append({"ring": src["ring"], "rank": rank, "block": block, "score0": s == 0})
    pos = pd.DataFrame(rows).groupby("ring").agg(median_rang=("rank", "median"), Ø_block=("block", "mean"),
                                                 anteil_score_0=("score0", "mean")).round(2)
    print("\nZwillings-Quellen in der Liste ihres Jobs (Rang 1 = bester, 61 = letzter):\n", pos.to_string())

    # Beispiel Matched / Missing / Extra
    j, c = 0, int(S[0].argmax())
    r = score(jobs.loc[j, "labels"], liste.loc[c, "labels"])
    print(f"\nBeispiel: Job „{jobs.loc[j, 'position']}“ × bester CV „{liste.loc[c, 'position']}“ "
          f"(Score {r['score']:.2f}, Rang {ranking(S[j]).loc[c, 'rank']})")
    for key in ["matched", "missing", "extra"]:
        print(f"  {key:8s}: {label_names(r[key])}")


if __name__ == "__main__":
    main()
