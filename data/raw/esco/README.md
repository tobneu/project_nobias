# ESCO-Klassifikation

Offizielle ESCO-Klassifikation (v1.2, Englisch, CSV) der Europäischen Kommission. Eingecheckt sind
nur die Dateien, die Code oder Notebooks im Projekt tatsächlich nutzen:

| Datei | Inhalt | Wofür im Projekt |
|---|---|---|
| `skills_en.csv` | ca. 13.900 Skills mit Label, Synonymen (`altLabels`), Typ und Beschreibung | `scripts/esco_extractor.py`: ESCOX liefert nur URIs, die Datei übersetzt sie in lesbare Labels |
| `occupations_en.csv` | ca. 3.000 Berufe mit ISCO-Gruppe und Definition | Definition der Ringe A/B/C im Jobmarkt (z. B. „data engineer“, ISCO 2511) |
| `occupationSkillRelations_en.csv` | Welche Skills ein Beruf braucht (`essential` / `optional`) | Keyword-Liste für die Auswahl der Jobs: was ein Data Engineer können muss, sagt ESCO, nicht wir |
| `digitalSkillsCollection_en.csv` | ca. 1.300 digitale Skills (ESCO-Sammlung) | IT-Filter für Skills |

Die übrigen Dateien aus dem Download bleiben lokal und sind per `.gitignore` ausgeschlossen.

## Woher

Der Download-Link wird per E-Mail zugeschickt.

1. https://esco.ec.europa.eu/en/use-esco/download öffnen
2. Auswählen:
   - Version: **v1.2.x**
   - Content: **Classification**
   - Language: **en**
   - Format: **CSV**
3. E-Mail-Adresse angeben und den Link aus der Mail öffnen
4. Die Dateien aus der Tabelle oben aus dem ZIP in diesen Ordner kopieren

Die Version muss zu ESCOX passen. v1.2 enthält alle ca. 13.900 Skills, die ESCOX
(`esco-skill-extractor==0.1.18`) verwendet.
