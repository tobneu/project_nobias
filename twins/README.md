# twins: kontrafaktische CV-Zwillinge

Dieser Ordner enthält Prompts, Skripte und Dokumentation für die LLM-erzeugten CV-Zwillinge. Ein Zwilling ist ein CV mit denselben Skills, bei dem genau ein Stilmerkmal (Proxy) verändert wurde.

## Varianten
| Variante | Was sich ändert |
|---|---|
| `edu` | Bildungsweg (academic, certification, self_taught); ersetzt eine vorhandene Bildungsangabe oder fügt eine hinzu |
| `lin` | Linearität der Laufbahn (linear, non_linear), über eine feste Zeile unter dem Titel |
| `tone` | Ton (confident, hedged), nur Bewertungswörter, Tätigkeiten und Ergebnisse bleiben unverändert |
| `para` | Paraphrase ohne inhaltliche Änderung, dient als Rauschgrenze |
| `all` | Kombination der drei Proxies, die „realistischen Zwillinge“ für den Vergleich MeritMe gegen TF-IDF |

Jeder Zwilling muss alle Anker (Skill-Begriffe des CVs) wörtlich enthalten, den Titel unverändert lassen und darf nichts erfinden.

## Ergebnis auf einen Blick
- **Pilot:** 12 CVs, 60 Zwillinge, manuell bewertet. Alle Kriterien erfüllt, Prompt-Version v2 eingefroren.
- **Vollauf:** 600 Zwillinge aus 120 Quell-CVs, Prompt v2 unverändert, Kriterien und Entscheidungsregeln in `vollauf/protokoll_vollauf.md`.
- **Zwillingsdatei für das Scoring:** `data/processed/twins_vollauf_v2.parquet` (nur verwendbare Zwillinge, Spalten: `twin_id`, `cv_id`, `id`, `ring`, `test`, `variante`, `richtung`, `assigned_job_id`, `text_zwilling`).

## Struktur
```
prompts/                         Rahmen und Vorlagen je Version (v1, v2)
prompts/CHANGELOG.md             jede Änderung mit Grund und Test-ID
src/                             Skripte (siehe unten)
keywords.pkl                     Keyword-Muster für die Anker               (nicht in Git)

pilot/testlog.csv                eine Zeile pro Funktionstest
pilot/freeze_kriterien.md        Kriterien für den Pilot, vor dem Pilot festgelegt
pilot/pilot_cvs.csv              die 12 Pilot-CVs (IDs und Kennzahlen, ohne Text)
pilot/cvs/                       CV-Texte und Anker: <cv_id>.txt, <cv_id>.anchors.txt   (nicht in Git)
pilot/raw/                       Prompt und unveränderte Modellantwort pro Test         (nicht in Git)

vollauf/protokoll_vollauf.md     Kriterien und Entscheidungsregeln des Vollaufs
vollauf/manifest.json            Prompt-Version, Prompt-Hash, Modell, Startwert
vollauf/vollauf_cvs.csv          die 120 Quell-CVs (IDs und Kennzahlen, ohne Text)
vollauf/vollauf_plan.csv         Plan: Zwilling, Variante, Richtung
vollauf/vollauf_ergebnis.csv     Ergebnis pro Zwilling (Status, Prüfwerte, Urteil)
vollauf/stichprobe.csv           die 60 manuell geprüften Zwillinge
vollauf/vollauf_zwillinge_uebersicht.csv   Tabelle ohne Texte
vollauf/cvs/                     CV-Texte und Anker                         (nicht in Git)
vollauf/raw/                     Prompt und unveränderte Modellantwort      (nicht in Git)
vollauf/vollauf_zwillinge.parquet   Zwillingstabelle mit Texten             (nicht in Git)
```

## Skripte
| Skript | Zweck |
|---|---|
| `src/twin_tools.py` | Prompt bauen, Antwort lesen, Zwilling automatisch prüfen (Anker, Länge, Änderungsanteil) |
| `src/run_test.py` | Ablauf der Funktionstests: `setup`, `prompt`, `check` |
| `src/select_pilot_cvs.py` | Wählt die 12 Pilot-CVs per Zufall mit festem Startwert (2026) |
| `src/extract_anchors.py` | Erzeugt die Anker der Pilot-CVs automatisch mit den Keyword-Mustern aus `keywords.pkl` |
| `src/generate_pilot.py` | Erzeugt die Pilot-Zwillinge |
| `src/review_pilot.py` | Manuelle Bewertung der Pilot-Zwillinge und Auswertung der Pilotkriterien |
| `src/vollauf_select.py` | Wählt die 120 Quell-CVs (`role == "zwilling_quelle"`), legt `vollauf/vollauf_cvs.csv` und `vollauf/cvs/` an |
| `src/vollauf_anchors.py` | Erzeugt die Anker der Vollauf-CVs |
| `src/vollauf_generate.py` | Kommandos `plan`, `run`, `status`, `check`, `stichprobe`, `zeichen`; Erzeugung wiederaufnehmbar |
| `src/vollauf_review.py` | Manuelle Prüfung der Stichprobe (60 Zwillinge), `--auswertung` prüft die Kriterien |
| `src/vollauf_export.py` | Erzeugt die Zwillingstabelle (Parquet, lokal) und die Übersicht ohne Text |

Alle Befehle im Ordner `twins` ausführen.

## Ablauf
1. **Funktionstest (abgeschlossen):** drei Test-CVs (Liste, Prosa, kurz). Runde 1 mit v1 (T01 bis T15), Runde 2 mit v2 (T16 bis T26). Ergebnis und Entscheidungen stehen im Changelog.
2. **Pilot (abgeschlossen):** 12 neue CVs, fünf Zwillinge pro CV, manuell bewertet. Kriterien in `pilot/freeze_kriterien.md`. Alle Kriterien erfüllt, v2 eingefroren (Manifest mit Modell, Datum, Prompt-Hash).
3. **Vollauf (abgeschlossen):** 120 Quell-CVs aus Tobis Datensatz, 600 Zwillinge, Erzeugung skriptgesteuert und wiederaufnehmbar, automatische Prüfungen für alle Zwillinge, manuelle Stichprobe von 60. Protokoll: `vollauf/protokoll_vollauf.md`.

## Funktionstest: pro Test (z. B. T27)
1. `python src/run_test.py prompt T27` baut den Prompt und speichert `pilot/raw/T27_prompt.txt`.
2. Prompt in eine neue, leere Sitzung geben (eine Sitzung pro Test).
3. Antwort unverändert als `pilot/raw/T27.json` speichern.
4. `python src/run_test.py check T27` prüft den Zwilling und fragt die Bewertung ab (Modell, ein Merkmal, erfunden, natürlich, Urteil, Problem, Konsequenz). Das Ergebnis geht ins Testlog.

Das Testlog nicht in Excel öffnen, solange ein Skript darauf schreibt.

## Pilot: Vorbereitung
1. In `eda_jobmarket_final.ipynb` alle Zellen bis zu `KEYWORDS = {...}` ausführen, darunter eine Zelle, die `KEYWORDS` nach `keywords.pkl` speichert.
2. `python src/select_pilot_cvs.py` wählt die CVs und legt `pilot/pilot_cvs.csv` und `pilot/cvs/<cv_id>.txt` an.
3. `python src/extract_anchors.py` legt `pilot/cvs/<cv_id>.anchors.txt` an. Die Anker vorab kurz ansehen.

## Vollauf: Ablauf
1. `python src/vollauf_select.py` wählt die Quell-CVs und legt `vollauf/vollauf_cvs.csv` und `vollauf/cvs/<cv_id>.txt` an.
2. `python src/vollauf_anchors.py` legt `vollauf/cvs/<cv_id>.anchors.txt` an.
3. `python src/vollauf_generate.py plan` erstellt den Plan. Das Skript bricht ab, wenn der Hash der Prompt-Dateien vom Pilot-Manifest abweicht.
4. `python src/vollauf_generate.py run` erzeugt die Zwillinge. Der Lauf kann abgebrochen und fortgesetzt werden, `status` zeigt den Stand.
5. `python src/vollauf_generate.py check`, `zeichen` und `stichprobe` prüfen alle Zwillinge automatisch und ziehen die Stichprobe (einmalig, Startwert 2026).
6. `python src/vollauf_review.py` für die manuelle Prüfung der Stichprobe, danach `--auswertung`.
7. `python src/vollauf_export.py` schreibt die Zwillingstabelle und die Übersicht.

Benötigte Daten (nicht in Git, außer der Zwillingsdatei): `data/processed/jobmarket_data-engineer_180cv_2026-10-20.parquet` mit der Rolle `zwilling_quelle`) und `data/raw/djinni/cv_profiles_en.parquet`.

## Regeln
- Eine Prompt-Version ändert sich nur mit Eintrag im Changelog (Änderung, Grund, Test-ID des Befunds). Maximal drei Versionen pro Variante.
- Länge ist ein Flag und kein Verwerfungsgrund. Erfundene Inhalte und abgeschwächte Kompetenzaussagen sind es.
- Kriterien des Piloten werden nach Beginn nicht mehr geändert. Abweichungen kommen ins Abweichungsprotokoll in `pilot/freeze_kriterien.md`.
- Die Kriterien des Vollaufs stehen in `vollauf/protokoll_vollauf.md` und wurden vor dem Lauf festgelegt.

## Reproduzierbarkeit und Einschränkungen
Die Zwillinge werden mit einem Sprachmodell über Chat bzw. Claude Code erzeugt, ohne API. Daraus folgt:
- **Die Erzeugung ist nicht reproduzierbar.** Temperatur und Zufallsstartwert sind nicht steuerbar. Derselbe Prompt liefert bei einem zweiten Lauf einen anderen Zwilling. Ein erneuter Lauf stellt den Datensatz also nicht wieder her.
- **Das Modell kann sich ändern.** Der Anbieter kann Modellversionen austauschen, und innerhalb einer Sitzung kann ein anderes als das eingestellte Modell antworten. Der Modellname wird pro Zwilling so festgehalten, wie er angegeben wurde, und ist keine geprüfte Angabe.
- **Der Datensatz ist deshalb ein Artefakt.** Maßgeblich sind die gespeicherten Rohantworten (`pilot/raw/`, `vollauf/raw/`) und die Zwillingstabelle, nicht die Prompts allein. Diese Daten werden archiviert und nicht neu erzeugt.
- **Was dokumentiert wird:** Modellname und Datum pro Zwilling, Hash der Prompt-Dateien im Manifest, unveränderte Rohantworten, Anzahl der Neugenerierungen, automatische Prüfergebnisse und Flags.
- **Was reproduzierbar bleibt:** CV-Auswahl (fester Startwert) und Anker-Extraktion.
- **Folge für die Aussage:** Die Ergebnisse gelten für diesen einen Satz erzeugter Zwillinge. Die Streuung zwischen möglichen Läufen ist nicht gemessen. Die Paraphrase-Kontrolle (`para`) erfasst einen Teil dieses Rauschens, ersetzt aber keine Wiederholung. Das gehört als Einschränkung in den Bericht.
