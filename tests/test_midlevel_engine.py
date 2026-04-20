from app.services.magnet_engine import Candle
from app.services.midlevel_engine import compute_mid_targets


def test_compute_mid_targets_bullish_mid_to_mid():
    candles = [
        Candle(time="2026-04-20T10:00:00", open=108.0, high=112.0, low=108.0, close=110.0),
        Candle(time="2026-04-20T10:15:00", open=110.0, high=114.0, low=109.0, close=113.0),
        Candle(time="2026-04-20T10:30:00", open=113.0, high=113.0, low=106.0, close=107.0),
    ]

    targets = compute_mid_targets(
        current_price=104.0,
        bias="bullish_continuation",
        anchor_high=102.0,
        anchor_low=98.0,
        daily_eq=105.0,
        m15_candles=candles,
    )

    assert targets.flow == "bullish_mid_to_mid"
    assert targets.current_mid is not None
    assert targets.current_mid.name == "anchor_mid"
    assert targets.current_mid.price == 100.0
    assert targets.next_mid is not None
    assert targets.next_mid.name == "daily_eq"
    assert targets.next_mid.price == 105.0


def test_compute_mid_targets_bearish_mid_to_mid():
    candles = [
        Candle(time="2026-04-20T10:00:00", open=88.0, high=92.0, low=88.0, close=90.0),
        Candle(time="2026-04-20T10:15:00", open=90.0, high=94.0, low=89.0, close=93.0),
        Candle(time="2026-04-20T10:30:00", open=93.0, high=93.0, low=86.0, close=87.0),
    ]

    targets = compute_mid_targets(
        current_price=96.0,
        bias="bearish_continuation",
        anchor_high=102.0,
        anchor_low=98.0,
        daily_eq=95.0,
        m15_candles=candles,
    )

    assert targets.flow == "bearish_mid_to_mid"
    assert targets.current_mid is not None
    assert targets.current_mid.name == "anchor_mid"
    assert targets.current_mid.price == 100.0
    assert targets.next_mid is not None
    assert targets.next_mid.name == "daily_eq"
    assert targets.next_mid.price == 95.0


def test_compute_mid_targets_no_valid_next_mid():
    candles = [
        Candle(time="2026-04-20T10:00:00", open=108.0, high=112.0, low=108.0, close=110.0),
        Candle(time="2026-04-20T10:15:00", open=110.0, high=114.0, low=109.0, close=113.0),
        Candle(time="2026-04-20T10:30:00", open=113.0, high=113.0, low=106.0, close=107.0),
    ]

    targets = compute_mid_targets(
        current_price=112.0,
        bias="bullish_continuation",
        anchor_high=102.0,
        anchor_low=98.0,
        daily_eq=105.0,
        m15_candles=candles,
    )

    assert targets.flow == "no_mid_flow"
    assert targets.current_mid is not None
    assert targets.next_mid is None


def test_compute_mid_targets_mid_compression():
    candles = [
        Candle(time="2026-04-20T10:00:00", open=106.0, high=110.0, low=106.0, close=108.0),
        Candle(time="2026-04-20T10:15:00", open=108.0, high=111.0, low=107.0, close=110.0),
        Candle(time="2026-04-20T10:30:00", open=110.0, high=110.0, low=104.0, close=105.0),
    ]

    targets = compute_mid_targets(
        current_price=100.2,
        bias="bullish_continuation",
        anchor_high=100.2,
        anchor_low=100.0,
        daily_eq=100.4,
        m15_candles=candles,
        compression_threshold=0.75,
    )

    assert targets.current_mid is not None
    assert targets.next_mid is not None
    assert targets.flow == "mid_compression"
