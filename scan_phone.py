"""
Cloud/phone wala scanner - bilkul apne aap chalta hai.

scan_today.py local cache (ohlcv_nifty500_raw.csv.gz, ~18 MB) pe depend karta hai.
GitHub Actions pe har run naya container hota hai, toh cache rakhna theek nahi.

Yeh script sirf utna data kheenchta hai jitna scan ke liye chahiye:
  - rule 1 ko 3 weekly candles + 2 hafte ki age = ~6 hafte
  - daily patterns ko 20-din ka volume average
  -> 8 mahine kaafi hai (10 saal ki jagah). Fetch 8 min se ghat ke ~2 min.

auto_adjust=False ZARURI hai - round levels asli traded price pe hote hain.
Dividend-adjusted history me woh levels kabhi exist hi nahi karte.

Output: index.html  (GitHub Pages isi naam ko dhoondhta hai)
"""

import os
import sys
from datetime import date, timedelta

import pandas as pd

import make_gann_page as page
from scan_today import _rule1, _rule2

MONTHS = 8
BATCH = 40
UNIVERSE = "ind_nifty500list.csv"
OUT_HTML = "index.html"


def fetch_recent(symbols, months=MONTHS):
    """Sirf aakhri `months` mahine ka daily OHLCV. Koi local cache nahi."""
    import yfinance as yf
    start = date.today() - timedelta(days=int(months * 31))
    end = date.today() + timedelta(days=1)
    frames, failed = [], []
    print(f"fetching {len(symbols)} symbols, {start} -> {date.today()}")
    for i in range(0, len(symbols), BATCH):
        b = symbols[i:i + BATCH]
        try:
            raw = yf.download([s + ".NS" for s in b], start=start, end=end,
                              auto_adjust=False, progress=False,
                              group_by="ticker", threads=True)
        except Exception as e:
            print(f"  batch {i} failed: {str(e)[:70]}")
            failed += b
            continue
        for s in b:
            t = s + ".NS"
            if t not in raw.columns.get_level_values(0):
                failed.append(s)
                continue
            d = raw[t].dropna(subset=["Close"]).copy()
            if d.empty:
                failed.append(s)
                continue
            d = d[["Open", "High", "Low", "Close", "Volume"]]
            d["symbol"] = s
            frames.append(d.reset_index())
        print(f"  {min(i + BATCH, len(symbols))}/{len(symbols)}", flush=True)

    if not frames:
        sys.exit("ERROR: kuch bhi fetch nahi hua - yfinance down ya network issue")
    px = pd.concat(frames, ignore_index=True)
    px.columns = [c.lower() if c != "symbol" else c for c in px.columns]
    px["date"] = pd.to_datetime(px["date"]).dt.tz_localize(None)
    if failed:
        print(f"  ({len(failed)} symbols ka data nahi mila - skip)")
    return px.sort_values(["symbol", "date"])


def main():
    if not os.path.exists(UNIVERSE):
        sys.exit(f"{UNIVERSE} repo me nahi hai - usse commit karna zaruri hai")
    syms = sorted(pd.read_csv(UNIVERSE)["Symbol"].astype(str).str.strip().unique())

    px = fetch_recent(syms)
    last = px.date.max()
    today = px.sort_values("date").groupby("symbol")["close"].last()
    print(f"\nprices through {last.date()}  |  {px.symbol.nunique()} symbols, "
          f"{len(px):,} bars")

    r1, r2 = _rule1(px, today), _rule2(px, today)
    r1.to_csv("scan_rule1.csv", index=False)
    r2.to_csv("scan_rule2.csv", index=False)
    both = set(zip(r1.symbol, r1.direction)) & set(zip(r2.symbol, r2.direction))
    print(f"rule1 {len(r1)} | rule2 {len(r2)} | dono {len(both)}")

    # HTML banao - make_gann_page ka hi template, par date yahin se
    recs = page.build_records()
    html = (page.TEMPLATE
            .replace("__DATA__", page.json.dumps(recs, separators=(",", ":")))
            .replace("__SUB__", f"Nifty 500 &middot; prices through {last.date()} "
                                f"&middot; {len(recs)} signals")
            .replace("__FAR__", str(page.MAX_FAR_PCT)))
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"wrote {OUT_HTML} ({os.path.getsize(OUT_HTML) / 1024:.0f} KB, {len(recs)} signals)")


if __name__ == "__main__":
    main()
