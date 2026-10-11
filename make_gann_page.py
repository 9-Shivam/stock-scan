"""
Gann Psychological Numbers - standalone HTML page banata hai.

scan_today.py chalane ke baad yeh chalao:
    python3 scan_today.py
    python3 make_gann_page.py

Output: Gann_Psychological_Numbers.html
  - ek hi file, koi internet nahi chahiye (phone pe offline chalega)
  - chhoti screen pe table ki jagah cards
  - dark mode apne aap

Phone pe le jaane ke tareeke:
  - file ko WhatsApp/Telegram pe khud ko bhej do, phir browser me kholo
  - ya: python3 -m http.server 8000   aur phone se http://<laptop-ip>:8000 kholo
    (dono same wifi pe hone chahiye)
"""

import json          # noqa: F401  (scan_phone isko page.json se use karta hai)
import os
from datetime import datetime

import pandas as pd

OUT = "Gann_Psychological_Numbers.html"
MAX_FAR_PCT = 10.0        # default filter: target itne % se door ho toh chhupa do


def build_records():
    r1 = pd.read_csv("scan_rule1.csv")
    r2 = pd.read_csv("scan_rule2.csv")
    k1 = set(zip(r1.symbol, r1.direction))
    k2 = set(zip(r2.symbol, r2.direction))
    both = k1 & k2

    def r2_for(sym, direction):
        m = r2[(r2.symbol == sym) & (r2.direction == direction)]
        m = m.drop_duplicates(["pattern", "tf", "level"])
        return [{"p": b.pattern, "tf": b.tf, "l": int(b.level),
                 "d": str(b.signal_date), "a": b.age} for _, b in m.iterrows()][:4]

    recs, seen = [], set()
    for _, a in r1.iterrows():
        key = (a.symbol, a.direction)
        seen.add(key)
        recs.append({"s": a.symbol, "dir": a.direction, "l": int(a.level),
                     "t": round(a.target, 2), "n": round(a.today, 2),
                     "p": round(a.to_tgt_pct, 2),
                     "b": "BOTH" if key in both else "R1",
                     "r1d": str(a.signal_date), "r1a": a.age,
                     "r2": r2_for(a.symbol, a.direction)})
    for (sym, direction), g in r2.groupby(["symbol", "direction"]):
        if (sym, direction) in seen:
            continue
        row = g.reindex(g.to_tgt_pct.abs().sort_values().index).iloc[0]
        recs.append({"s": sym, "dir": direction, "l": int(row.level),
                     "t": round(row.target, 2), "n": round(row.today, 2),
                     "p": round(row.to_tgt_pct, 2), "b": "R2",
                     "r1d": None, "r1a": None, "r2": r2_for(sym, direction)})
    recs.sort(key=lambda r: abs(r["p"]))
    return recs


TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#111">
<title>Gann Psychological Numbers</title>
<style>
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
:root{--bg:#fff;--bg2:#f7f6f2;--bd:#e5e3dc;--tx:#1a1a18;--tx2:#4a4945;--tx3:#83827d;
      --up:#1a7f5a;--dn:#b4442e}
@media(prefers-color-scheme:dark){
  :root{--bg:#1c1c1a;--bg2:#262624;--bd:#3a3a37;--tx:#f0efea;--tx2:#c9c7c1;--tx3:#8a8880;
        --up:#4ab88a;--dn:#e07a63}}
body{margin:0;padding:12px;background:var(--bg);color:var(--tx);
  font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  padding-bottom:env(safe-area-inset-bottom)}
h1{font-size:17px;margin:0 0 2px;letter-spacing:-.02em}
.sub{font-size:11.5px;color:var(--tx3);margin-bottom:10px}
.warn{font-size:11px;background:var(--bg2);border:1px solid var(--bd);border-radius:6px;
  padding:8px 10px;color:var(--tx2);margin-bottom:12px;line-height:1.5}
.ctl{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
.seg{display:flex;border:1px solid var(--bd);border-radius:7px;overflow:hidden}
.seg button{font:inherit;font-size:12.5px;padding:7px 11px;border:0;background:transparent;
  color:var(--tx3);border-right:1px solid var(--bd);cursor:pointer;min-height:36px}
.seg button:last-child{border-right:0}
.seg button.on{background:var(--tx);color:var(--bg);font-weight:600}
.chk{display:flex;align-items:center;gap:6px;font-size:12.5px;color:var(--tx3);
  padding:7px 0;cursor:pointer}
.chk input{width:16px;height:16px;accent-color:var(--tx)}
.cnt{font-size:11.5px;color:var(--tx3);margin:4px 0 8px}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
th{text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.05em;
  color:var(--tx3);padding:7px 8px;border-bottom:1px solid var(--bd);cursor:pointer;white-space:nowrap}
th.n{text-align:right}
td{padding:8px;border-bottom:1px solid var(--bd);vertical-align:top}
td.n{text-align:right}
.sym{font-weight:700;letter-spacing:-.01em}
.tag{display:inline-block;font-size:9px;font-weight:700;letter-spacing:.05em;
  padding:2px 5px;border-radius:3px;text-transform:uppercase}
.tBOTH{background:var(--tx);color:var(--bg)}
.tR1{background:var(--bg2);color:var(--tx2);border:1px solid var(--bd)}
.tR2{color:var(--tx3);border:1px solid var(--bd)}
.up{color:var(--up);font-weight:700}.dn{color:var(--dn);font-weight:700}
.dates{font-size:10.5px;color:var(--tx3);line-height:1.5}
.dates b{color:var(--tx2)}
.a0{color:var(--up);font-weight:700}.a2{color:var(--dn)}
.card{border:1px solid var(--bd);border-radius:9px;padding:11px;margin-bottom:8px;background:var(--bg)}
.crow{display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.cnum{font-size:12.5px;color:var(--tx2);margin-top:5px;font-variant-numeric:tabular-nums}
.cnum span{color:var(--tx3)}
.empty{padding:30px;text-align:center;color:var(--tx3)}
#cards{display:none}
@media(max-width:640px){#tblwrap{display:none}#cards{display:block}body{padding:10px}}
</style></head><body>

<h1>Gann Psychological Numbers</h1>
<div class="sub">__SUB__</div>
<div class="warn"><b>Scanner only — no tested edge.</b> Rule 1 UP backtested at &minus;0.9%;
Rule 2 was flat on weekly and a volatility effect (not directional) on daily. Targets are
&#8377;24 fixed, so they mean ~16% at level 150 and ~0.8% at level 2900.</div>

<div class="ctl">
  <div class="seg" id="bucket">
    <button data-v="ALL" class="on">All</button><button data-v="BOTH">Dono</button>
    <button data-v="R1">Rule 1</button><button data-v="R2">Rule 2</button>
  </div>
  <div class="seg" id="dir">
    <button data-v="ALL" class="on">Both</button><button data-v="UP">Up</button>
    <button data-v="DOWN">Down</button>
  </div>
</div>
<div class="ctl">
  <label class="chk"><input type="checkbox" id="fresh"> Fresh only</label>
  <label class="chk"><input type="checkbox" id="near" checked> Hide &gt;__FAR__% away</label>
</div>
<div class="cnt" id="cnt"></div>

<div id="tblwrap"><table id="tbl"><thead><tr>
  <th data-k="s">Stock</th><th data-k="b">Rule</th><th data-k="dir">Dir</th>
  <th data-k="l" class="n">Level</th><th data-k="n" class="n">Now</th>
  <th data-k="t" class="n">Target</th><th data-k="p" class="n">To tgt</th>
  <th>Signal date / age</th></tr></thead><tbody></tbody></table></div>
<div id="cards"></div>

<script>
const DATA=__DATA__, FAR=__FAR__;
let st={bucket:'ALL',dir:'ALL',fresh:false,near:true,sort:'p',asc:true};
const ageCls=a=>{if(!a)return'';const n=parseInt(a);return n===0?'a0':(n>=2?'a2':'')};
const fresh=r=>(r.r1a&&parseInt(r.r1a)===0)||(r.r2||[]).some(x=>parseInt(x.a)===0);
function rows(){
  let d=DATA.filter(r=>(st.bucket==='ALL'||r.b===st.bucket)&&(st.dir==='ALL'||r.dir===st.dir)
    &&(!st.fresh||fresh(r))&&(!st.near||Math.abs(r.p)<=FAR));
  const k=st.sort;
  d.sort((a,b)=>{let x=a[k],y=b[k];if(k==='p'){x=Math.abs(x);y=Math.abs(y)}
    if(typeof x==='string')return st.asc?x.localeCompare(y):y.localeCompare(x);
    return st.asc?x-y:y-x});
  return d;
}
function dateLines(r){
  let s='';
  if(r.r1d)s+='<div><b>R1</b> 3 candles @'+r.l+' &middot; '+r.r1d+' <span class="'+ageCls(r.r1a)+'">('+r.r1a+')</span></div>';
  (r.r2||[]).forEach(x=>{s+='<div><b>R2</b> '+x.p+' ['+x.tf+'] @'+x.l+' &middot; '+x.d+' <span class="'+ageCls(x.a)+'">('+x.a+')</span></div>'});
  return s;
}
function render(){
  const d=rows();
  document.getElementById('cnt').textContent=d.length+' of '+DATA.length+' signals';
  const tb=document.querySelector('#tbl tbody'), cd=document.getElementById('cards');
  if(!d.length){tb.innerHTML='<tr><td colspan="8" class="empty">Nothing matches.</td></tr>';
    cd.innerHTML='<div class="empty">Nothing matches.</div>';return}
  tb.innerHTML=d.map(r=>{const c=r.dir==='UP'?'up':'dn';
    return '<tr><td class="sym">'+r.s+'</td><td><span class="tag t'+r.b+'">'+(r.b==='BOTH'?'dono':r.b)+'</span></td>'
    +'<td class="'+c+'">'+(r.dir==='UP'?'\\u25b2':'\\u25bc')+'</td><td class="n">'+r.l+'</td>'
    +'<td class="n">'+r.n+'</td><td class="n">'+r.t+'</td>'
    +'<td class="n '+c+'">'+(r.p>0?'+':'')+r.p.toFixed(2)+'%</td>'
    +'<td class="dates">'+dateLines(r)+'</td></tr>'}).join('');
  cd.innerHTML=d.map(r=>{const c=r.dir==='UP'?'up':'dn';
    return '<div class="card"><div class="crow"><div><span class="sym">'+r.s+'</span> '
    +'<span class="tag t'+r.b+'">'+(r.b==='BOTH'?'dono':r.b)+'</span></div>'
    +'<div class="'+c+'">'+(r.dir==='UP'?'\\u25b2':'\\u25bc')+' '+(r.p>0?'+':'')+r.p.toFixed(2)+'%</div></div>'
    +'<div class="cnum"><span>level</span> '+r.l+' &nbsp; <span>now</span> '+r.n
    +' &nbsp; <span>target</span> '+r.t+'</div>'
    +'<div class="dates" style="margin-top:6px">'+dateLines(r)+'</div></div>'}).join('');
}
document.querySelectorAll('.seg').forEach(s=>s.addEventListener('click',e=>{
  const b=e.target.closest('button');if(!b)return;
  s.querySelectorAll('button').forEach(x=>x.classList.remove('on'));
  b.classList.add('on');st[s.id]=b.dataset.v;render()}));
document.getElementById('fresh').onchange=e=>{st.fresh=e.target.checked;render()};
document.getElementById('near').onchange=e=>{st.near=e.target.checked;render()};
document.querySelectorAll('th[data-k]').forEach(th=>th.onclick=()=>{
  const k=th.dataset.k;st.asc=st.sort===k?!st.asc:true;st.sort=k;render()});
render();
</script></body></html>
"""


def main():
    for f in ("scan_rule1.csv", "scan_rule2.csv"):
        if not os.path.exists(f):
            raise SystemExit(f"{f} nahi mila - pehle 'python3 scan_today.py' chalao")
    recs = build_records()
    px = pd.read_csv("ohlcv_nifty500_raw.csv.gz", usecols=["date"], parse_dates=["date"])
    sub = (f"Nifty 500 &middot; prices through {px.date.max().date()} &middot; "
           f"generated {datetime.now():%d %b %Y %H:%M} &middot; {len(recs)} signals")
    html = (TEMPLATE.replace("__DATA__", json.dumps(recs, separators=(",", ":")))
                    .replace("__SUB__", sub)
                    .replace("__FAR__", str(MAX_FAR_PCT)))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved {OUT}  ({os.path.getsize(OUT) / 1024:.0f} KB, {len(recs)} signals)")
    print("Phone pe kholne ke liye: khud ko WhatsApp/Telegram pe bhej do,")
    print("ya 'python3 -m http.server 8000' chala ke phone se laptop ka IP kholo.")


if __name__ == "__main__":
    main()
