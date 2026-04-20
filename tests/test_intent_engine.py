from app.services.intent_engine import build_trade_intent, resolve_bias
from app.services.market_context_engine import StructureState
from app.services.magnet_engine import Magnet


def test_resolve_bias_bullish_continuation():
    bullish_major = Magnet("PDH", 3361.4, "bullish", 10.0, False, True, "daily")

    resolved = resolve_bias(
        anchor_direction="bullish",
        event_type="m15_close_above_anchor_value_high",
        current_price=3358.4,
        value_low=3348.2,
        value_high=3350.4,
        bullish_nearest_magnet=None,
        bullish_major_magnet=bullish_major,
        bearish_nearest_magnet=None,
        bearish_major_magnet=None,
    )

    assert resolved == "bullish_continuation"


def test_resolve_bias_bearish_reversal():
    bearish_major = Magnet("PDL", 3329.8, "bearish", 10.0, False, True, "daily")
    structure = StructureState(type="mss", direction="bearish")

    resolved = resolve_bias(
        anchor_direction="bullish",
        event_type="m15_close_below_anchor_value_low",
        current_price=3346.0,
        value_low=3348.2,
        value_high=3350.4,
        bullish_nearest_magnet=None,
        bullish_major_magnet=None,
        bearish_nearest_magnet=None,
        bearish_major_magnet=bearish_major,
        structure=structure,
    )

    assert resolved == "bearish_reversal"


def test_build_trade_intent_prefers_major_target():
    nearest = Magnet("equal_highs", 3360.0, "bullish", 8.0, True, False, "m15_eqh")
    major = Magnet("PDH", 3361.4, "bullish", 10.0, False, True, "daily")

    intent = build_trade_intent(
        resolved_bias="bullish_continuation",
        event_type="m15_close_above_anchor_value_high",
        nearest_magnet=nearest,
        major_magnet=major,
        structure=StructureState(type="bos", direction="bullish"),
    )

    assert intent.action == "BUY"
    assert intent.entry_type == "continuation"
    assert intent.target == 3361.4
    assert intent.stop_hint == "below_value_low"
    assert "structure=bos:bullish" in intent.reason
