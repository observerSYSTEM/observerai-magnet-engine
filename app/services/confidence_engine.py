from __future__ import annotations


def score_signal(
    event_type: str,
    bias: str,
    anchor_direction: str,
    anchor_type: str,
    adr_used_pct: float,
    has_nearest_magnet: bool,
    has_major_magnet: bool,
    magnet_path_depth: int = 0,
    sweep_type: str = "none",
    sweep_strength: float = 0.0,
    structure_type: str = "none",
    structure_direction: str = "neutral",
    momentum_classification: str = "weak",
    momentum_direction: str = "neutral",
    mid_flow: str = "no_mid_flow",
) -> int:
    score = 50

    bullish_event = "above" in event_type
    bearish_event = "below" in event_type

    if bullish_event and "bullish" in bias:
        score += 12
    if bearish_event and "bearish" in bias:
        score += 12

    if bullish_event and anchor_direction == "bullish":
        score += 10
    if bearish_event and anchor_direction == "bearish":
        score += 10

    if anchor_type == "acceptance":
        score += 8
    elif anchor_type == "rejection":
        score += 6
    else:
        score -= 4

    if adr_used_pct < 50:
        score += 8
    elif adr_used_pct < 80:
        score += 3
    elif adr_used_pct <= 100:
        score -= 6
    else:
        score -= 12

    if has_nearest_magnet:
        score += 5
    if has_major_magnet:
        score += 7
    if magnet_path_depth >= 3:
        score += 4
    elif magnet_path_depth > 0:
        score += 2

    if "continuation" in bias and structure_type == "bos" and structure_direction in bias:
        score += 8
    if "reversal" in bias and structure_type == "mss" and structure_direction in bias:
        score += 8

    if "bullish" in bias and sweep_type == "sellside":
        score += min(6, int(round(sweep_strength)))
    if "bearish" in bias and sweep_type == "buyside":
        score += min(6, int(round(sweep_strength)))

    if momentum_direction in bias and momentum_classification == "strong":
        score += 8
    elif momentum_direction in bias and momentum_classification == "moderate":
        score += 4
    elif momentum_direction not in {"neutral", ""} and momentum_direction not in bias and momentum_classification == "strong":
        score -= 6

    if "bullish" in bias and mid_flow == "bullish_mid_to_mid":
        score += 5
    elif "bearish" in bias and mid_flow == "bearish_mid_to_mid":
        score += 5
    elif mid_flow == "mid_compression":
        score -= 4
    elif mid_flow == "no_mid_flow":
        score -= 2

    return max(0, min(100, score))
