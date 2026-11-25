"""Vollauf, Schritt nach der Erzeugung: baut aus allen Antworten EINE Tabelle (eine Zeile pro Zwilling).

Aufruf (im Ordner twins):  python src/vollauf_export.py
Voraussetzung: `python src/vollauf_generate.py check` ist gelaufen (und möglichst `stichprobe` + Bewertung).
Schreibt:
  vollauf/vollauf_zwillinge.parquet        mit Texten (Original und Zwilling), für das Scoring. NUR LOKAL (Djinni-Texte)
  vollauf/vollauf_zwillinge_uebersicht.csv ohne Texte, zum Ansehen in Excel und für Git
Jede Zeile: CV-Herkunft (cv_id, id, ring, test, assigned_job_id), Zwilling (variante, richtung, text_zwilling),
Original (text_original), Prüfwerte (Längen, Flags), Stichprobe und manuelle Bewertung, Herkunft (Prompt, Modell, Datum).
`verwendbar` = Zwilling ist fertig (kein harter Fehler im letzten Versuch). Nur diese gehen ins Scoring."""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vollauf_generate as gp  # noqa: E402
from twin_tools import parse_reply  # noqa: E402


def main():
    for f in (gp.CVS_CSV, gp.PLAN_CSV, gp.ERGEBNIS_CSV):
        if not f.exists():
            sys.exit(f"{f.name} fehlt. Erst: python src/vollauf_generate.py check")
    cvs = pd.read_csv(gp.CVS_CSV, dtype=str)[["cv_id", "id", "test", "primary_keyword", "assigned_job_id"]]
    erg = pd.read_csv(gp.ERGEBNIS_CSV, dtype=str).fillna("")
    stich = {z["twin_id"] for z in gp.lies(gp.STICHPROBE_CSV)} if gp.STICHPROBE_CSV.exists() else set()
    manifest = json.loads(gp.MANIFEST.read_text(encoding="utf-8")) if gp.MANIFEST.exists() else {}

    zeilen = []
    for _, z in erg.iterrows():
        v = gp.versuche(z["twin_id"])
        text_zw, what, cli, zeit = "", "", "", ""
        if v:
            try:
                a = parse_reply(v[-1].read_text(encoding="utf-8"))
                text_zw, what = a["twin_text"], a.get("what_changed", "")
            except Exception:  # noqa: BLE001
                pass
            meta = v[-1].with_suffix(".meta.json")
            if meta.exists():
                m = json.loads(meta.read_text(encoding="utf-8"))
                cli, zeit = m.get("cli_model", ""), m.get("zeit", "")
        zeilen.append({
            "twin_id": z["twin_id"], "cv_id": z["cv_id"], "ring": z["ring"], "cv_typ": z["cv_typ"],
            "variante": z["variante"], "richtung": z["richtung"],
            "verwendbar": z["status"] == "fertig", "status": z["status"], "versuche": z["versuche"],
            "text_original": gp.cv_text(z["cv_id"]), "text_zwilling": text_zw, "what_changed": what,
            "n_words_orig": z["n_words_orig"], "n_words_twin": z["n_words_twin"],
            "laengenverhaeltnis": z["laengenverhaeltnis"], "laenge_flag": z["laenge_flag"] != "",
            "aenderungsanteil": z["aenderungsanteil"], "harte_fehler": z["harte_fehler"],
            "in_stichprobe": z["twin_id"] in stich, "urteil": z["urteil"], "befund": z["befund"],
            "erfunden": z["erfunden"], "problem": z["problem"],
            "prompt_version": manifest.get("prompt_version", ""), "prompt_hash": manifest.get("prompt_hash", ""),
            "modell_angegeben": z["modell_angegeben"], "cli_model": cli, "erzeugt_am": z["datum"], "zeit": zeit,
        })
    df = pd.DataFrame(zeilen).merge(cvs, on="cv_id", how="left")
    for s in ("n_words_orig", "n_words_twin", "versuche"):
        df[s] = pd.to_numeric(df[s], errors="coerce")
    for s in ("laengenverhaeltnis", "aenderungsanteil"):
        df[s] = pd.to_numeric(df[s], errors="coerce")
    ordnung = {"edu": 0, "lin": 1, "tone": 2, "para": 3, "all": 4}
    df = df.sort_values(["ring", "cv_id", "variante"], key=lambda c: c.map(ordnung) if c.name == "variante" else c)
    df = df.reset_index(drop=True)

    text_spalten = ["text_original", "text_zwilling"]
    try:
        df.to_parquet(gp.VOLL / "vollauf_zwillinge.parquet", index=False)
        print("Geschrieben: vollauf/vollauf_zwillinge.parquet (mit Texten, nur lokal)")
    except Exception as e:  # noqa: BLE001
        df.to_pickle(gp.VOLL / "vollauf_zwillinge.pkl")
        print(f"Parquet nicht möglich ({e}), stattdessen vollauf/vollauf_zwillinge.pkl (mit Texten, nur lokal)")
    df.drop(columns=text_spalten + ["what_changed"]).to_csv(
        gp.VOLL / "vollauf_zwillinge_uebersicht.csv", index=False, encoding="utf-8-sig")
    print("Geschrieben: vollauf/vollauf_zwillinge_uebersicht.csv (ohne Texte)")

    print(f"\n{len(df)} Zeilen, davon verwendbar: {int(df['verwendbar'].sum())}")
    print(df.groupby(["variante", "ring"]).agg(n=("twin_id", "size"), verwendbar=("verwendbar", "sum"),
                                                laenge_flag=("laenge_flag", "sum")).to_string())
    if not stich:
        print("\nHinweis: Noch keine Stichprobe gezogen, die Spalten urteil/befund sind leer.")


if __name__ == "__main__":
    main()
