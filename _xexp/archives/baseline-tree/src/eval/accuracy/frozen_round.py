"""Step 7-E Accuracy Validator — frozen_round (§12).

工程四舍五入，冻结实现。
    Decimal(str(value)) + ROUND_HALF_UP
禁止 Python round()（banker's rounding）。
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any


def frozen_round(value: Any, decimals: int) -> float:
    """§12 — frozen_round.

    Raises (in order):
        ① ValueError   if value is None
        ② ValueError   if value is NaN or ±Inf
        ③ TypeError    if decimals is not int or decimals < 0

    Mathematical semantics (frozen, B2 zero-change):
        Decimal(str(value)).quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)
        then cast to float.
    """
    # ① None guard
    if value is None:
        raise ValueError("frozen_round: value must not be None")

    # Use str() to get clean decimal representation — avoids float binary noise
    d = Decimal(str(value))

    # ② NaN / ±Inf guard
    if d.is_nan() or d.is_infinite():
        raise ValueError("frozen_round: value must be finite (NaN / Inf forbidden)")

    # ③ decimals type + range guard
    if not isinstance(decimals, int) or decimals < 0:
        raise TypeError("frozen_round: decimals must be a non-negative int")

    # ④ Legal input: quantize with ROUND_HALF_UP
    if decimals == 0:
        quantize_str = "1"
    else:
        quantize_str = "0." + ("0" * decimals)

    return float(d.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP))
