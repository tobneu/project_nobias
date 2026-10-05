# ESCO Skills

Diese Datei wird für `scripts/esco_extractor.py` benötigt:

```
data/raw/esco/skills_en.csv
```

## Wofür

ESCOX liefert pro Text nur ESCO-URIs, z. B.
`http://data.europa.eu/esco/skill/ccd0a1d9-afda-43d9-b901-96344886e14d`.
Über `skills_en.csv` werden diese URIs auf lesbare Labels (`preferredLabel`, z. B. „Python (computer programming)“) und den Skill-Typ (`skillType`: `knowledge` oder `skill/competence`) abgebildet.
Ohne die Datei gibt der Extractor Skills ohne Label aus.

## Woher

Die Datei ist Teil der offiziellen ESCO-Klassifikation der Europäischen Kommission. Der Download-Link wird per E-Mail zugeschickt.

1. https://esco.ec.europa.eu/en/use-esco/download öffnen
2. Auswählen:
   - Version: **v1.2.x**
   - Content: **Classification**
   - Language: **en**
   - Format: **CSV**
3. E-Mail-Adresse angeben und den Link aus der Mail öffnen
4. Aus dem ZIP die Datei `skills_en.csv` in diesen Ordner kopieren

Die Version muss zu ESCOX passen. v1.2 enthält alle ca. 13.900 Skills, die ESCOX (`esco-skill-extractor==0.1.18`) verwendet.

## Im Repo

`skills_en.csv` ist bewusst eingecheckt (ca. 9 MB), da die ESCO-Version im Projekt fix bleibt. Die Anleitung oben dient nur dazu, die Datei bei Bedarf neu zu beziehen.
