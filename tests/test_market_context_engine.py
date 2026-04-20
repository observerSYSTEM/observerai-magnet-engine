from app.services.market_context_engine import (
    classify_candle_momentum,
    detect_liquidity_sweep,
    detect_structure,
)
from app.services.magnet_engine import Candle


def test_detect_liquidity_sweep_sellside():
    candles = [
        Candle(time="2026-04-19T10:00:00", open=3350.0, high=3352.0, low=3348.0, close=3351.0),
        Candle(time="2026-04-19T10:15:00", open=3351.0, high=3353.0, low=3349.0, close=3352.0),
        Candle(time="2026-04-19T10:30:00", open=3352.0, high=3352.8, low=3347.0, close=3349.6),
    ]

    sweep = detect_liquidity_sweep(candles)

    assert sweep.type == "sellside"
    assert sweep.strength > 0.0


def test_detect_structure_bos_and_momentum():
    candles = [
        Candle(time="2026-04-19T10:00:00", open=3346.0, high=3349.0, low=3344.8, close=3348.5),
        Candle(time="2026-04-19T10:15:00", open=3348.5, high=3350.5, low=3347.9, close=3350.1),
        Candle(time="2026-04-19T10:30:00", open=3350.1, high=3352.4, low=3349.6, close=3351.8),
        Candle(time="2026-04-19T10:45:00", open=3351.8, high=3354.0, low=3351.2, close=3353.2),
        Candle(time="2026-04-19T11:00:00", open=3353.2, high=3355.8, low=3352.8, close=3354.9),
        Candle(time="2026-04-19T11:15:00", open=3354.9, high=3357.2, low=3354.4, close=3356.3),
        Candle(time="2026-04-19T11:30:00", open=3356.3, high=3360.8, low=3355.8, close=3360.1),
    ]

    structure = detect_structure(candles, anchor_direction="bullish")
    momentum = classify_candle_momentum(candles[-1])

    assert structure.type == "bos"
    assert structure.direction == "bullish"
    assert momentum.direction == "bullish"
    assert momentum.classification in {"moderate", "strong"}
