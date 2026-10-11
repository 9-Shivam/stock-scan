"""
Round-number level strategy (user ka apna idea, 2026-10-02).

Rule:
  Levels = 50 ke multiples (50, 100, 150, ... 30000). Weekly candles pe kaam.

  Ek level L = 50*X ko weekly candle "straddle" karti hai jab L candle ke
  andar aata hai. Do case:

    UP   : close > L  aur  low  < L   (L, low aur close ke beech)
    DOWN : close < L  aur  high > L   (L, close aur high ke beech)

  Agar lagataar 3 weekly candles ek hi L ko ek hi tarike se straddle karein
  ("teen parallel candles"), toh:
    UP   -> target L + 24
    DOWN -> target L - 24

Output: woh stocks jinka 3-candle pattern pichhle 1-2 hafton me pura hua.

NOTE - abhi tak yeh sirf ek SCANNER hai, tested edge nahi.
Yeh pattern kaam karta hai ya nahi, woh backtest.py se naapo. Dhyan rahe:
  - target 24 rupaye ABSOLUTE hai. 300 ke stock pe 8% hai, 30000 ke stock pe
    0.08%. Yaani alag alag price pe yeh bilkul alag trade hai.
  - 50 ka grid mehnge stocks pe bahut ghana hai: 5000 ka stock agar hafte me
    300 points ghoomta hai toh ek hi candle 6 levels straddle karti hai.
"""

import argparse

import numpy as np
import pandas as pd

CONFIG = {
    "level_step": 50,          # levels 50 ke multiple
    # [USER] 50 ka grid sirf 3000 tak. Uske upar alag scheme hai jo abhi decide
    # nahi hui - tab tak 3000 se upar ke levels generate hi nahi karte, isliye
    # mehnge stocks (PTCIL ~22000 wagairah) apne aap bahar ho jaate hain.
    "level_max": 3_000,
    "run_length": 3,           # lagataar kitni candles chahiye
    "target_offset": 24.0,     # [USER] L +/- 24
    "recent_weeks": 2,         # pattern itne hafte ke andar pura hua ho
    "week_rule": "W-FRI",
}


def to_weekly(df, rule="W-FRI"):
    """Daily OHLCV -> weekly candles."""
    d = df.sort_values("date").set_index("date")
    w = d.resample(rule).agg(open=("open", "first"), high=("high", "max"),
                             low=("low", "min"), close=("close", "last"),
                             volume=("volume", "sum")).dropna(subset=["close"])
    return w


def straddles(w, level):
    """
    Har weekly candle ke liye: yeh level kis tarah straddle hua.
    Returns Series of "UP" / "DOWN" / None.
    """
    up = (w["close"] > level) & (w["low"] < level)
    dn = (w["close"] < level) & (w["high"] > level)
    return np.where(up, "UP", np.where(dn, "DOWN", None))


def find_runs(w, cfg=CONFIG):
    """
    Saare levels pe lagataar `run_length` candles ka pattern dhoondo.
    Returns list of dicts.
    """
    if len(w) < cfg["run_length"]:
        return []
    lo, hi = float(w["low"].min()), float(w["high"].max())
    step = cfg["level_step"]
    first = int(np.floor(lo / step)) * step
    last = min(int(np.ceil(hi / step)) * step, cfg["level_max"])
    out = []
    n = cfg["run_length"]
    for level in range(max(step, first), last + step, step):
        s = straddles(w, level)
        # lagataar n same-direction straddles
        for i in range(n - 1, len(s)):
            seg = s[i - n + 1:i + 1]
            if seg[0] is None or any(x != seg[0] for x in seg):
                continue
            direction = seg[0]
            out.append({
                "level": level,
                "direction": direction,
                "start_week": w.index[i - n + 1],
                "end_week": w.index[i],
                "weeks_ago": len(w) - 1 - i,
                "target": level + cfg["target_offset"] if direction == "UP"
                          else level - cfg["target_offset"],
                "closes": "|".join(f"{c:.1f}" for c in w["close"].values[i - n + 1:i + 1]),
                "lows": "|".join(f"{c:.1f}" for c in w["low"].values[i - n + 1:i + 1]),
                "highs": "|".join(f"{c:.1f}" for c in w["high"].values[i - n + 1:i + 1]),
                "last_close": float(w["close"].iloc[-1]),
            })
    return out


def scan(prices, cfg=CONFIG, recent_only=True):
    rows = []
    for sym, g in prices.groupby("symbol"):
        w = to_weekly(g, cfg["week_rule"])
        for r in find_runs(w, cfg):
            if recent_only and r["weeks_ago"] > cfg["recent_weeks"]:
                continue
            r["symbol"] = sym
            rows.append(r)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    # target abhi kitna door hai (aur kya pehle hi hit ho gaya)
    df["dist_to_target_pct"] = (df["target"] / df["last_close"] - 1) * 100
    df["target_offset_pct"] = cfg["target_offset"] / df["level"] * 100
    df["already_past_target"] = np.where(
        df["direction"] == "UP", df["last_close"] >= df["target"],
        df["last_close"] <= df["target"])
    cols = ["symbol", "direction", "level", "target", "last_close",
            "dist_to_target_pct", "target_offset_pct", "already_past_target",
            "weeks_ago", "start_week", "end_week", "lows", "closes", "highs"]
    return df[cols].sort_values(["direction", "target_offset_pct"], ascending=[True, False])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prices", default="ohlcv_nifty500.csv.gz")
    ap.add_argument("--all", action="store_true", help="sirf recent nahi, poora itihaas")
    ap.add_argument("--out", default="round_level_hits.csv")
    a = ap.parse_args()

    px = pd.read_csv(a.prices, parse_dates=["date"])
    px.columns = [c.lower() for c in px.columns]
    print(f"{px.symbol.nunique()} symbols, {px.date.min().date()} se {px.date.max().date()}")

    hits = scan(px, recent_only=not a.all)
    if hits.empty:
        print("Koi stock nahi mila.")
        return
    hits.to_csv(a.out, index=False)
    for d in ["UP", "DOWN"]:
        sel = hits[hits.direction == d]
        print(f"\n{'=' * 100}\n{d}  (target = level {'+' if d == 'UP' else '-'} "
              f"{CONFIG['target_offset']:.0f})   {len(sel)} hits\n{'=' * 100}")
        if len(sel):
            print(sel.drop(columns=["direction"]).to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    print(f"\nSaved: {a.out}")


if __name__ == "__main__":
    main()
