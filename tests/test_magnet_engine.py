from app.services.magnet_engine import Candle, compute_xauusd_magnet_map


def test_compute_xauusd_magnet_map():
    candles = [
        Candle(time="2026-04-19T10:00:00", open=3346.0, high=3349.0, low=3344.8, close=3348.5),
        Candle(time="2026-04-19T10:15:00", open=3348.5, high=3350.5, low=3347.9, close=3350.1),
        Candle(time="2026-04-19T10:30:00", open=3350.1, high=3352.4, low=3349.6, close=3351.8),
        Candle(time="2026-04-19T10:45:00", open=3351.8, high=3354.0, low=3351.2, close=3353.2),
        Candle(time="2026-04-19T11:00:00", open=3353.2, high=3355.8, low=3352.8, close=3354.9),
        Candle(time="2026-04-19T11:15:00", open=3354.9, high=3357.2, low=3354.4, close=3356.3),
        Candle(time="2026-04-19T11:30:00", open=3356.3, high=3359.1, low=3355.8, close=3358.4),
    ]

    result = compute_xauusd_magnet_map(
        current_price=3358.4,
        m15_candles=candles,
        pdh=3361.4,
        pdl=3329.8,
        eq=3345.6,
        adr_high=3372.8,
        adr_low=3323.6,
        tolerance=0.60,
    )

    assert "bullish" in result
    assert "bearish" in result
    assert result["current_price"] == 3358.4
    assert result["bullish"].major is not None
    assert result["bullish"].nearest is not None
    assert result["bullish"].candidates
    assert result["bullish"].candidates[0].rank_score >= result["bullish"].candidates[-1].rank_score
    assert result["bullish"].nearest.distance >= 0.0
