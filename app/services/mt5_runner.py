from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.symbols import normalize_symbol
from app.services.anchor_engine import london_time_to_utc
from app.services.mt5_symbols import get_mt5_module, resolve_broker_symbol
from app.schemas.oracle import (
    OracleEvaluateRequest,
    OracleEvaluateResponse,
    OraclePriceCandleIn,
    OracleTimedCandleIn,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import httpx

M1_ATR_PERIOD = 14
M15_LOOKBACK_BARS = 160
H1_LOOKBACK_BARS = 240
H4_LOOKBACK_BARS = 180
POST_RETRY_ATTEMPTS = 3
POST_RETRY_DELAY_SECONDS = 3


class RunnerSkipCycle(RuntimeError):
    """Recoverable runner precondition failure for the current polling cycle."""


@dataclass(frozen=True)
class RunnerSnapshot:
    symbol: str
    broker_symbol: str
    current_price: float
    prev_m15_close: float
    atr_m1: float
    m1_count: int
    m15_count: int
    h1_count: int
    h4_count: int
    daily_levels_count: int
    daily_adr_count: int

def _utc_from_timestamp(timestamp: int | float) -> datetime:
    return datetime.fromtimestamp(int(timestamp), tz=timezone.utc)


def _to_timed_candle(rate: Any) -> OracleTimedCandleIn:
    timestamp = _utc_from_timestamp(rate["time"])
    return OracleTimedCandleIn(
        time=timestamp,
        open=float(rate["open"]),
        high=float(rate["high"]),
        low=float(rate["low"]),
        close=float(rate["close"]),
    )


def _to_price_candle(rate: Any, *, daily: bool = False) -> OraclePriceCandleIn:
    timestamp = _utc_from_timestamp(rate["time"])
    time_value = timestamp.date().isoformat() if daily else timestamp.isoformat().replace("+00:00", "Z")
    return OraclePriceCandleIn(
        time=time_value,
        open=float(rate["open"]),
        high=float(rate["high"]),
        low=float(rate["low"]),
        close=float(rate["close"]),
    )


def _initialize_mt5(settings: Settings) -> Any:
    mt5 = get_mt5_module()
    kwargs: dict[str, Any] = {}
    if settings.mt5_terminal_path:
        terminal_path = Path(settings.mt5_terminal_path).expanduser()
        if not terminal_path.exists():
            raise RuntimeError(
                f"MT5 terminal path does not exist: {settings.mt5_terminal_path}. Update MT5_TERMINAL_PATH before live verification."
            )
        kwargs["path"] = str(terminal_path)
    if settings.mt5_login is not None:
        kwargs["login"] = settings.mt5_login
    if settings.mt5_password:
        kwargs["password"] = settings.mt5_password
    if settings.mt5_server:
        kwargs["server"] = settings.mt5_server

    logger.info(
        "Connecting to MT5 | login=%s server=%s terminal_path=%s",
        settings.mt5_login,
        settings.mt5_server or "default",
        settings.mt5_terminal_path or "auto",
    )
    if not mt5.initialize(**kwargs):
        raise RuntimeError(
            "MT5 initialize failed "
            f"(login={settings.mt5_login}, server={settings.mt5_server or 'default'}, terminal_path={settings.mt5_terminal_path or 'auto'}): "
            f"{mt5.last_error()}"
        )

    logger.info("MT5 connected | version=%s", mt5.version())
    return mt5


def _shutdown_mt5(mt5: Any | None) -> None:
    if mt5 is None:
        return
    try:
        mt5.shutdown()
    except Exception:
        logger.exception("MT5 shutdown failed.")


def _copy_rates_from_pos(mt5: Any, symbol: str, timeframe: int, count: int) -> list[Any]:
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"MT5 returned no rates for {symbol} timeframe={timeframe}.")
    return sorted(rates, key=lambda rate: rate["time"])


def _copy_m1_rates_for_day(mt5: Any, symbol: str, trading_day_utc: datetime) -> list[Any]:
    start = trading_day_utc
    end = datetime.now(timezone.utc) + timedelta(minutes=1)
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start, end)
    if rates is None or len(rates) == 0:
        logger.info(
            "Market closed or no live session data yet | symbol=%s | waiting for market open",
            symbol,
        )
        raise RunnerSkipCycle(
            f"Market closed or no live session data yet for {symbol} on {trading_day_utc.date()}; waiting for market open."
        )
    return sorted(rates, key=lambda rate: rate["time"])


def _copy_daily_rates(mt5: Any, symbol: str, count: int) -> list[Any]:
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, count)
    if rates is None or len(rates) < count:
        raise RuntimeError(f"MT5 returned insufficient D1 rates for {symbol}.")
    return sorted(rates, key=lambda rate: rate["time"])


def _ensure_m1_history_ready(m1_rates: list[Any], symbol: str, period: int = M1_ATR_PERIOD) -> None:
    required = period + 1
    available = len(m1_rates)
    if available >= required:
        return

    logger.warning(
        "Insufficient M1 history | symbol=%s available=%s required=%s reason=ATR(M1) needs completed candles",
        symbol,
        available,
        required,
    )
    raise RunnerSkipCycle(
        f"Insufficient M1 history for {symbol}: have {available} candles, need at least {required} to compute ATR(M1)."
    )


def _ensure_m15_history_ready(m15_rates: list[Any], symbol: str) -> None:
    available = len(m15_rates)
    if available < 2:
        logger.warning(
            "Insufficient M15 history | symbol=%s available=%s required_min=2 requested=%s",
            symbol,
            available,
            M15_LOOKBACK_BARS,
        )
        raise RunnerSkipCycle(
            f"Insufficient M15 history for {symbol}: have {available} candles, need at least 2 to compute the previous M15 close."
        )

    if available < M15_LOOKBACK_BARS:
        logger.warning(
            "Limited M15 history | symbol=%s available=%s requested=%s",
            symbol,
            available,
            M15_LOOKBACK_BARS,
        )


def _ensure_london_anchor_candle_ready(
    m1_rates: list[Any],
    trading_day_utc: datetime,
    symbol: str,
    now_utc: datetime,
) -> None:
    target = london_time_to_utc(trading_day_utc, 8, 1)
    target_timestamp = int(target.timestamp())

    for rate in m1_rates:
        if int(rate["time"]) == target_timestamp:
            return

    reason = (
        "session has not reached London 08:01 yet"
        if now_utc < target
        else "candle is missing from current M1 history"
    )
    logger.warning(
        "London 08:01 candle not found | symbol=%s trading_day=%s expected_utc=%s reason=%s",
        symbol,
        trading_day_utc.date(),
        target.isoformat(),
        reason,
    )
    raise RunnerSkipCycle(
        f"London 08:01 candle unavailable for {symbol} at {target.isoformat()} ({reason})."
    )


def _compute_atr_m1(m1_rates: list[Any], period: int = M1_ATR_PERIOD) -> float:
    completed_rates = m1_rates[:-1] if len(m1_rates) > period + 1 else m1_rates
    if len(completed_rates) < period + 1:
        raise RuntimeError(f"Need at least {period + 1} M1 candles to compute ATR.")

    recent = completed_rates[-(period + 1) :]
    previous_close = float(recent[0]["close"])
    true_ranges: list[float] = []

    for rate in recent[1:]:
        high = float(rate["high"])
        low = float(rate["low"])
        close = float(rate["close"])
        true_range = max(high - low, abs(high - previous_close), abs(low - previous_close))
        true_ranges.append(true_range)
        previous_close = close

    return round(sum(true_ranges) / len(true_ranges), 5)


def _resolve_current_price(mt5: Any, symbol: str, fallback_price: float) -> float:
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return round(fallback_price, 5)

    bid = float(getattr(tick, "bid", 0.0) or 0.0)
    ask = float(getattr(tick, "ask", 0.0) or 0.0)
    last = float(getattr(tick, "last", 0.0) or 0.0)

    if bid > 0 and ask > 0:
        return round((bid + ask) / 2.0, 5)
    if last > 0:
        return round(last, 5)
    if bid > 0:
        return round(bid, 5)
    if ask > 0:
        return round(ask, 5)
    return round(fallback_price, 5)


def build_live_oracle_payload(
    mt5: Any,
    settings: Settings,
    symbol: str | None = None,
) -> tuple[OracleEvaluateRequest, RunnerSnapshot]:
    """
    Build a live oracle payload from MetaTrader 5 market data.

    The payload is shaped to match POST /oracle/evaluate exactly.
    """

    instrument = normalize_symbol(symbol or settings.normalized_default_symbol)
    broker_symbol = resolve_broker_symbol(mt5, instrument)

    now_utc = datetime.now(timezone.utc)
    trading_day_utc = datetime(now_utc.year, now_utc.month, now_utc.day, tzinfo=timezone.utc)

    m1_rates = _copy_m1_rates_for_day(mt5, broker_symbol, trading_day_utc)
    _ensure_m1_history_ready(m1_rates, instrument)
    _ensure_london_anchor_candle_ready(m1_rates, trading_day_utc, instrument, now_utc)

    m15_rates = _copy_rates_from_pos(mt5, broker_symbol, mt5.TIMEFRAME_M15, M15_LOOKBACK_BARS)
    _ensure_m15_history_ready(m15_rates, instrument)
    h1_rates = _copy_rates_from_pos(mt5, broker_symbol, mt5.TIMEFRAME_H1, H1_LOOKBACK_BARS)
    h4_rates = _copy_rates_from_pos(mt5, broker_symbol, mt5.TIMEFRAME_H4, H4_LOOKBACK_BARS)

    daily_rates = _copy_daily_rates(mt5, broker_symbol, settings.adr_lookback_days + 2)

    current_price = _resolve_current_price(mt5, broker_symbol, float(m15_rates[-1]["close"]))
    prev_m15_close = round(float(m15_rates[-2]["close"]), 5)
    atr_m1 = _compute_atr_m1(m1_rates)

    current_daily = daily_rates[-1]
    previous_daily = daily_rates[-2]
    completed_daily = list(reversed(daily_rates[-(settings.adr_lookback_days + 1) : -1]))

    payload = OracleEvaluateRequest(
        symbol=instrument,
        current_price=current_price,
        prev_m15_close=prev_m15_close,
        atr_m1=atr_m1,
        m1_candles=[_to_timed_candle(rate) for rate in m1_rates],
        m15_candles=[_to_price_candle(rate) for rate in m15_rates],
        h1_candles=[_to_price_candle(rate) for rate in h1_rates],
        h4_candles=[_to_price_candle(rate) for rate in h4_rates],
        daily_candles_for_levels=[
            _to_price_candle(current_daily, daily=True),
            _to_price_candle(previous_daily, daily=True),
        ],
        daily_candles_for_adr=[_to_price_candle(rate, daily=True) for rate in completed_daily],
    )

    snapshot = RunnerSnapshot(
        symbol=instrument,
        broker_symbol=broker_symbol,
        current_price=current_price,
        prev_m15_close=prev_m15_close,
        atr_m1=atr_m1,
        m1_count=len(payload.m1_candles),
        m15_count=len(payload.m15_candles),
        h1_count=len(payload.h1_candles or []),
        h4_count=len(payload.h4_candles or []),
        daily_levels_count=len(payload.daily_candles_for_levels),
        daily_adr_count=len(payload.daily_candles_for_adr),
    )
    return payload, snapshot


def post_oracle_payload(
    payload: OracleEvaluateRequest,
    api_base_url: str,
    client: Any | None = None,
) -> OracleEvaluateResponse:
    """POST a live payload to the ObserverAI oracle endpoint."""

    import httpx

    url = f"{api_base_url.rstrip('/')}/oracle/evaluate"
    owns_client = client is None
    http_client = client or httpx.Client(timeout=30)

    try:
        response = http_client.post(url, json=payload.model_dump(mode="json"))
        response.raise_for_status()
        return OracleEvaluateResponse.model_validate(response.json())
    finally:
        if owns_client:
            http_client.close()


def _post_oracle_with_retries(
    payload: OracleEvaluateRequest,
    settings: Settings,
) -> OracleEvaluateResponse:
    last_error: Exception | None = None

    for attempt in range(1, POST_RETRY_ATTEMPTS + 1):
        try:
            logger.info(
                "Posting oracle payload | attempt=%s/%s api_base_url=%s",
                attempt,
                POST_RETRY_ATTEMPTS,
                settings.api_base_url,
            )
            result = post_oracle_payload(payload, settings.api_base_url)
            logger.info(
                "Oracle response | symbol=%s action=%s resolved_bias=%s event=%s confidence=%s target=%s",
                result.symbol,
                result.intent.action,
                result.resolved_bias,
                result.event_type,
                result.confidence,
                result.intent.target,
            )
            return result
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Oracle POST failed | attempt=%s/%s error=%s",
                attempt,
                POST_RETRY_ATTEMPTS,
                exc,
            )
            if attempt < POST_RETRY_ATTEMPTS:
                time.sleep(POST_RETRY_DELAY_SECONDS)

    raise RuntimeError("Oracle POST failed after all retries.") from last_error


def run_live_mt5_runner() -> None:
    """Run the live MT5 polling loop for signal generation."""

    configure_logging()
    settings = get_settings()
    interval_seconds = max(1, settings.runner_interval_seconds)
    mt5: Any | None = None
    cycle = 0

    logger.info(
        "Runner startup | terminal_path=%s server=%s login=%s symbols=%s api_base_url=%s interval=%ss",
        settings.mt5_terminal_path or "auto",
        settings.mt5_server or "default",
        settings.mt5_login if settings.mt5_login is not None else "unset",
        ",".join(settings.runner_symbols),
        settings.api_base_url,
        interval_seconds,
    )

    try:
        while True:
            cycle += 1
            cycle_started = time.monotonic()
            logger.info(
                "Runner heartbeat | cycle=%s symbols=%s status=starting",
                cycle,
                ",".join(settings.runner_symbols),
            )

            try:
                if mt5 is None:
                    mt5 = _initialize_mt5(settings)

                any_success = False
                any_waiting = False
                any_failure = False

                for symbol in settings.runner_symbols:
                    logger.info("Runner evaluating symbol=%s", symbol)
                    try:
                        payload, snapshot = build_live_oracle_payload(mt5, settings, symbol=symbol)
                        logger.info(
                            "Payload generated | symbol=%s broker_symbol=%s current_price=%.5f prev_m15_close=%.5f atr_m1=%.5f m1=%s m15=%s h1=%s h4=%s d1_levels=%s d1_adr=%s",
                            snapshot.symbol,
                            snapshot.broker_symbol,
                            snapshot.current_price,
                            snapshot.prev_m15_close,
                            snapshot.atr_m1,
                            snapshot.m1_count,
                            snapshot.m15_count,
                            snapshot.h1_count,
                            snapshot.h4_count,
                            snapshot.daily_levels_count,
                            snapshot.daily_adr_count,
                        )
                        _post_oracle_with_retries(payload, settings)
                        any_success = True
                    except RunnerSkipCycle as exc:
                        any_waiting = True
                        logger.warning(
                            "Runner cycle waiting for live data | cycle=%s symbol=%s reason=%s",
                            cycle,
                            symbol,
                            exc,
                        )
                    except Exception:
                        any_failure = True
                        logger.exception("Runner cycle failed | cycle=%s symbol=%s", cycle, symbol)

                if any_success:
                    elapsed = time.monotonic() - cycle_started
                    sleep_for = max(0.0, interval_seconds - elapsed)
                    logger.info("Runner heartbeat | cycle=%s status=ok next_run_in=%.1fs", cycle, sleep_for)
                    time.sleep(sleep_for)
                    continue

                retry_sleep = min(interval_seconds, 10)
                if any_waiting and not any_failure:
                    logger.info(
                        "Runner heartbeat | cycle=%s status=waiting_for_data next_run_in=%ss",
                        cycle,
                        retry_sleep,
                    )
                else:
                    _shutdown_mt5(mt5)
                    mt5 = None
                    logger.info(
                        "Runner heartbeat | cycle=%s status=retrying next_run_in=%ss",
                        cycle,
                        retry_sleep,
                    )
                time.sleep(retry_sleep)
                continue
            except RunnerSkipCycle as exc:
                logger.warning(
                    "Runner cycle waiting for live data | cycle=%s symbol=%s reason=%s",
                    cycle,
                    settings.normalized_default_symbol,
                    exc,
                )
                retry_sleep = min(interval_seconds, 10)
                logger.info("Runner heartbeat | cycle=%s status=waiting_for_data next_run_in=%ss", cycle, retry_sleep)
                time.sleep(retry_sleep)
                continue
            except Exception:
                logger.exception(
                    "Runner cycle failed | cycle=%s symbols=%s",
                    cycle,
                    ",".join(settings.runner_symbols),
                )
                _shutdown_mt5(mt5)
                mt5 = None
                retry_sleep = min(interval_seconds, 10)
                logger.info("Runner heartbeat | cycle=%s status=retrying next_run_in=%ss", cycle, retry_sleep)
                time.sleep(retry_sleep)
                continue
    except KeyboardInterrupt:
        logger.info("MT5 runner stopped by operator.")
    finally:
        _shutdown_mt5(mt5)
