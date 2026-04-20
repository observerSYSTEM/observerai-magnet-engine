from __future__ import annotations


def detect_m15_event(
    prev_close: float,
    curr_close: float,
    eq: float,
    discount_high: float,
    premium_low: float,
    value_high: float,
    value_low: float,
    pdh: float,
    pdl: float,
) -> str:
    """
    Detects key M15 close events for the ObserverAI Magnet Engine.
    """

    if prev_close <= eq and curr_close > eq:
        return "m15_close_above_eq"

    if prev_close >= eq and curr_close < eq:
        return "m15_close_below_eq"

    if prev_close <= discount_high and curr_close > discount_high:
        return "m15_close_above_discount_high"

    if prev_close >= premium_low and curr_close < premium_low:
        return "m15_close_below_premium_low"

    if prev_close <= value_high and curr_close > value_high:
        return "m15_close_above_anchor_value_high"

    if prev_close >= value_low and curr_close < value_low:
        return "m15_close_below_anchor_value_low"

    if prev_close <= pdh and curr_close > pdh:
        return "m15_close_above_pdh"

    if prev_close >= pdl and curr_close < pdl:
        return "m15_close_below_pdl"

    return "no_event"