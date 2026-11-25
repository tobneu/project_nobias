# Freeze-Kriterien für den Pilot (Prompts v2)

Status: Entwurf, wird mit der Freigabe unten verbindlich.
Erstellt: 29.10.2026, vor Beginn des Pilots und vor Sicht auf Pilot-Zwillinge.
Gilt für: Projekt MeritMe, Bericht für Applied AI Lab „Style Effects in TF-IDF-Based CV Matching“.

Diese Kriterien werden nach Beginn des Pilots nicht mehr geändert. Jede Abweichung wird im Abweichungsprotokoll (Abschnitt 10) mit Datum und Begründung festgehalten.

## 1. Zweck
Der Pilot prüft, ob die Prompts v2 auf neuen CVs stabil funktionieren. Er entscheidet, ob v2 für den Vollauf eingefroren wird oder ob eine einzelne Variante überarbeitet werden muss. Der Pilot ist keine inhaltliche Auswertung der Effekte.

## 2. Feste Rahmenbedingungen
- Prompts: Version v2 (`prompts/v2/`), unverändert. Der Hash der Prompt-Dateien wird vor dem Start im Manifest festgehalten.
- Modell: Claude Sonnet 5.5. Modellname und Datum werden pro Zwilling gespeichert. Die Temperatur ist nicht steuerbar, das wird im Bericht als Einschränkung genannt.
- Jeder Zwilling wird in einer eigenen, frischen Sitzung ohne Vorgeschichte erzeugt.
- Richtungen werden vom Skript mit festem Zufallsstartwert zugewiesen und gleichmäßig verteilt (edu: je 4 pro Richtung, lin und tone: je 6 pro Richtung).
- Anker werden automatisch mit Regex aus eda_jobsmarket.ipynb aus dem CV extrahiert, nicht von Hand.

## 3. Stichprobe

**Ziel:** 12 CVs, an denen der Pilot prüft, ob die Prompts auch auf unbekannten CVs zuverlässig funktionieren.

**Woher die CVs kommen:** Aus den Djinni-CVs, die bisher in keinem Teil des Projekts verwendet werden. Ausgeschlossen sind:
- die drei CVs aus dem Funktionstest (036d40ed, e26ee3f2, 222d5f74),
- der gesamte Markt-Datensatz von Tobi (die Jobs, die Bewerberliste und die 120 CVs, aus denen im Vollauf die Zwillinge entstehen).

Damit liegen die Pilot-CVs sicher nicht unter den Quell-CVs des Vollaufs. Das ist Absicht: Die Prompts sollen nicht an denselben CVs geprüft werden, an denen sie später eingesetzt werden. Sonst sagt die Erfolgsquote im Pilot weniger über den Vollauf aus.

Nur englische CVs aus den drei Berufsfeldern A (Data Engineer), B (Python) und C (QA Automation).

**Aufteilung:** 4 CVs pro Berufsfeld. In jedem Berufsfeld gibt es
- einen Listen-CV (Aufzählung von Skills, 60 bis 100 Wörter),
- einen Prosa-CV (Fließtext, 120 bis 200 Wörter),
- einen kurzen CV (30 bis 59 Wörter),
- einen vierten CV (Berufsfeld A: Liste, B: Prosa, C: kurz).

Insgesamt sind das 4 Listen-, 4 Prosa- und 4 kurze CVs.

**Auswahl:** Zufällig per Skript (`src/select_pilot_cvs.py`) mit festem Startwert 2026, nicht von Hand. So ist die Auswahl nachvollziehbar und nicht davon beeinflusst, welche CVs besonders gut passen würden. Die gezogenen CV-IDs werden vor der Erzeugung der Zwillinge in `pilot/pilot_cvs.csv` gespeichert.

## 4. Zwillingsplan
Pro CV fünf Zwillinge: edu, lin, tone, para, all (Richtung benachteiligt). Gesamt 60 Zwillinge.
Falls das Team für den Vollauf auch die Richtung begünstigt bei `all` vorsieht, kommen vier weitere Zwillinge hinzu (all/begünstigt, je einer pro Zwillingstyp und CV-Typ). Entscheidung im Team vor Pilotstart.

## 5. Automatische Prüfungen
Harte Fehler (Zwilling wird neu erzeugt, höchstens zwei Neugenerierungen):
- Antwort ist kein gültiges JSON.
- Ein Anker fehlt. Geprüft wird, ob der Anker als Zeichenfolge im Zwilling vorkommt, ohne Beachtung der Groß- und Kleinschreibung. Eine andere Schreibweise (zum Beispiel ein Zeichen oder ein Wort anders) zählt als fehlend.
- Der Titel (erste Zeile) ist verändert.
- Die Zeichenkodierung ist beschädigt (Kodierungsreste wie "ï¿½", "â€", "Ã" oder das Ersatzzeichen U+FFFD im Zwilling). Eingeführt am 8.11.2026, nachdem beim Pilotstart ein Kodierungsfehler im Aufruf aufgetreten war (siehe Abweichungsprotokoll).

Flags (werden gespeichert, führen nicht zum Verwerfen):
- Länge außerhalb der Toleranz. Toleranz für `edu`, `lin`, `tone` und `para`: ±20 % und höchstens 10 Wörter Spielraum bei kurzen CVs. Für `all`: ±30 % und 15 Wörter, weil drei Änderungen zusammenkommen.
- Änderungsanteil (Anteil geänderter Wörter).
- `proxies_angewendet` (bei `all`: welche der drei Proxies tatsächlich geändert wurden). Im Pilot wurde diese Angabe nicht automatisch gefüllt, sondern in der manuellen Bewertung beurteilt (Spalten `ein_proxy` und `problem`).

## 6. Manuelle Bewertung und Befund-Definition
Alle 60 Zwillinge werden von Hand geprüft, mit denselben Fragen wie im Testlog: nur das gewollte Merkmal geändert, nichts erfunden, natürlicher Text, Urteil, Problem.

Als Befund zählt:
- erfundener Inhalt (Aussage, Station, Zahl, Tool, Unsicherheitsformel, die im CV nicht steht),
- abgeschwächte oder verstärkte Tätigkeit, Kompetenz oder Ergebnis,
- ungewollt geänderter zweiter Proxy,
- geändertes Formular- oder Grußelement ohne Auftrag,
- unnatürlicher Text, der als Zwilling nicht glaubwürdig wäre.

Kein Befund (nur Beobachtung):
- Kurz-CV bei `all` wird deutlich länger.
- Ton bei `all` nicht anwendbar, weil der CV keine Selbstbeschreibung und keinen Suchsatz enthält.
- Geringer Tonwechsel bei hedged.
- Glättung oder Wortwahl bei `para` im Rahmen des Rauschens.

## 7. Kriterien
Der Pilot gilt als bestanden, wenn alle folgenden Punkte erfüllt sind:
1. Mindestens 54 von 60 Zwillingen (90 %) ohne Befund.
2. Pro Variante (edu, lin, tone, para, all) mindestens 10 von 12 Zwillingen ohne Befund.
3. Keine erfundenen Inhalte in den akzeptierten Zwillingen.
4. Kein fehlender Anker und keine Titeländerung in den akzeptierten Zwillingen.
5. Höchstens 12 von 60 Zwillingen (20 %) brauchten eine Neugenerierung, und höchstens zwei Zwillinge scheitern auch nach zwei Neugenerierungen.

## 8. Entscheidungsregel
- Alle fünf Kriterien erfüllt: v2 wird eingefroren (Manifest mit Modell, Datum, Prompt-Hash). Danach folgt der Vollauf.
- Eine Variante verfehlt Kriterium 2 oder 3: nur diese Variante bekommt eine v3. Die Prüfung dieser Variante wird mit sechs neuen CVs wiederholt, nicht mit denselben.
- Maximal drei Prompt-Versionen pro Variante. Besteht auch v3 nicht, wird die Variante aus der Hauptauswertung genommen und im Bericht als Einschränkung genannt.
- Kriterium 1 oder 5 verfehlt, aber alle Varianten einzeln bestanden: Ursache in den Befunden suchen, Entscheidung im Team.

## 9. Zusatzfrage für den Pilot
Verschiebt `hedged` die Ähnlichkeit zur Stellenbeschreibung messbar stärker als die Rauschgrenze `para`? Dazu wird pro Zwilling die Veränderung des Scores gegenüber dem Original berechnet und nach Variante und Richtung beschrieben (deskriptiv, ohne Signifikanztest, da je Gruppe nur 6 bis 12 Werte). Ist hedged kaum von para zu unterscheiden, wird vor dem Vollauf im Team über mehr Spielraum für Selbstbeschreibungen in hedged entschieden (mögliche v3).

## 10. Abweichungsprotokoll

**1. Zeichenkodierung (8.11.2026).** Die ersten Zwillinge enthielten Kodierungsreste ("ï¿½"), weil der Aufruf des Modells unter Windows nicht als UTF-8 lief. Korrektur: `encoding="utf-8"` im Aufruf und Kodierungsreste als harter Fehler (Abschnitt 5). Betroffene Zwillinge wurden verschoben und neu erzeugt. Der Prüfbefehl `zeichen` meldet 15 Zwillinge mit Sonderzeichen im Original (•, ’, geschütztes Leerzeichen). In keinem wurde ein Kodierungsrest gefunden, daher keine weitere Neuerzeugung.

**2. Modell (8.11.2026).** Die ersten drei Zwillinge entstanden mit dem Standardmodell der CLI. Sie wurden nach `pilot/raw/modelltest/` verschoben und mit `--cli-model sonnet` neu erzeugt. Das Modell-Label in der Dokumentation ist eine Angabe der Bearbeiterin und wird nicht automatisch geprüft. Die Erzeugung ist nicht reproduzierbar (keine Steuerung der Temperatur über die CLI), das gilt als Limitation.

**Pilot-Ergebnis (8.11.2026):** 60 Zwillinge (12 CVs × 5 Varianten, Prompts v2) wurden erzeugt und vollständig manuell bewertet. 58 von 60 ohne Befund (edu 11/12, lin 12/12, tone 12/12, para 12/12, all 11/12). Keine erfundenen Inhalte, kein fehlender Anker, keine Titeländerung, keine Neugenerierung, kein Fehlschlag. Alle fünf Kriterien sind erfüllt.

**Entscheidung:** Prompts v2 werden für den Volllauf eingefroren.

**Befunde:** Zwei Befunde, beide beim CV 690dd958: Die feste Bildungszeile widerspricht dem vorhandenen M.Sc. (edu, all).

**Beobachtungen für Auswertung und Limitationen:**
- Bei vier `all`-Zwillingen Längen-Flag (Kurz-CVs, +32 bis +46 %).
- Tone wurde bei fünf `all`-Zwillingen nicht angewendet, davon vier berechtigt (keine wertende Selbstbeschreibung), einer zu streng ("Skilled in").
- Ein Fall mit Tone-Überschuss ("huge" zu "fairly good").
- `edu` und `lin` ergänzen nur Zeilen.

**Offene Punkte vor dem Volllauf:** Behandlung von CVs mit vorhandenem Abschluss (edu), Spielraum beim Hedgen (tone). Entscheidung im Team.

