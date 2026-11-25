"""Vollauf: baut aus der Zwillingstabelle eine einzelne HTML-Datei zum Durchsehen (offline, ohne Server).

Aufruf (im Ordner twins):  python src/vollauf_html.py
Liest:     vollauf/vollauf_zwillinge.parquet (oder .pkl), erzeugt von  python src/vollauf_export.py
Schreibt:  vollauf/vollauf_zwillinge.html
Die Datei enthält die Djinni-Texte und bleibt deshalb lokal (nicht in Git, nicht weitergeben).
Filter nach Variante, Ring, CV-Typ, Richtung, Stichprobe, Flags, Befund; Suche nach twin_id oder cv_id;
rechts Original und Zwilling nebeneinander mit Markierung der Änderungen."""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vollauf_generate as gp  # noqa: E402

SPALTEN = ["twin_id", "cv_id", "ring", "cv_typ", "variante", "richtung", "verwendbar", "status", "versuche",
           "text_original", "text_zwilling", "what_changed", "n_words_orig", "n_words_twin", "laengenverhaeltnis",
           "laenge_flag", "aenderungsanteil", "harte_fehler", "in_stichprobe", "urteil", "befund", "erfunden",
           "problem", "test", "assigned_job_id"]

SEITE = r"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Zwillinge Vollauf</title>
<style>
:root{--bg:#f7f6f2;--card:#fff;--ink:#1f2328;--mute:#6b7280;--line:#e2e0d8;--acc:#2f5d8a;--add:#d6f0dc;--addt:#14532d;--del:#fbd9d6;--delt:#7f1d1d;--warn:#b45309}
@media (prefers-color-scheme:dark){:root{--bg:#16181c;--card:#1f2228;--ink:#e6e6e6;--mute:#9aa1ab;--line:#2f333b;--acc:#7fb0e0;--add:#1d4d2c;--addt:#bbf7d0;--del:#5a2220;--delt:#fecaca;--warn:#f59e0b}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
header{padding:14px 16px;border-bottom:1px solid var(--line);background:var(--card)}
h1{font-size:18px;margin:0 0 4px}.sub{color:var(--mute);font-size:13px}
.filter{display:flex;flex-wrap:wrap;gap:8px;padding:10px 16px;border-bottom:1px solid var(--line);background:var(--card);align-items:center}
select,input[type=search]{font:inherit;padding:5px 8px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--ink)}
label.chk{display:flex;gap:4px;align-items:center;font-size:14px}
main{display:grid;grid-template-columns:minmax(260px,340px) 1fr;height:calc(100vh - 150px);min-height:420px}
#liste{overflow:auto;border-right:1px solid var(--line);background:var(--card)}
.zeile{padding:7px 12px;border-bottom:1px solid var(--line);cursor:pointer;display:flex;justify-content:space-between;gap:8px;font-size:14px}
.zeile:hover{background:var(--bg)}.zeile.aktiv{background:var(--bg);box-shadow:inset 3px 0 var(--acc)}
.tag{font-size:11px;padding:1px 6px;border-radius:9px;border:1px solid var(--line);color:var(--mute);white-space:nowrap}
.tag.warn{color:var(--warn);border-color:var(--warn)}.tag.rot{color:var(--delt);background:var(--del);border-color:transparent}
#detail{overflow:auto;padding:16px}
.meta{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 12px}
.spalten{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.box{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px}
.box h3{margin:0 0 8px;font-size:13px;color:var(--mute);text-transform:uppercase;letter-spacing:.04em}
.text{white-space:pre-wrap;word-break:break-word;font-size:14px}
ins{background:var(--add);color:var(--addt);text-decoration:none;border-radius:3px;padding:0 1px}
del{background:var(--del);color:var(--delt);border-radius:3px;padding:0 1px}
.hinweis{margin-top:12px;font-size:14px}.hinweis b{color:var(--mute);font-weight:600}
table{border-collapse:collapse;font-size:13px;margin:8px 0}td,th{border:1px solid var(--line);padding:3px 9px;text-align:right}th:first-child,td:first-child{text-align:left}
@media (max-width:760px){main{grid-template-columns:1fr;height:auto}#liste{max-height:240px}.spalten{grid-template-columns:1fr}}
</style></head><body>
<header><h1>Zwillinge Vollauf</h1><div class="sub" id="kopf"></div></header>
<div class="filter">
 <select id="fv"></select><select id="fr"></select><select id="ft"></select><select id="fd"></select>
 <label class="chk"><input type="checkbox" id="fs">Stichprobe</label>
 <label class="chk"><input type="checkbox" id="ff">Längen-Flag</label>
 <label class="chk"><input type="checkbox" id="fb">Befund</label>
 <label class="chk"><input type="checkbox" id="fn">nicht verwendbar</label>
 <input type="search" id="q" placeholder="twin_id oder cv_id">
 <span class="sub" id="anzahl"></span>
</div>
<main><div id="liste"></div><div id="detail"><div class="sub">Zwilling links auswählen.</div></div></main>
<script>
const D=__DATEN__;
const $=i=>document.getElementById(i);
const opt=(el,label,vals)=>{el.innerHTML='<option value="">'+label+'</option>'+vals.map(v=>'<option>'+v+'</option>').join('')};
const uniq=k=>[...new Set(D.map(d=>d[k]).filter(x=>x!==''))].sort();
opt($('fv'),'alle Varianten',uniq('variante'));opt($('fr'),'alle Ringe',uniq('ring'));
opt($('ft'),'alle CV-Typen',uniq('cv_typ'));opt($('fd'),'alle Richtungen',uniq('richtung'));
const esc=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
function diff(a,b){
  const A=a.split(/(\s+)/),B=b.split(/(\s+)/),n=A.length,m=B.length;
  const L=Array.from({length:n+1},()=>new Uint16Array(m+1));
  for(let i=n-1;i>=0;i--)for(let j=m-1;j>=0;j--)L[i][j]=A[i]===B[j]?L[i+1][j+1]+1:Math.max(L[i+1][j],L[i][j+1]);
  let i=0,j=0,o='',t='';
  while(i<n&&j<m){
    if(A[i]===B[j]){o+=esc(A[i]);t+=esc(B[j]);i++;j++}
    else if(L[i+1][j]>=L[i][j+1]){o+=/^\s+$/.test(A[i])?esc(A[i]):'<del>'+esc(A[i])+'</del>';i++}
    else{t+=/^\s+$/.test(B[j])?esc(B[j]):'<ins>'+esc(B[j])+'</ins>';j++}
  }
  while(i<n){o+=/^\s+$/.test(A[i])?esc(A[i]):'<del>'+esc(A[i])+'</del>';i++}
  while(j<m){t+=/^\s+$/.test(B[j])?esc(B[j]):'<ins>'+esc(B[j])+'</ins>';j++}
  return [o,t];
}
let aktiv=null,sicht=[];
function tags(d){let s='';
  if(d.in_stichprobe)s+='<span class="tag">Stichprobe</span>';
  if(d.laenge_flag)s+='<span class="tag warn">Länge</span>';
  if(!d.verwendbar)s+='<span class="tag rot">'+esc(d.status)+'</span>';
  if(d.befund==='ja')s+='<span class="tag rot">Befund</span>';return s}
function liste(){
  const v=$('fv').value,r=$('fr').value,t=$('ft').value,di=$('fd').value,q=$('q').value.trim().toLowerCase();
  sicht=D.filter(d=>(!v||d.variante===v)&&(!r||d.ring===r)&&(!t||d.cv_typ===t)&&(!di||d.richtung===di)
    &&(!$('fs').checked||d.in_stichprobe)&&(!$('ff').checked||d.laenge_flag)&&(!$('fb').checked||d.befund==='ja')
    &&(!$('fn').checked||!d.verwendbar)&&(!q||d.twin_id.toLowerCase().includes(q)||d.cv_id.toLowerCase().includes(q)));
  $('anzahl').textContent=sicht.length+' von '+D.length;
  $('liste').innerHTML=sicht.map((d,i)=>'<div class="zeile'+(aktiv===d.twin_id?' aktiv':'')+'" data-i="'+i+'"><span>'+d.twin_id+'</span><span>'+tags(d)+'</span></div>').join('');
}
function zeige(d){
  aktiv=d.twin_id;const [o,t]=diff(d.text_original,d.text_zwilling);
  const m=(k,v)=>v===''||v===null?'':'<span class="tag">'+k+' '+esc(v)+'</span>';
  $('detail').innerHTML='<h2 style="margin:0;font-size:17px">'+d.twin_id+'</h2><div class="meta">'+
   m('Ring',d.ring)+m('Typ',d.cv_typ)+m('Variante',d.variante)+m('Richtung',d.richtung||'-')+m('Versuche',d.versuche)+
   m('Wörter',d.n_words_orig+' → '+d.n_words_twin)+m('Verhältnis',d.laengenverhaeltnis)+m('Änderungsanteil',d.aenderungsanteil)+m('Test',d.test)+tags(d)+'</div>'+
   '<div class="spalten"><div class="box"><h3>Original</h3><div class="text">'+o+'</div></div><div class="box"><h3>Zwilling</h3><div class="text">'+t+'</div></div></div>'+
   '<div class="hinweis"><b>Was geändert wurde (Modell):</b> '+esc(d.what_changed)+'</div>'+
   (d.harte_fehler?'<div class="hinweis"><b>Harte Fehler:</b> '+esc(d.harte_fehler)+'</div>':'')+
   (d.urteil?'<div class="hinweis"><b>Bewertung:</b> '+esc(d.urteil)+', Befund '+esc(d.befund)+(d.problem?' – '+esc(d.problem):'')+'</div>':'');
  liste();
}
$('liste').addEventListener('click',e=>{const z=e.target.closest('.zeile');if(z)zeige(sicht[+z.dataset.i])});
['fv','fr','ft','fd','fs','ff','fb','fn','q'].forEach(i=>$(i).addEventListener('input',liste));
// Übersicht
const grp={};D.forEach(d=>{const k=d.variante+'|'+d.ring;grp[k]=grp[k]||{n:0,ok:0,fl:0};grp[k].n++;grp[k].ok+=d.verwendbar?1:0;grp[k].fl+=d.laenge_flag?1:0});
$('kopf').innerHTML=D.length+' Zwillinge, davon '+D.filter(d=>d.verwendbar).length+' verwendbar, '+D.filter(d=>d.in_stichprobe).length+' in der Stichprobe, '+
  D.filter(d=>d.laenge_flag).length+' mit Längen-Flag. Prompt '+esc(__PROMPT__)+'. Nur lokal verwenden, enthält CV-Texte.';
liste();
</script></body></html>"""


def main():
    pq, pk = gp.VOLL / "vollauf_zwillinge.parquet", gp.VOLL / "vollauf_zwillinge.pkl"
    if pq.exists():
        df = pd.read_parquet(pq)
    elif pk.exists():
        df = pd.read_pickle(pk)
    else:
        sys.exit("Tabelle fehlt. Erst: python src/vollauf_export.py")
    df = df[SPALTEN].copy()
    for s in ("n_words_orig", "n_words_twin", "versuche"):
        df[s] = df[s].apply(lambda x: "" if pd.isna(x) else int(x))
    for s in ("laengenverhaeltnis", "aenderungsanteil"):
        df[s] = df[s].apply(lambda x: "" if pd.isna(x) else float(x))
    df = df.fillna("")
    for s in ("verwendbar", "laenge_flag", "in_stichprobe"):
        df[s] = df[s].astype(bool)
    daten = json.dumps(df.to_dict(orient="records"), ensure_ascii=False).replace("</", "<\\/")
    prompt = json.dumps(f"v2 ({gp.json.loads(gp.MANIFEST.read_text(encoding='utf-8')).get('prompt_hash', '')})") \
        if gp.MANIFEST.exists() else '"v2"'
    html = SEITE.replace("__DATEN__", daten).replace("__PROMPT__", prompt)
    ziel = gp.VOLL / "vollauf_zwillinge.html"
    ziel.write_text(html, encoding="utf-8")
    print(f"Geschrieben: vollauf/{ziel.name} ({len(df)} Zwillinge, {ziel.stat().st_size // 1024} KB). Im Browser öffnen, nicht weitergeben.")


if __name__ == "__main__":
    main()
