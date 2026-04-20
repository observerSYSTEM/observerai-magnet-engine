from app.api.dashboard import signals_dashboard


def test_signals_dashboard_contains_signals_consumer():
    response = signals_dashboard()
    body = response.body.decode("utf-8")

    assert "/signals/latest" in body
    assert "/performance/summary" in body
    assert "Signals Dashboard" in body
    assert "Performance Summary" in body
    assert "formatAge" in body
    assert "renderPerformance" in body
    assert "anchor_type" in body
    assert "adr_state" in body
    assert "Nearest Magnet" in body
    assert "Major Magnet" in body
    assert "Structure Type" in body
    assert "Structure Direction" in body
    assert "Sweep Type" in body
    assert "Sweep Strength" in body
    assert "Momentum Class" in body
    assert "Momentum Direction" in body
    assert "Mid Flow" in body
    assert "Current Mid" in body
    assert "Next Mid" in body
    assert "No valid mid" in body
    assert "Magnet Path" in body
    assert "signal.magnet_path" in body
    assert "signal.mid_targets" in body
    assert "No tracked outcomes yet" in body
    assert "Performance unavailable" in body
    assert "setInterval(loadSignals, 15000)" in body
