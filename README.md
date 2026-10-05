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