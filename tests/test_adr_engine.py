from app.services.adr_engine import DailyCandle, compute_adr


def test_compute_adr():
    candles = [
        DailyCandle(time="2026-04-18", open=3331.0, high=3356.0, low=3328.0, close=3348.0),  # 28
        DailyCandle(time="2026-04-17", open=3318.0, high=3342.0, low=3310.0, close=3330.0),  # 32
        DailyCandle(time="2026-04-16", open=3348.0, high=3360.0, low=3335.0, close=3320.0),  # 25
        DailyCandle(time="2026-04-15", open=3302.0, high=3329.0, low=3296.0, close=3318.0),  # 33
        DailyCandle(time="2026-04-14", open=3280.0, high=3311.0, low=3279.0, close=3301.0),  # 32
    ]

    adr = compute_adr(candles, lookback_days=5)
    assert adr == 30.0