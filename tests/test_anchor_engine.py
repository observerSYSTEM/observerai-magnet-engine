from datetime import datetime, timezone

from app.services.anchor_engine import Candle, classify_anchor


def test_classify_anchor_returns_tuple():
    candle = Candle(
        time=datetime(2026, 4, 19, 7, 1, tzinfo=timezone.utc),
        open=1.0,
        high=3.0,
        low=0.0,
        close=2.0,
    )

    direction, kind, wick_ratio, body_ratio = classify_anchor(candle)

    assert direction in ["bullish", "bearish"]
    assert kind in ["rejection", "acceptance", "neutral"]
    assert 0 <= wick_ratio <= 1
    assert 0 <= body_ratio <= 1