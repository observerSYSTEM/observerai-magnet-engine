from app.services.event_engine import detect_m15_event


def test_detect_m15_close_above_eq():
    event = detect_m15_event(
        prev_close=3345.0,
        curr_close=3350.0,
        eq=3348.0,
        discount_high=3346.0,
        premium_low=3355.0,
        value_high=3349.0,
        value_low=3347.0,
        pdh=3360.0,
        pdl=3330.0,
    )
    assert event == "m15_close_above_eq"


def test_detect_no_event():
    event = detect_m15_event(
        prev_close=3348.2,
        curr_close=3348.4,
        eq=3348.0,
        discount_high=3346.0,
        premium_low=3355.0,
        value_high=3350.0,
        value_low=3347.0,
        pdh=3360.0,
        pdl=3330.0,
    )
    assert event == "no_event"