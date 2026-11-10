# Protokoll für den Vollauf (Zwillingsgenerierung)

Status: Entwurf, wird mit der Freigabe unten verbindlich.
Erstellt: 8.11.2026, nach Abschluss des Pilots und vor der Erzeugung des ersten Vollauf-Zwillings.
Gilt für: Projekt MeritMe, Bericht „Style Effects in TF-IDF-Based CV Matching“.

Dieses Protokoll gilt für den Vollauf. Der Pilot ist abgeschlossen und eingefroren (`prompts/freeze_kriterien.md`, Commit `7cf0f3f`). Nach Beginn des Vollaufs werden die Punkte unten nicht mehr geändert. Abweichungen kommen mit Datum und Begründung in Abschnitt 8.

## 1. Zweck
Der Vollauf erzeugt die Zwillinge für die Hauptauswertung. Er ändert weder Prompts noch Kriterien, sondern wendet die im Pilot freigegebenen Prompts v2 auf alle Quell-CVs an und prüft die Qualität.

## 2. Feste Rahmenbedingungen
- Prompts: Version v2 (`prompts/v2/`), unverändert. Das Skript bricht ab, wenn der Prompt-Hash (`23972a71e9c10c6e`) vom Pilot-Manifest abweicht.
- Modell: Claude Sonnet 5.5 über die Claude Code CLI (`--cli-model sonnet`). Modellname und Datum werden pro Zwilling gespeichert. Das Modell-Label ist eine Angabe und wird nicht automatisch geprüft. Die Temperatur ist nicht steuerbar, die Erzeugung ist nicht reproduzierbar (Limitation im Bericht).
- Jeder Zwilling wird in einer eigenen Sitzung in einem leeren Verzeichnis erzeugt, ohne Vorgeschichte.
- Zufallsstartwert für Richtungszuweisung und Stichprobe: 2026.
- Anker werden automatisch mit Tobis Keyword-Mustern aus dem CV extrahiert (`keywords.pkl`), nicht von Hand.

## 3. Umfang
- Quell-CVs: die 120 CVs mit `role == "zwilling_quelle"` aus Job-Markt (`jobmarket_data-engineer_180cv_2026-10-20.parquet`): Ring A 70, Ring B 30, Ring C 20. Ring A und B bilden den Haupttest, Ring C die Kontrolle.
- Keine Überschneidung mit den 12 Pilot-CVs (wird vom Skript geprüft).
- Pro CV fünf Zwillinge: `edu`, `lin`, `tone`, `para`, `all`. Gesamt 600 Zwillinge.
- Richtungen werden vom Skript getrennt je Ring gleichmäßig verteilt (edu: academic, certification, self_taught; lin: linear, non_linear; tone: confident, hedged).
- `all` immer in der Richtung benachteiligt. Die Richtung begünstigt gehört nicht zum Vollauf.

## 4. Automatische Prüfungen (alle 600 Zwillinge)
Harte Fehler (Zwilling wird neu erzeugt, höchstens zwei Neugenerierungen):
- Antwort ist kein gültiges JSON.
- Ein Anker fehlt (Prüfung ohne Beachtung der Groß- und Kleinschreibung).
- Der Titel (erste Zeile) ist verändert.
- Die Zeichenkodierung ist beschädigt.

Flags (werden gespeichert, führen nicht zum Verwerfen): Länge außerhalb der Toleranz, Änderungsanteil, `proxies_angewendet`. Länge und Änderungsanteil gehen als Kovariaten in die Auswertung, zusätzlich eine Sensitivitätsanalyse ohne CVs unter 50 Wörtern.

## 5. Manuelle Bewertung (Stichprobe)
- Nach vollständiger Erzeugung wird einmalig eine Stichprobe gezogen (`vollauf_generate.py stichprobe`): je Variante 12 Zwillinge, geschichtet nach Ring (A 7, B 3, C 2), zusammen 60 Zwillinge. Die Ziehung ist per Startwert reproduzierbar und wird nicht wiederholt.
- Die Stichprobe wird mit denselben Fragen und derselben Befund-Definition bewertet wie im Pilot (`prompts/freeze_kriterien.md`, Abschnitt 6).

## 6. Kriterien
Der Vollauf gilt als bestanden, wenn alle Punkte erfüllt sind:
1. Mindestens 54 von 60 Stichproben-Zwillingen (90 %) ohne Befund.
2. Pro Variante mindestens 10 von 12 Stichproben-Zwillingen ohne Befund.
3. Keine erfundenen Inhalte in den akzeptierten Zwillingen der Stichprobe.
4. In allen 600 Zwillingen: kein fehlender Anker, keine Titeländerung, keine Kodierungsreste.
5. Höchstens 60 von 600 Zwillingen (10 %) brauchten eine Neugenerierung, und höchstens 6 scheitern auch nach zwei Neugenerierungen.

## 7. Entscheidungsregel
- Alle Kriterien erfüllt: Die Zwillinge gehen in die Auswertung (Manifest einfrieren, Scoring, Statistik).
- Eine Variante verfehlt Kriterium 2 oder 3: Die Stichprobe dieser Variante wird mit einer zweiten Ziehung von 12 Zwillingen (neuer Startwert 2027, ohne Zurücklegen) erweitert. Liegt die Befundquote der 24 Zwillinge über 20 %, wird nur diese Variante überarbeitet (v3, höchstens drei Versionen pro Variante), für alle 120 CVs neu erzeugt und erneut mit 12 neuen Zwillingen geprüft. Die übrigen Varianten bleiben unverändert.
- Besteht auch v3 nicht, wird die Variante aus der Hauptauswertung genommen und als Einschränkung berichtet.
- Kriterium 4 oder 5 verfehlt: Ursache in den Rohantworten suchen, Entscheidung im Team, Eintrag in Abschnitt 8.

## 8. Abweichungsprotokoll
| Datum | Abweichung | Begründung |
|---|---|---|
| | | |
