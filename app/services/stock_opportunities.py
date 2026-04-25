from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.schemas.stocks import WeeklyStockOpportunitiesResponse, WeeklyStockOpportunityOut
from app.services.mt5_symbols import get_mt5_module, resolve_broker_symbol


WATCHLIST = ("AAPL", "NVDA", "TSLA", "MSFT", "AMD", "META", "AMZN", "NFLX")


def _week_label() -> str:
    return datetime.utcnow().date().isoformat()


def _unavailable(message: str) -> WeeklyStockOpportunitiesResponse:
    return WeeklyStockOpportunitiesResponse(
        week=_week_label(),
        available=False,
        message=message,
        opportunities=[],
    )


def _initialize_mt5_for_scan() -> Any:
    settings = get_settings()
    mt5 = get_mt5_module()
    kwargs: dict[str, Any] = {}

    if settings.mt5_terminal_path:
        terminal_path = Path(settings.mt5_terminal_path).expanduser()
        if not terminal_path.exists():
            raise RuntimeError(
                f"MT5 terminal path does not exist: {settings.mt5_terminal_path}."
            )
        kwargs["path"] = str(terminal_path)
    if settings.mt5_login is not None:
        kwargs["login"] = settings.mt5_login
    if settings.mt5_password:
        kwargs["password"] = settings.mt5_password
    if settings.mt5_server:
        kwargs["server"] = settings.mt5_server

    if not mt5.initialize(**kwargs):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    return mt5


def _shutdown_mt5(mt5: Any | None) -> None:
    if mt5 is None:
        return
    try:
        mt5.shutdown()
    except Exception:
        pass


def _scan_symbol(mt5: Any, symbol: str) -> WeeklyStockOpportunityOut | None:
    try:
        broker_symbol = resolve_broker_symbol(mt5, symbol)
    except RuntimeError:
        return None

    weekly = mt5.copy_rates_from_pos(broker_symbol, mt5.TIMEFRAME_W1, 0, 10)
    daily = mt5.copy_rates_from_pos(broker_symbol, mt5.TIMEFRAME_D1, 0, 25)
    if weekly is None or daily is None or len(weekly) < 6 or len(daily) < 10:
        return None

    weekly = list(sorted(weekly, key=lambda row: row["time"]))
    daily = list(sorted(daily, key=lambda row: row["time"]))

    latest_week = weekly[-1]
    previous_weeks = weekly[-5:-1]
    latest_day = daily[-1]
    recent_days = daily[-6:-1]

    weekly_close = float(latest_week["close"])
    weekly_sma = sum(float(row["close"]) for row in previous_weeks) / len(previous_weeks)
    daily_close = float(latest_day["close"])
    prior_high = max(float(row["high"]) for row in recent_days)
    prior_low = min(float(row["low"]) for row in recent_days)
    prev_day_close = float(daily[-2]["close"])
    day_open = float(latest_day["open"])
    gap_pct = ((day_open - prev_day_close) / prev_day_close) * 100 if prev_day_close else 0.0
    avg_volume = sum(float(row["tick_volume"]) for row in recent_days) / len(recent_days)
    volume_spike = float(latest_day["tick_volume"]) > avg_volume * 1.2 if avg_volume else False
    relative_strength = ((weekly_close - float(weekly[-4]["close"])) / float(weekly[-4]["close"])) * 100

    bias = "bullish" if weekly_close >= weekly_sma else "bearish"
    breakout_up = daily_close > prior_high
    breakout_down = daily_close < prior_low

    if bias == "bullish" and breakout_up:
        confidence = 74 + (6 if volume_spike else 0) + (4 if gap_pct >= 0 else 0) + (4 if relative_strength > 0 else 0)
        return WeeklyStockOpportunityOut(
            symbol=symbol,
            bias="bullish",
            confidence=min(95, confidence),
            setup_type="weekly_liquidity_breakout",
            entry_zone=f"Above {prior_high:.2f}",
            target_zone=f"Weekly extension {weekly_close * 1.02:.2f}",
            risk_note="Check earnings and macro calendar before entry.",
            reason="Weekly trend aligns with a daily breakout, liquidity expansion, and supportive participation.",
        )

    if bias == "bearish" and breakout_down:
        confidence = 74 + (6 if volume_spike else 0) + (4 if gap_pct <= 0 else 0) + (4 if relative_strength < 0 else 0)
        return WeeklyStockOpportunityOut(
            symbol=symbol,
            bias="bearish",
            confidence=min(95, confidence),
            setup_type="weekly_liquidity_breakout",
            entry_zone=f"Below {prior_low:.2f}",
            target_zone=f"Weekly extension {weekly_close * 0.98:.2f}",
            risk_note="Check earnings and macro calendar before entry.",
            reason="Weekly pressure aligns with a daily breakdown, liquidity clearance, and expanding downside participation.",
        )

    return None


def scan_weekly_stock_opportunities() -> WeeklyStockOpportunitiesResponse:
    """
    Scan the stock watchlist using MT5 CFDs when available.

    If the current broker feed does not expose stock data, the endpoint returns
    a clean unavailable state instead of failing the rest of the backend.
    """

    mt5: Any | None = None
    try:
        mt5 = _initialize_mt5_for_scan()
    except Exception:
        return _unavailable("Stock data not available from current MT5 broker feed.")

    try:
        opportunities = [item for item in (_scan_symbol(mt5, symbol) for symbol in WATCHLIST) if item is not None]
        opportunities.sort(key=lambda item: item.confidence, reverse=True)
        return WeeklyStockOpportunitiesResponse(
            week=_week_label(),
            available=bool(opportunities),
            message=None if opportunities else "Stock data not available from current MT5 broker feed.",
            opportunities=opportunities,
        )
    finally:
        _shutdown_mt5(mt5)
