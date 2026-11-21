# project_nobias

## ESCO Skill Extraction (MVP)

Skills aus beliebigem Text:

```
python scripts/esco_extractor.py --raw "Python, SQL, project management"
```

Skills aus zufälligem Djinni-CV:

```
python scripts/try_random_cv.py --seed 7
```

Strengerer Schwellwert (Default 0.5):

```
python scripts/try_random_cv.py --seed 7 --threshold 0.6
```

## Scoring der TF-IDF-Baseline

Berechnet TF-IDF-Scores (Cosinus) für jedes Dokument gegen jede Stelle und schreibt sie nach `data/processed/`. Im Repo-Hauptordner ausführen:

```
python scripts/build_scoring_inputs.py
python scripts/score_tfidf.py
```

`build_scoring_inputs.py` baut die gemeinsamen Eingaben (`scoring_docs.parquet`, `scoring_jobs.parquet`: Bewerberliste, Original-CVs, Zwillinge, Stellen). Es kann für weitere Methoden genutzt werden, ist aber nicht nötig: Jede Methode kann auch eigene Eingaben verwenden.

Ausgabe: `scores_tfidf.parquet` mit den Spalten `doc_id`, `job_id`, `score`, `methode` und `scores_tfidf_manifest.json` mit den Einstellungen. Eine weitere Methode (z. B. MeritMe) schreibt dasselbe Format als `scores_<methode>.parquet`. Dann lassen sich die Scores in den Notebooks direkt vergleichen. 