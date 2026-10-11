"""
Ek hi jagah se dono rules ka scan.

RULE 1 : lagataar 3 weekly candles ek hi 50-level ko straddle karein
         (UP = close upar, low neeche | DOWN = close neeche, high upar)
RULE 2 : candlestick pattern jiska BODY level ko cross kare
         (weekly aur daily, dono)

Dono ka target: L + 24 (UP) / L - 24 (DOWN)

MAX_AGE = 2 : pattern 2 period se purana ho toh nikaal do. Purane setups
pe price kaafi door nikal chuki hoti hai - 25-Sep wale CANHLIFE ka target
2 hafte baad 25% door tha, woh signal nahi raha.

Output teen hisson me:
  DONO     - dono rules, same direction
  RULE 1   - sirf teen parallel candles
  RULE 2   - sirf candle crossing the level

Run: python3 scan_today.py              (prices apne aap update honge)
     python3 scan_today.py --no-refresh (cache jaisa hai waise hi use karo)
"""

import argparse
import os
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd

import fast_patterns as fp
import round_level_strategy as rl
from levels import levels_crossed_by_body

PRICES = "ohlcv_nifty500_raw.csv.gz"     # UNADJUSTED - levels psychological hain
MAX_AGE = 2                              # 2 weeks (weekly) / 2 days (daily)
STEP, LEVEL_MAX, OFFSET = 50, 3000, 24.0
MIN_BODY_FRAC = 0.10                     # circuit/doji candles hatao
BATCH = 40                               # yfinance ek baar me kitne symbols


def refresh_prices(path=PRICES, overlap_days=5):
    """
    Cache me jo din missing hain sirf wahi fetch karo.

    auto_adjust=False ZARURI hai. True karoge toh prices dividend ke hisaab se
    peeche adjust ho jaati hain aur round levels ka matlab hi khatam - ITC Jan-2019
    me asal me 272 pe trade hui thi par adjusted data 196 dikhata hai.

    overlap: aakhri kuch din dobara kheenchte hain taaki late corrections aa jaayein.
    """
    if not os.path.exists(path):
        sys.exit(f"{path} nahi mila - pehle poora history fetch karna padega")
    old = pd.read_csv(path, parse_dates=["date"])
    old.columns = [c.lower() for c in old.columns]
    last = old.date.max().date()
    start = last - timedelta(days=overlap_days)
    end = date.today() + timedelta(days=1)
    if start >= end:
        print(f"cache already current ({last})")
        return old

    import yfinance as yf
    syms = sorted(old.symbol.unique())
    print(f"cache {last} tak hai - {start} se {date.today()} tak update kar rahe hain "
          f"({len(syms)} symbols)...")
    frames = []
    for i in range(0, len(syms), BATCH):
        b = syms[i:i + BATCH]
        try:
            raw = yf.download([s + ".NS" for s in b], start=start, end=end,
                              auto_adjust=False, progress=False,
                              group_by="ticker", threads=True)
        except Exception as e:
            print(f"  batch {i} fail: {str(e)[:60]}")
            continue
        for s in b:
            t = s + ".NS"
            if t not in raw.columns.get_level_values(0):
                continue
            d = raw[t].dropna(subset=["Close"]).copy()
            if d.empty:
                continue
            d = d[["Open", "High", "Low", "Close", "Volume"]]
            d["symbol"] = s
            frames.append(d.reset_index())
        print(f"  {min(i + BATCH, len(syms))}/{len(syms)}", flush=True)

    if not frames:
        print("  kuch naya nahi mila - purana cache hi use kar rahe hain")
        return old
    new = pd.concat(frames, ignore_index=True)
    new.columns = [c.lower() if c != "symbol" else c for c in new.columns]
    new["date"] = pd.to_datetime(new["date"]).dt.tz_localize(None)
    merged = (pd.concat([old[old.date < pd.Timestamp(start)], new], ignore_index=True)
                .drop_duplicates(["symbol", "date"], keep="last")
                .sort_values(["symbol", "date"]))
    merged.to_csv(path, index=False, compression="gzip")
    added = merged.date.max().date()
    print(f"  updated: {last} -> {added}  ({len(merged):,} bars)")
    return merged


def _rule1(px, today):
    """Teen parallel weekly candles. 3rd candle ki closing date bhi."""
    cfg = dict(rl.CONFIG, recent_weeks=MAX_AGE)
    d = rl.scan(px, cfg, recent_only=True)
    if d.empty:
        return d
    d = d.sort_values("weeks_ago").drop_duplicates(["symbol", "level", "direction"])
    d = d[d.weeks_ago <= MAX_AGE]
    d["today"] = d.symbol.map(today)
    d["to_tgt_pct"] = (d.target / d.today - 1) * 100
    d["signal_date"] = pd.to_datetime(d.end_week).dt.date
    d["age"] = d.weeks_ago.astype(int).astype(str) + "w"
    # target pehle se hit = ab signal nahi
    d = d[((d.direction == "UP") & (d.today < d.target)) |
          ((d.direction == "DOWN") & (d.today > d.target))]
    return d[["symbol", "direction", "level", "target", "today",
              "to_tgt_pct", "signal_date", "age"]]


def _patterns_at(o, h, l, c, j):
    """Us candle pe matching-direction patterns, degenerate candles chhod ke."""
    if (h[j] - l[j]) <= 0 or abs(c[j] - o[j]) / (h[j] - l[j]) < MIN_BODY_FRAC:
        return None, []
    bull = c[j] > o[j]
    pats = fp.detect_all(o, h, l, c)
    names = [k for k in (fp.BULLISH if bull else fp.BEARISH) if pats[k][j]]
    return bull, names


def _rule2(px, today):
    rows = []
    for sym, g in px.groupby("symbol"):
        g = g.sort_values("date")
        # ---- weekly ----
        w = rl.to_weekly(g, rl.CONFIG["week_rule"])
        n = len(w)
        if n >= 4:
            o, h, l, c = (w[x].values for x in ("open", "high", "low", "close"))
            for j in range(max(2, n - 1 - MAX_AGE), n):
                bull, names = _patterns_at(o, h, l, c, j)
                if not names:
                    continue
                for L in levels_crossed_by_body(o[j], c[j], STEP, LEVEL_MAX):
                    rows.append({"symbol": sym, "direction": "UP" if bull else "DOWN",
                                 "tf": "weekly", "pattern": ",".join(names), "level": L,
                                 "target": L + OFFSET if bull else L - OFFSET,
                                 "signal_date": w.index[j].date(), "age": f"{n - 1 - j}w"})
        # ---- daily ----
        o, h, l, c = (g[x].values.astype(float) for x in ("open", "high", "low", "close"))
        m = len(o)
        if m >= 30:
            for j in range(max(2, m - 1 - MAX_AGE), m):
                bull, names = _patterns_at(o, h, l, c, j)
                if not names:
                    continue
                for L in levels_crossed_by_body(o[j], c[j], STEP, LEVEL_MAX):
                    rows.append({"symbol": sym, "direction": "UP" if bull else "DOWN",
                                 "tf": "daily", "pattern": ",".join(names), "level": L,
                                 "target": L + OFFSET if bull else L - OFFSET,
                                 "signal_date": pd.Timestamp(g.date.values[j]).date(),
                                 "age": f"{m - 1 - j}d"})
    d = pd.DataFrame(rows)
    if d.empty:
        return d
    d["today"] = d.symbol.map(today)
    d["to_tgt_pct"] = (d.target / d.today - 1) * 100
    d = d[((d.direction == "UP") & (d.today < d.target)) |
          ((d.direction == "DOWN") & (d.today > d.target))]
    return d.sort_values("to_tgt_pct", key=abs)


def _print(title, df, cols):
    print(f"\n{'=' * 100}\n{title}\n{'=' * 100}")
    for dirn in ["DOWN", "UP"]:
        s = df[df.direction == dirn]
        print(f"\n  -- {dirn} ({len(s)}) --")
        if len(s):
            print(s[cols].to_string(index=False, float_format=lambda x: f"{x:,.2f}"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-refresh", action="store_true",
                    help="prices update mat karo, cache jaisa hai waise use karo")
    a = ap.parse_args()

    if a.no_refresh:
        px = pd.read_csv(PRICES, parse_dates=["date"])
        px.columns = [c.lower() for c in px.columns]
    else:
        px = refresh_prices()
    last = px.date.max()
    today = px.sort_values("date").groupby("symbol")["close"].last()
    print(f"prices through {last.date()}   |   max signal age = {MAX_AGE}")

    r1, r2 = _rule1(px, today), _rule2(px, today)
    k1 = set(zip(r1.symbol, r1.direction))
    k2 = set(zip(r2.symbol, r2.direction))
    both = k1 & k2

    print(f"\n{'=' * 100}\nDONO RULES  ({len(both)})\n{'=' * 100}")
    for sym, dirn in sorted(both):
        a = r1[(r1.symbol == sym) & (r1.direction == dirn)].iloc[0]
        print(f"\n{sym}  [{dirn}]   now {a.today:,.2f}   target {a.target:,.2f} "
              f"({a.to_tgt_pct:+.2f}%)")
        print(f"   rule1: 3 candles @{a.level:.0f}  -> 3rd candle {a.signal_date} ({a.age})")
        for _, b in r2[(r2.symbol == sym) & (r2.direction == dirn)].iterrows():
            print(f"   rule2: {b.pattern} ({b.tf}) @{b.level:.0f} -> {b.signal_date} ({b.age})")

    _print("SIRF RULE 1  (teen parallel candles)",
           r1[[(s, d) not in k2 for s, d in zip(r1.symbol, r1.direction)]],
           ["symbol", "level", "target", "today", "to_tgt_pct", "signal_date", "age"])
    _print("SIRF RULE 2  (candle crossing the level)",
           r2[[(s, d) not in k1 for s, d in zip(r2.symbol, r2.direction)]].drop_duplicates(
               ["symbol", "direction"]),
           ["symbol", "pattern", "tf", "level", "target", "today", "to_tgt_pct",
            "signal_date", "age"])

    r1.to_csv("scan_rule1.csv", index=False)
    r2.to_csv("scan_rule2.csv", index=False)
    print("\nSaved: scan_rule1.csv, scan_rule2.csv")

    # phone wala page bhi yahin bana do - ek hi command me sab
    try:
        import make_gann_page
        make_gann_page.main()
    except Exception as e:
        print(f"(page nahi bani: {str(e)[:80]} - alag se 'python3 make_gann_page.py' chalao)")


if __name__ == "__main__":
    main()
