from app.api.dashboard import signals_dashboard


def test_signals_dashboard_contains_v2_sections():
    response = signals_dashboard()
    body = response.body.decode("utf-8")

    assert "/v2/dashboard-summary" in body
    assert "/v2/intelligence" in body
    assert "/stocks/weekly-opportunities" in body
    assert "ObserverAI Dashboard v2" in body
    assert "Best Direction Now" in body
    assert "08:01 Anchor" in body
    assert "Zone-to-Zone Liquidity" in body
    assert "M15 Midlevel Break" in body
    assert "Volatility + Manipulation" in body
    assert "News Direction" in body
    assert "Weekly Stock Opportunities" in body
    assert "Multi-Symbol Overview" in body
    assert "SUPPORTED_SYMBOLS" in body
    assert "XAUUSD" in body
    assert "BTCUSD" in body
    assert "GBPJPY" in body
    assert "Next M15 close in:" in body
    assert "No signals yet for this symbol." in body
    assert "setInterval(loadDashboard, REFRESH_INTERVAL_MS)" in body
    assert "setInterval(updateM15Timer, 1000)" in body
