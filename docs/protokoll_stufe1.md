# Protokoll Stufe 1: Label-Stabilität

Ergebnis vom 25.11.2026: **bestanden**

## Kriterium

Laut Erfolgskriterien: mittlerer Jaccard ≥ 0,85 zwischen den ESCO-Labels von Original und Zwilling, im Mittel ≥ 5 Labels
pro CV. Geprüft auf den 100 `all`-Zwillingen des Haupttests (Ring A + B), bei denen Bildungsweg, Laufbahn und Ton
gleichzeitig verändert sind. Gemessen wird nur ESCOX (korrigierte Zerlegung, nur IT-Skills), weil die Wortsuche durch die
wörtlich erhaltenen Skill-Begriffe ohnehin stabil ist.

Die Methode (`scripts/matching.py`, Commit `8c169b6`) stand vor den Zwillingen (Commit `c68a26f`) fest und ist seitdem
unverändert.

## Ergebnis

| Labels | Mittlerer Jaccard |
|---|---|
| **ESCOX mit Fix, nur IT (Gate)** | **0,996** |
| Hybrid | 0,997 |
| ESCOX unverändert | 0,814 |

8,2 Labels pro CV, kein Paar ohne Labels.

Unverändertes ESCOX wäre gescheitert, weil es aus den Sätzen zum Bildungsweg Soft Skills herausliest. Die Einschränkung
auf IT-Skills filtert sie heraus.

Skript: `scripts/stufe1.py`, Ausgabe: `docs/stufe1_ausgabe.txt`, Zwillinge: `data/processed/twins_vollauf_v2.parquet`
(SHA-256 `a94d5c9b…0221d`).

## Grenzen

- Die Zwillinge übernehmen die Skill-Begriffe wörtlich, ein Teil der Stabilität kommt daher.
- Verglichen wird Original gegen Zwilling, nicht Zwilling gegen Zwilling.

## Konsequenz

Die Extraktion bleibt unverändert, ein Wechsel auf MeritMe-ESCOX ist nicht nötig.
