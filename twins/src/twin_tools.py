"""Hilfsfunktionen für die Zwillingstests: Prompt bauen und Zwilling prüfen."""
import difflib
import json
import re
from pathlib import Path

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"
DIRECTIONS = {
    "edu": ["academic", "certification", "self_taught"],
    "lin": ["linear", "non_linear"],
    "tone": ["confident", "hedged"],
    "para": [None],
    "all": ["benachteiligt", "beguenstigt"],
}


def _nur_richtung(modul, direction):
    """Entfernt die Beschreibungen der nicht gewählten Richtungen, damit das
    Modell nur die zugewiesene sieht. Ein Block beginnt mit '- "name":' und
    läuft über Folgezeilen mit Einrückung."""
    out, skip = [], False
    for z in modul.splitlines():
        m = re.match(r'- "([a-z_]+)":', z)
        if m:
            skip = m.group(1) != direction
        elif not z.startswith("  "):
            skip = False
        if not skip:
            out.append(z)
    return "\n".join(out)


def build_prompt(cv_text, anchors, variant, direction=None, tol=0.2, version="v1"):
    """Setzt Rahmen + Modul zusammen. Platzhalter werden mit str.replace gefüllt,
    weil das JSON-Beispiel im Rahmen geschweifte Klammern enthält."""
    if direction not in DIRECTIONS[variant]:
        raise ValueError(f"Richtung {direction!r} passt nicht zu {variant!r}")
    if variant == "all":
        tol = max(tol, 0.3)  # drei Änderungen auf einmal brauchen mehr Spielraum
    pdir = PROMPTS / version
    rahmen = (pdir / "rahmen.txt").read_text(encoding="utf-8")
    modul = (pdir / f"{variant}.txt").read_text(encoding="utf-8")
    modul = _nur_richtung(modul, direction).replace("{direction}", str(direction))
    n = len(cv_text.split())
    if version == "v1":
        slack = round(n * tol)
    else:  # ab v2: Mindestspielraum in Wörtern, Länge ist Richtwert
        slack = max(round(n * tol), 15 if variant == "all" else 10)
    felder = {
        "{change_block}": modul.strip(),
        "{anchors}": ", ".join(anchors),
        "{cv_text}": cv_text,
        "{n_words}": str(n),
        "{min_words}": str(max(1, n - slack)),
        "{max_words}": str(n + slack),
    }
    if variant == "all":
        rahmen = rahmen.replace("exactly ONE aspect of presentation changed",
                                "only the aspects listed in CHANGE changed")
    for k, v in felder.items():
        rahmen = rahmen.replace(k, v)
    return rahmen


def parse_reply(raw):
    """Holt das JSON aus der Modellantwort (auch wenn Codezäune drumherum sind)."""
    m = re.search(r"\{.*\}", raw, flags=re.S)
    if not m:
        raise ValueError("Kein JSON gefunden")
    return json.loads(m.group(0))


def check(original, twin, anchors, tol=0.2, show_diff=True, min_slack=0):
    fehlt = [a for a in anchors if a not in twin]
    n_o, n_t = len(original.split()), len(twin.split())
    ratio = n_t / n_o
    erste_zeile_gleich = original.splitlines()[0].strip() == twin.splitlines()[0].strip()
    sm = difflib.SequenceMatcher(None, original.split(), twin.split())
    geaendert = 1 - sm.ratio()  # Anteil geänderter Wörter (Näherung)
    diff = [z for z in difflib.unified_diff(original.splitlines(), twin.splitlines(),
                                            lineterm="", n=0)
            if z[0] in "+-" and not z.startswith(("+++", "---"))]
    ergebnis = {
        "anker_fehlen": fehlt,
        "laenge_ok": abs(n_t - n_o) <= max(tol * n_o, min_slack),
        "laengenverhaeltnis": round(ratio, 2),
        "titel_gleich": erste_zeile_gleich,
        "aenderungsanteil": round(geaendert, 2),
        "n_words_orig": n_o,
        "n_words_twin": n_t,
    }
    print("Fehlende Anker:", fehlt or "keine")
    print(f"Länge: {n_o} -> {n_t} (Verhältnis {ratio:.2f}, {'ok' if ergebnis['laenge_ok'] else 'AUSSERHALB'})")
    print("Titel unverändert:", erste_zeile_gleich)
    print(f"Änderungsanteil (Wörter): {geaendert:.2f}")
    if show_diff:
        print("--- Diff ---")
        print("\n".join(diff))
    return ergebnis
