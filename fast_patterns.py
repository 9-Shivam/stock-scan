"""
detect_candle_patterns ka vectorised version (numpy).

swing_screener wala original bar-by-bar pandas .iloc use karta hai - weekly data
pe theek hai, par daily pe 10 lakh bars hain aur woh bahut dheema pad jaata hai.
Yahan wahi rules numpy me, poore array pe ek saath.

AB YEH ORIGINAL SE MATCH NAHI KARTA - jaan boojh ke.
swing_screener wale rules teen-candle patterns pe bahut dheele the:
Three White Soldiers ke 90% aur Three Black Crows ke 64% detections me koi
candle pichli candle ke body se bahar khulti thi (yaani gap), jo kitaab ke
hisaab se pattern hi nahi hai. Morning/Evening Star ki pehli candle doji bhi
ho sakti thi. detect_all(strict=True) yeh theek karta hai - details uske
docstring me. strict=False purana behaviour deta hai.

Shape-only (trend_lookback=None wala behaviour), kyunki level-cross test me
hum trend filter use nahi kar rahe.
"""

import numpy as np

BULLISH = ["Bullish Engulfing", "Hammer", "Piercing Line", "Bullish Harami",
           "Morning Star", "Three White Soldiers", "Bullish Marubozu"]
BEARISH = ["Gravestone Doji", "Shooting Star", "Bearish Engulfing",
           "Dark Cloud Cover", "Bearish Harami", "Evening Star",
           "Three Black Crows", "Bearish Marubozu"]


def detect_all(o, h, l, c, strict=True):
    """
    Returns dict: pattern name -> boolean array (us bar pe pattern bana ya nahi).
    Pehle 2 bars hamesha False (original bhi idx<2 pe [] deta hai).

    strict=True (default) do extra sharten lagata hai jo kitaabi definition me hain
    par swing_screener ke purane code me nahi thi:

    1. Three White Soldiers / Three Black Crows: har candle PICHLI candle ke body
       ke ANDAR khulni chahiye. Bina iske gap-down/gap-up wali series bhi ginti thi -
       70,502 soldiers me se 63,332 (90%) aise hi the, aur 123,220 crows me se
       79,462 (64%).

    2. Morning Star / Evening Star: pehli candle ek asli move honi chahiye
       (body >= range ka 50%), sirf body>0 nahi. TRENT pe "Morning Star" bani thi
       jiski pehli candle ka body Rs 6.70 tha 2890 ke stock pe - woh doji hai,
       star nahi.

    strict=False purana (dhila) behaviour deta hai - sirf comparison ke liye.
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

    # body ke upar/neeche ka kinara (candle green ho ya red, dono ke liye)
    btop, bbot = np.maximum(o, c), np.minimum(o, c)
    btop1, bbot1 = shift(btop, 1), shift(bbot, 1)
    btop2, bbot2 = shift(btop, 2), shift(bbot, 2)
    # har candle pichli candle ke body ke andar khuli?
    inside1 = (o >= bbot1) & (o <= btop1)
    inside2 = (o1 >= bbot2) & (o1 <= btop2)
    opens_inside = (inside1 & inside2) if strict else np.ones(n, bool)
    # star patterns ki pehli candle asli move honi chahiye, doji nahi
    long_first = (b2 >= 0.5 * shift(rng, 2)) if strict else (b2 > 0)

    p = {}
    p["Bullish Engulfing"] = bear1 & bull & (o <= c1) & (c >= o1)
    p["Hammer"] = (rng > 0) & (body > 0) & (lower >= 2 * body) & (upper <= 0.3 * body)
    p["Piercing Line"] = bear1 & bull & (o < l1 * 1.001) & (c > (o1 + c1) / 2) & (c < o1)
    p["Bullish Harami"] = bear1 & bull & (o > c1) & (c < o1) & (body < b1)
    p["Morning Star"] = bear2 & long_first & (b1 < 0.5 * b2) & bull & (c > (o2 + c2) / 2)
    p["Three White Soldiers"] = bull2 & bull1 & bull & (c1 > c2) & (c > c1) & opens_inside
    p["Bullish Marubozu"] = (rng > 0) & bull & (body >= 0.9 * rng) & \
                            ((h - c) <= 0.05 * rng) & ((o - l) <= 0.05 * rng)

    p["Gravestone Doji"] = (rng > 0) & (body <= 0.05 * rng) & \
                           (upper >= 0.7 * rng) & (lower <= 0.05 * rng)
    p["Shooting Star"] = (rng > 0) & (body > 0) & (upper >= 2 * body) & (lower <= 0.3 * body)
    p["Bearish Engulfing"] = bull1 & bear & (o >= c1) & (c <= o1)
    p["Dark Cloud Cover"] = bull1 & bear & (o > h1 * 0.999) & (c < (o1 + c1) / 2) & (c > o1)
    p["Bearish Harami"] = bull1 & bear & (o < c1) & (c > o1) & (body < b1)
    p["Evening Star"] = bull2 & long_first & (b1 < 0.5 * b2) & bear & (c < (o2 + c2) / 2)
    p["Three Black Crows"] = bear2 & bear1 & bear & (c1 < c2) & (c < c1) & opens_inside
    p["Bearish Marubozu"] = (rng > 0) & bear & (body >= 0.9 * rng) & \
                            ((h - o) <= 0.05 * rng) & ((c - l) <= 0.05 * rng)

    for k in p:
        arr = np.nan_to_num(p[k], nan=0).astype(bool)
        arr[:2] = False                      # original idx<2 pe [] deta hai
        p[k] = arr
    return p


def verify_against_original(df, sample=400, seed=0, strict=False):
    """
    Original detect_candle_patterns se bit-by-bit milao.

    NOTE: default strict=False hai. strict=True ke saath yeh jaan boojh ke
    differ karega - kyunki tabhi toh teen-candle wale false positives rukte hain.
    """
    from swing_screener import detect_candle_patterns
    fast = detect_all(df["Open"], df["High"], df["Low"], df["Close"], strict=strict)
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
