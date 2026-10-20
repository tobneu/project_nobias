"""Baut aus einer jobmarket-Parquet eine interaktive HTML-Tabelle zum schnellen Durchlesen.

    python scripts/jobmarket_to_html.py                       # neueste jobmarket_*.parquet
    python scripts/jobmarket_to_html.py --market <pfad>.parquet

Die HTML landet neben der Parquet (data/processed/, per .gitignore ausgeschlossen – sie enthält CV-Texte).
"""
import argparse
import json
from pathlib import Path

import pandas as pd

PROCESSED = Path("data/processed")
CV_PATH = Path("data/raw/djinni/cv_profiles_en.parquet")
JOB_PATH = Path("data/raw/djinni/job_postings_en.parquet")

FILTER_COLUMNS = ["doc_type", "role", "ring", "test", "primary_keyword"]
HIDDEN_BY_DEFAULT = ["id", "assigned_job_id", "esco_uris", "seed"]


def load(path: Path) -> pd.DataFrame:
    market = pd.read_parquet(path)

    cv = pd.read_parquet(CV_PATH, columns=["id", "Position", "Highlights", "Moreinfo"])
    cv["text"] = cv[["Position", "Highlights", "Moreinfo"]].fillna("").agg("\n".join, axis=1).str.strip()
    jobs = pd.read_parquet(JOB_PATH, columns=["id", "Position", "Long Description"])
    jobs["text"] = jobs[["Position", "Long Description"]].fillna("").agg("\n".join, axis=1).str.strip()
    texts = pd.concat([cv[["id", "text"]], jobs[["id", "text"]]])

    market = market.merge(texts, on="id", how="left")
    job_titles = market.loc[market["role"] == "job"].set_index("id")["position"]
    market.insert(market.columns.get_loc("assigned_job_id") + 1, "assigned_job",
                  market["assigned_job_id"].map(job_titles))

    for col in market.columns:                         # Listen -> lesbarer Text
        if market[col].apply(lambda v: hasattr(v, "__len__") and not isinstance(v, str)).any():
            market[col] = market[col].apply(lambda v: ", ".join(v) if v is not None else "")
    return market.fillna("")


PAGE = """<!doctype html>
<html lang="de"><head><meta charset="utf-8"><title>__TITLE__</title>
<style>
  body { font: 13px system-ui, sans-serif; margin: 16px; background: #fcfcfb; color: #0b0b0b; }
  #controls { display: flex; flex-wrap: wrap; gap: 8px 16px; margin-bottom: 12px; align-items: center; }
  #columns label { margin-right: 10px; white-space: nowrap; }
  table { border-collapse: collapse; width: 100%; }
  th { position: sticky; top: 0; background: #e1e0d9; text-align: left; padding: 6px; }
  td { border-bottom: 1px solid #e1e0d9; padding: 6px; vertical-align: top; }
  td div { max-height: 4.5em; overflow: hidden; cursor: pointer; white-space: pre-wrap; }
  td div.open { max-height: none; }
  .hidden { display: none; }
</style></head><body>
<h2>__TITLE__</h2>
<div id="controls">
  <input id="search" placeholder="Suche in allen Spalten …" size="35">
  <span id="filters"></span>
  <span id="count"></span>
</div>
<details><summary>Spalten ein-/ausblenden</summary><div id="columns"></div></details>
<p style="color:#898781">Zelle anklicken, um langen Text aufzuklappen.</p>
<table><thead><tr id="head"></tr></thead><tbody id="body"></tbody></table>
<script>
const data = __DATA__;
const filterCols = __FILTERS__;
const hiddenCols = new Set(__HIDDEN__);
const cols = Object.keys(data[0]);

const head = document.getElementById("head");
const body = document.getElementById("body");

cols.forEach((c, i) => {
  const th = document.createElement("th");
  th.textContent = c;
  th.dataset.col = i;
  head.appendChild(th);

  const label = document.createElement("label");
  label.innerHTML = `<input type="checkbox" ${hiddenCols.has(c) ? "" : "checked"}> ${c}`;
  label.querySelector("input").onchange = e => toggleColumn(i, e.target.checked);
  document.getElementById("columns").appendChild(label);
});

data.forEach(row => {
  const tr = document.createElement("tr");
  cols.forEach((c, i) => {
    const td = document.createElement("td");
    td.dataset.col = i;
    const div = document.createElement("div");
    div.textContent = row[c];
    div.onclick = () => div.classList.toggle("open");
    td.appendChild(div);
    tr.appendChild(td);
  });
  body.appendChild(tr);
});

filterCols.forEach(c => {
  const select = document.createElement("select");
  const values = [...new Set(data.map(r => r[c]))].sort();
  select.innerHTML = `<option value="">${c}: alle</option>` +
    values.map(v => `<option>${v}</option>`).join("");
  select.dataset.col = c;
  select.onchange = applyFilters;
  document.getElementById("filters").appendChild(select);
});
document.getElementById("search").oninput = applyFilters;

function toggleColumn(i, visible) {
  document.querySelectorAll(`[data-col="${i}"]`).forEach(el => el.classList.toggle("hidden", !visible));
}

function applyFilters() {
  const query = document.getElementById("search").value.toLowerCase();
  const active = [...document.querySelectorAll("#filters select")].filter(s => s.value);
  let shown = 0;
  [...body.rows].forEach((tr, r) => {
    const row = data[r];
    const ok = active.every(s => String(row[s.dataset.col]) === s.value) &&
               (!query || Object.values(row).some(v => String(v).toLowerCase().includes(query)));
    tr.classList.toggle("hidden", !ok);
    shown += ok;
  });
  document.getElementById("count").textContent = `${shown} von ${data.length} Zeilen`;
}

cols.forEach((c, i) => { if (hiddenCols.has(c)) toggleColumn(i, false); });
applyFilters();
</script></body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--market", type=Path, default=None, help="Pfad zur jobmarket-Parquet (Default: neueste)")
    args = parser.parse_args()

    path = args.market or sorted(PROCESSED.glob("jobmarket_*.parquet"))[-1]
    market = load(path)

    as_json = lambda obj: json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")   # kein </script> im Text
    html = (PAGE.replace("__TITLE__", path.stem)
                .replace("__DATA__", as_json(market.to_dict(orient="records")))
                .replace("__FILTERS__", as_json([c for c in FILTER_COLUMNS if c in market.columns]))
                .replace("__HIDDEN__", as_json(HIDDEN_BY_DEFAULT)))

    out = path.with_suffix(".html")
    out.write_text(html, encoding="utf-8")
    print(f"Gespeichert: {out} ({len(market)} Zeilen)")


if __name__ == "__main__":
    main()
