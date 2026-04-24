from app.api.dashboard import signals_dashboard


def test_signals_dashboard_contains_multi_symbol_lifecycle_consumer():
    response = signals_dashboard()
    body = response.body.decode("utf-8")

    assert "/signals/best" in body
    assert "/signals/latest" in body
    assert "/liquidity/magnets" in body
    assert "Signals Dashboard" in body
    assert "Best Signal Now" in body
    assert "Strongest Liquidity Magnet" in body
    assert "Swing Liquidity" in body
    assert "H1 Magnets" in body
    assert "H4 Magnets" in body
    assert "Scalping Signals" in body
    assert "SUPPORTED_SYMBOLS" in body
    assert "XAUUSD" in body
    assert "BTCUSD" in body
    assert "GBPJPY" in body
    assert "Next M15 close in:" in body
    assert "No signals yet for this symbol." in body
    assert "Lifecycle" in body
    assert "Tradeable" in body
    assert "Not Tradeable" in body
    assert "formatLifecycle" in body
    assert "humanizeLabel" in body
    assert "renderStrongestLiquidity" in body
    assert "setInterval(loadDashboard, REFRESH_INTERVAL_MS)" in body
    assert "setInterval(updateM15Timer, 1000)" in body
