# Prompt-Changelog

## v1 (27.10.2026) Ausgangsversion
- Rahmen + Vorlagen edu / lin / tone / para. Das Skript weist die Richtung zu und zeigt dem Modell nur diese.
- edu: drei feste Sätze (academic / certification / self_taught).
- lin: linear / non_linear mit generischen Aussagen, ohne Namen und Zahlen.
- tone: confident / hedged, nur Wortwahl, keine neuen Fakten.
- para: Umformulieren als Kontrolle, keine Richtung.
- Grundlage: eigene Proxy-EDA (Bildungsmarker, Tonalitäts-Merkmale).

- Ergänzt (28.10.): Vorlage `all` (kombiniert: self_taught + non_linear + hedged, Längengrenze ±30 %). Bestehende Module unverändert.

## v2 (28.10.2026)
Grundlage: Funktionstest mit 15 Tests (T01-T15) an drei CVs, siehe pilot/testlog.csv.

| Befund (Test-ID) | Änderung in v2 |
|---|---|
| hedged schwächt Tätigkeiten und Ergebnisse ab ("tried to deploy", "trying to lead", "might have increased"): T07, T11, T13, T14, T15 | Rahmenregel 6 (Getanes bleibt getan, Zahlen, Dauer, Rollen unverändert). tone/hedged darf nur Selbstbeschreibung und Wünsche abschwächen, mit Beispielen. |
| erfundene Zweifel und Wertungen ("though I might be wrong", "although I might not have done it perfectly", "a few small projects"): T14, T15 | Rahmenregel 4 ergänzt (keine Meinungen, Zweifel, Lob oder Selbsteinschätzungen); tone und all verbieten Qualitätszweifel ausdrücklich. |
| Ich-Form eingeführt, obwohl der CV keine hat: T15 | hedged: Ich-Form nur, wenn das Original sie schon nutzt (Abweichung von v1, bewusste Entscheidung, siehe unten). |
| lin/linear lang und wertend ("steadily forward", etwa doppelt so lang wie non_linear): T06 | lin: feste Sätze statt Beispielen, "Previously worked in customer support before moving into IT." und "Continuous career within IT.", Platz direkt unter dem Titel. |
| Gruß verändert ("Good afternoon!" -> "Hello!"): T14 | Rahmenregel 3: Grüße und Schlusszeilen unverändert. |
| Singular/Plural und Satzbau driften ("application"->"applications"): T03, T04, T08 | Rahmenregel 6: Singular/Plural, Zeit, Zahlen wie im Original. |
| Modell glättet Grammatik und Rechtschreibung ("a new experiences" -> "new experiences"): T08, T12, T14, T15 | Rahmenregel 7: Fehler des Originals nicht korrigieren, Sprache nicht polieren. Gilt auch für para, damit die Kontrolle dasselbe Rauschen misst wie die Tonzwillinge (Abweichung von v1, bewusste Entscheidung). |
| Leerzeilen im Text | Rahmenregel 8: Zeilenumbrüche und Leerzeilen wie im Original. |
| JSON ungültig durch Anführungszeichen in what_changed: T09 | Rahmen: Anführungszeichen maskieren, in what_changed nur einfache. |
| Längenvorgabe zu eng für kurze CVs, bei all zu streng: T10, T13, T15 | Länge ist Richtwert, kein Ablehnungsgrund. Spielraum mindestens 10 Wörter (all: 15). Das Längenverhältnis wird im Testlog gespeichert. Gesamteffekt und längenbereinigter Effekt werden in der Auswertung getrennt berichtet. |
| all nur als Worst Case | all hat zwei Richtungen: benachteiligt (self_taught, non_linear, hedged) und beguenstigt (academic, linear, confident). Welche eingesetzt wird, ist offen. |

Unverändert: edu (T01, T05, T09 unauffällig); die festen Bildungssätze bleiben.
Technisch: Das Skript nimmt den Prompt aus dem Ordner der Version, die in der Spalte prompt_version steht.

Offen:
- all bei CVs unter etwa 60 Wörtern (T15) prüfen: Wenn auch v2 dort scheitert, kurze CVs bei all ausnehmen.
- lin/linear passt nicht, wenn der CV schon einen Branchenwechsel beschreibt.
- Richtung von all (nur benachteiligt oder gemischt) mit Tobi und Nadia klären.

Kriterien Runde 2 (festgelegt vor Testbeginn):
- hedged und all: keine abgeschwächte Tätigkeit, keine erfundenen Zweifel
- lin: genau der feste Satz, sonst nichts
- Gruß und Grammatikfehler des Originals bleiben
- JSON gültig, kein Fallback-Hinweis im Check
- kein Anker fehlt, nichts erfunden
- mindestens 9 von 11 Tests ohne Befund
edu: nur Stichprobe (T26), Modul unverändert.

## v2 – Runde 2 (29.10.2026): Funktionstest mit Prompts v2
Tests T16–T26, Claude Sonnet 5.5 (Chat), drei Test-CVs (Liste 036d40ed, Prosa e26ee3f2, kurz 222d5f74). edu nur als Stichprobe (T26), da unverändert; T27/T28 bewusst nicht durchgeführt.

### Kriterien (vor Runde 2 festgelegt)
Mindestens 9 von 11 Tests ohne Befund. Kein verlorener Anker, nichts Erfundenes, Tätigkeiten und Ergebnisse unverändert, Antwort als gültiges JSON.
Präzisierung bei der Auswertung: Als Befund zählt nur, was auf den Prompt zurückgeht. Designbedingte Einschränkungen (T22, T24) zählen nicht, sind aber unten aufgeführt.

### Ergebnis
| | v1 (15 Tests) | v2 (11 Tests) |
|---|---|---|
| ok | 8 | 8 |
| ok mit Einschränkung | 5 | 3 (T22, T24, T25) |
| verworfen | 2 (T14, T15) | 0 |

Prompt-bedingte Befunde in v2: 1 (T25). Damit sind 10 von 11 Tests ohne prompt-bedingten Befund, das Kriterium ist erfüllt. v2 gilt als Pilot-Kandidat; eine v3 wird vor dem Pilot nicht erstellt.

### Befunde aus v1, die in v2 nicht mehr auftreten
- Abgeschwächte Tätigkeiten und Ergebnisse (T07, T11, T13, T14, T15): in T20, T21, T23 bleiben „deployed“, „leading a project“ und „Team Lead“ unverändert.
- Erfundene Zusätze (T14, T15): keine.
- Ungültiges JSON (T09): nicht aufgetreten.
- Zu langer linear-Satz (T06): T17 liegt bei 132 statt 148 Wörtern.

### Beobachtungen ohne Prompt-Änderung
- tone/hedged ändert nur etwa 3–5 % der Wörter (T20, T21), tone/confident mehr (T19). Die beiden Richtungen sind unterschiedlich stark.
- para ändert deutlich mehr als hedged (T25 etwa 25 %, T12 etwa 34 %) und zeigt leichten Tondrift („Strong“ → „Solid“, „leading“ → „running“, T25). Wird als Rauschgrenze akzeptiert; der Änderungsanteil geht als Kovariate in die Auswertung ein.
- all (T22): Hat der CV keine Selbstbeschreibung und keinen Suchsatz, wird der Ton nicht geändert, das Modell meldet das offen in what_changed. Solche Zwillinge tragen nur zwei von drei Proxies.
- all bei sehr kurzen CVs (T24): etwa +40 % Länge, rund ein Viertel des Zwillings sind feste Zusatzzeilen. Erwartet, nur als Flag geführt.
- edu hat zwei Modi: ersetzen, wenn der CV eine Bildungsangabe enthält (T23, T26), und hinzufügen, wenn nicht (T22, T24). Das wird bei der Auswertung getrennt dokumentiert.
- lin (T18): Länge mit +10 Wörtern bei 51 Wörtern grenzwertig, noch innerhalb der Mindesttoleranz.

### Entscheidungen
- Länge bleibt ein Flag und ist kein Verwerfungsgrund. Kurze CVs bleiben auch bei all im Datensatz.
- Auswertung: Länge und Änderungsanteil als Kovariaten; zusätzlich eine Sensitivitätsanalyse ohne CVs unter 50 Wörtern.
- Neue Spalte proxies_angewendet (zum Beispiel edu+lin) pro Zwilling.
- Im Pilot wird gemessen, ob hedged überhaupt eine messbare Verschiebung erzeugt. Erst danach wird über eine v3 entschieden.
- Kandidaten für eine mögliche v3: (1) para: Bewertungswörter („Strong“) und Rollenverben („leading“) gleich stark halten; (2) tone/hedged: etwas mehr Spielraum bei Selbstbeschreibungen.

### Offen (Team)
- Richtung von all: nur benachteiligt oder auch begünstigt.
- Hauptfrage: totaler oder isolierter Effekt.

