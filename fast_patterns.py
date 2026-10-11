"""
detect_candle_patterns ka vectorised version (numpy).

swing_screener wala original bar-by-bar pandas .iloc use karta hai - weekly data
pe theek hai, par daily pe 10 lakh bars hain aur woh bahut dheema pad jaata hai.
Yahan wahi rules numpy me, poore array pe ek saath.

Rules bilkul wahi hain - verify_against_original() se check kar sakte ho.
Shape-only (trend_lookback=None wala behaviour), kyunki level-cross test me
hum trend filter use nahi kar rahe.
"""

import numpy as np

BULLISH = ["Bullish Engulfing", "Hammer", "Piercing Line", "Bullish Harami",
           "Morning Star", "Three White Soldiers", "Bullish Marubozu"]
BEARISH = ["Gravestone Doji", "Shooting Star", "Bearish Engulfing",
           "Dark Cloud Cover", "Bearish Harami", "Evening Star",
           "Three Black Crows", "Bearish Marubozu"]


def detect_all(o, h, l, c):
    """
    Returns dict: pattern name -> boolean array (us bar pe pattern bana ya nahi).
    Pehle 2 bars hamesha False (original bhi idx<2 pe [] deta hai).
    """
    o, h, l, c = (np.asarray(x, dtype=float) for x in (o, h, l, c))
    n = len(o)
    body = np.abs(c - o)
    rng = h - l
    bull = c > o
    bear = c < o
    upper = h - np.maximum(o, c)
    lower = np.minimum(o, c) - l

    def shift(a, k):
        """a[i-k], out-of-range pe False/NaN."""
        out = np.full(n, np.nan)
        if k < n:
            out[k:] = a[:n - k]
        return out

    b1, b2 = shift(body, 1), shift(body, 2)
    o1, o2 = shift(o, 1), shift(o, 2)
    c1, c2 = shift(c, 1), shift(c, 2)
    h1, l1 = shift(h, 1), shift(l, 1)
    bull1, bull2 = shift(bull.astype(float), 1) == 1, shift(bull.astype(float), 2) == 1
    bear1, bear2 = shift(bear.astype(float), 1) == 1, shift(bear.astype(float), 2) == 1

    p = {}
    p["Bullish Engulfing"] = bear1 & bull & (o <= c1) & (c >= o1)
    p["Hammer"] = (rng > 0) & (body > 0) & (lower >= 2 * body) & (upper <= 0.3 * body)
    p["Piercing Line"] = bear1 & bull & (o < l1 * 1.001) & (c > (o1 + c1) / 2) & (c < o1)
    p["Bullish Harami"] = bear1 & bull & (o > c1) & (c < o1) & (body < b1)
    p["Morning Star"] = bear2 & (b2 > 0) & (b1 < 0.5 * b2) & bull & (c > (o2 + c2) / 2)
    p["Three White Soldiers"] = bull2 & bull1 & bull & (c1 > c2) & (c > c1)
    p["Bullish Marubozu"] = (rng > 0) & bull & (body >= 0.9 * rng) & \
                            ((h - c) <= 0.05 * rng) & ((o - l) <= 0.05 * rng)

    p["Gravestone Doji"] = (rng > 0) & (body <= 0.05 * rng) & \
                           (upper >= 0.7 * rng) & (lower <= 0.05 * rng)
    p["Shooting Star"] = (rng > 0) & (body > 0) & (upper >= 2 * body) & (lower <= 0.3 * body)
    p["Bearish Engulfing"] = bull1 & bear & (o >= c1) & (c <= o1)
    p["Dark Cloud Cover"] = bull1 & bear & (o > h1 * 0.999) & (c < (o1 + c1) / 2) & (c > o1)
    p["Bearish Harami"] = bull1 & bear & (o < c1) & (c > o1) & (body < b1)
    p["Evening Star"] = bull2 & (b2 > 0) & (b1 < 0.5 * b2) & bear & (c < (o2 + c2) / 2)
    p["Three Black Crows"] = bear2 & bear1 & bear & (c1 < c2) & (c < c1)
    p["Bearish Marubozu"] = (rng > 0) & bear & (body >= 0.9 * rng) & \
                            ((h - o) <= 0.05 * rng) & ((c - l) <= 0.05 * rng)

    for k in p:
        arr = np.nan_to_num(p[k], nan=0).astype(bool)
        arr[:2] = False                      # original idx<2 pe [] deta hai
        p[k] = arr
    return p


def verify_against_original(df, sample=400, seed=0):
    """Original detect_candle_patterns se bit-by-bit milao."""
    from swing_screener import detect_candle_patterns
    fast = detect_all(df["Open"], df["High"], df["Low"], df["Close"])
    rng = np.random.default_rng(seed)
    idxs = rng.choice(np.arange(2, len(df)), size=min(sample, len(df) - 2), replace=False)
    bad = 0
    for i in idxs:
        ref = set(detect_candle_patterns(df, idx=int(i)))
        mine = {k for k, v in fast.items() if v[i]}
        if ref != mine:
            bad += 1
            if bad <= 5:
                print(f"  MISMATCH at {i}: original={sorted(ref)} fast={sorted(mine)}")
    return len(idxs) - bad, len(idxs)
