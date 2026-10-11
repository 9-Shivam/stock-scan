"""
Psychological level helpers - chhota module, koi bhaari dependency nahi.

Yeh alag isliye hai: scan_today ko sirf levels_crossed_by_body chahiye tha, par
woh level_candle_cross me baitha tha, jo round_level_candles ko import karta hai,
jo swing_screener (59 KB) ko import karta hai. Cloud run ke liye itna saara code
le jaane ki koi zarurat nahi.
"""

import numpy as np


def levels_crossed_by_body(o, c, step, level_max):
    """
    Candle ke body (open..close) ke beech jitne `step` ke multiples aate hain.

    Body ko level tak "pahunchna" nahi hai - bas use andar lena hai.
    open 149.5, close 151 -> [150]  (1.5 point ka body bhi chalega)
    Level thik open ya close pe ho toh cross nahi maana jaata.
    """
    lo, hi = (o, c) if o < c else (c, o)
    first = int(np.floor(lo / step)) * step + step
    out, lev = [], first
    while lev < hi and lev <= level_max:
        if lev > 0:
            out.append(lev)
        lev += step
    return out
