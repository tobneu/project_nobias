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

## Jobmarkt (Datenbasis für Ziel 1)

Fester Markt für die Zwillingstests: 20 Data-Engineering-Jobs, eine Bewerberliste aus 60 CVs
(20 Kern / 20 Rand / 20 Außen) und 120 Zwillings-Quellen (70 / 30 / 20).

**Datei:** `data/processed/jobmarket_data-engineer_180cv_2026-10-20.parquet` – eine Zeile pro Dokument,
Spalten erklärt in Abschnitt 11 des Notebooks.

### Wie er entsteht

Notebook `notebooks/eda_jobmarket_final.ipynb` (Kernel: MeritMe-Env, Laufzeit ca. 2 Minuten):

1. Nur englische Djinni-CVs und -Jobs
2. Drei Ringe = ESCO-Berufsfamilien: A Data Engineering, B Softwareentwicklung (Djinni: Python),
   C Softwaretest (Djinni: QA Automation). Ausgestochen wird über das `Primary Keyword`.
3. Keyword-Liste pro Ring aus zwei Sichten: Skills der ESCO-Berufe + prägende TF-IDF-Begriffe der Ring-Jobs
4. Filter: Jobs nennen die Rolle im Titel, Jobs und CVs enthalten ≥ 5 Keywords ihrer Ring-Liste
5. Zufällige Ziehung (Seed 42) – kein Score von MeritMe oder TF-IDF entscheidet über die Auswahl
6. ESCOX-Labels und Score-Spreizung nur zur Kontrolle

![Auswahlpipeline](docs/img/Djinni%20ESCO%20Jobmarket%20Dataset%20Pipeline-2026-10-20-170003.png)

### Ansehen

Interaktive Tabelle (filtern, Spalten ausblenden, Volltextsuche, inkl. CV- und Jobtexte):

```
python scripts/jobmarket_to_html.py
xdg-open data/processed/jobmarket_data-engineer_180cv_2026-10-20.html
```

Qualitative Analyse (Gruppen, Labels, Matching, Bereitschaft für Stufe 1):

```
python scripts/analyze_jobmarket.py                 # Grundanalyse
python scripts/analyze_jobmarket.py --perturb       # + ESCOX-Vorabtest für Stufe 1
python scripts/analyze_jobmarket.py --occupations   # + ESCO-Occupations und Mini-Zwillingstest
```