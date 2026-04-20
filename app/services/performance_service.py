from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal, Protocol, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.signal import Signal
from app.models.signal_outcome import SignalOutcome
from app.schemas.oracle import OracleEvaluateResponse
from app.schemas.performance import (
    PerformanceSignalsResponse,
    PerformanceSummaryResponse,
    StoredSignalOutcomeOut,
)

OutcomeAction = Literal["BUY", "SELL", "WAIT"]
ACTIONABLE_ACTIONS = {"BUY", "SELL"}
SIGNAL_EXPIRY_HOURS = 24
RECENT_SWING_LOOKBACK = 4


class CandleLike(Protocol):
    high: float
    low: float


@dataclass(frozen=True)
class SignalOutcomeSeed:
    """Stored outcome seed derived from a freshly evaluated signal."""

    action: OutcomeAction
    entry_price: float
    target: float | None
    stop_hint: str | None
    stop_price: float | None


def _round_price(value: float) -> float:
    return round(value, 5)


def _recent_extremes(m15_candles: Sequence[CandleLike]) -> tuple[float | None, float | None]:
    if not m15_candles:
        return None, None

    recent = list(m15_candles[-RECENT_SWING_LOOKBACK:])
    recent_low = min(candle.low for candle in recent)
    recent_high = max(candle.high for candle in recent)
    return _round_price(recent_low), _round_price(recent_high)


def _resolve_stop_price(
    *,
    action: OutcomeAction,
    stop_hint: str | None,
    anchor_value_low: float,
    anchor_value_high: float,
    recent_low: float | None,
    recent_high: float | None,
) -> float | None:
    if action == "BUY" and stop_hint == "below_value_low":
        return _round_price(anchor_value_low)
    if action == "SELL" and stop_hint == "above_value_high":
        return _round_price(anchor_value_high)
    if action == "BUY" and stop_hint == "below_recent_low" and recent_low is not None:
        return recent_low
    if action == "SELL" and stop_hint == "above_recent_high" and recent_high is not None:
        return recent_high
    return None


def build_signal_outcome_seed(
    *,
    response: OracleEvaluateResponse,
    anchor_value_low: float,
    anchor_value_high: float,
    m15_candles: Sequence[CandleLike],
) -> SignalOutcomeSeed | None:
    """
    Build a persisted outcome seed for actionable signals.

    The runner tracks BUY and SELL intents only. WAIT outputs remain stored as
    signals, but they do not create open performance rows because there is no
    trade to evaluate against future prices.
    """

    action = response.intent.action
    if action not in ACTIONABLE_ACTIONS:
        return None

    recent_low, recent_high = _recent_extremes(m15_candles)
    stop_price = _resolve_stop_price(
        action=action,
        stop_hint=response.intent.stop_hint,
        anchor_value_low=anchor_value_low,
        anchor_value_high=anchor_value_high,
        recent_low=recent_low,
        recent_high=recent_high,
    )

    return SignalOutcomeSeed(
        action=action,
        entry_price=_round_price(response.current_price),
        target=_round_price(response.intent.target) if response.intent.target is not None else None,
        stop_hint=response.intent.stop_hint,
        stop_price=stop_price,
    )


def create_signal_outcome(
    db: Session,
    signal: Signal,
    seed: SignalOutcomeSeed | None,
) -> SignalOutcome | None:
    """Persist a new outcome row for an actionable signal."""

    if seed is None:
        return None

    row = SignalOutcome(
        signal_id=signal.id,
        symbol=signal.symbol,
        action=seed.action,
        entry_price=seed.entry_price,
        target=seed.target,
        stop_hint=seed.stop_hint,
        stop_price=seed.stop_price,
        outcome_status="open",
        mfe=0.0,
        mae=0.0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _compute_excursions(action: str, entry_price: float, current_price: float) -> tuple[float, float]:
    if action == "BUY":
        favorable = max(0.0, current_price - entry_price)
        adverse = max(0.0, entry_price - current_price)
    else:
        favorable = max(0.0, entry_price - current_price)
        adverse = max(0.0, current_price - entry_price)

    return _round_price(favorable), _round_price(adverse)


def _is_target_hit(outcome: SignalOutcome, current_price: float) -> bool:
    if outcome.target is None:
        return False
    if outcome.action == "BUY":
        return current_price >= outcome.target
    return current_price <= outcome.target


def _is_invalidated(outcome: SignalOutcome, current_price: float) -> bool:
    if outcome.stop_price is None:
        return False
    if outcome.action == "BUY":
        return current_price <= outcome.stop_price
    return current_price >= outcome.stop_price


def evaluate_open_signal_outcomes(
    db: Session,
    *,
    symbol: str,
    current_price: float,
    observed_at: datetime | None = None,
) -> list[SignalOutcome]:
    """
    Update open signal outcomes using the latest observed market price.

    Target hits and invalidations close immediately. Remaining open signals
    expire after 24 hours if neither outcome condition has been reached.
    """

    observed_time = observed_at or datetime.utcnow()
    stmt = (
        select(SignalOutcome, Signal.created_at)
        .join(Signal, Signal.id == SignalOutcome.signal_id)
        .where(
            SignalOutcome.symbol == symbol,
            SignalOutcome.outcome_status == "open",
        )
        .order_by(Signal.created_at.asc())
    )
    rows = list(db.execute(stmt))

    for outcome, signal_created_at in rows:
        favorable, adverse = _compute_excursions(
            action=outcome.action,
            entry_price=outcome.entry_price,
            current_price=current_price,
        )
        outcome.mfe = _round_price(max(outcome.mfe, favorable))
        outcome.mae = _round_price(max(outcome.mae, adverse))

        if _is_target_hit(outcome, current_price):
            outcome.outcome_status = "target_hit"
            outcome.closed_at = observed_time
            continue

        if _is_invalidated(outcome, current_price):
            outcome.outcome_status = "invalidated"
            outcome.closed_at = observed_time
            continue

        if observed_time >= signal_created_at + timedelta(hours=SIGNAL_EXPIRY_HOURS):
            outcome.outcome_status = "expired"
            outcome.closed_at = observed_time

    if rows:
        db.commit()

    return [outcome for outcome, _ in rows]


def signal_outcome_to_schema(outcome: SignalOutcome) -> StoredSignalOutcomeOut:
    return StoredSignalOutcomeOut(
        signal_id=outcome.signal_id,
        symbol=outcome.symbol,
        action=outcome.action,
        entry_price=outcome.entry_price,
        target=outcome.target,
        stop_hint=outcome.stop_hint,
        outcome_status=outcome.outcome_status,
        mfe=_round_price(outcome.mfe),
        mae=_round_price(outcome.mae),
        closed_at=outcome.closed_at,
    )


def list_performance_signals(
    db: Session,
    *,
    symbol: str,
    limit: int = 50,
) -> PerformanceSignalsResponse:
    """Return stored signal outcomes ordered from newest signal to oldest."""

    stmt = (
        select(SignalOutcome)
        .join(Signal, Signal.id == SignalOutcome.signal_id)
        .where(SignalOutcome.symbol == symbol)
        .order_by(Signal.created_at.desc())
        .limit(limit)
    )
    rows = list(db.scalars(stmt))
    items = [signal_outcome_to_schema(row) for row in rows]
    return PerformanceSignalsResponse(symbol=symbol, count=len(items), items=items)


def get_performance_summary(db: Session, *, symbol: str) -> PerformanceSummaryResponse:
    """Aggregate performance statistics for stored signal outcomes."""

    stmt = select(SignalOutcome).where(SignalOutcome.symbol == symbol)
    rows = list(db.scalars(stmt))

    total = len(rows)
    open_signals = sum(1 for row in rows if row.outcome_status == "open")
    target_hit = sum(1 for row in rows if row.outcome_status == "target_hit")
    invalidated = sum(1 for row in rows if row.outcome_status == "invalidated")
    expired = sum(1 for row in rows if row.outcome_status == "expired")
    closed_signals = target_hit + invalidated + expired
    win_rate_pct = round((target_hit / closed_signals) * 100, 2) if closed_signals else 0.0
    avg_mfe = round(sum(row.mfe for row in rows) / total, 5) if total else 0.0
    avg_mae = round(sum(row.mae for row in rows) / total, 5) if total else 0.0

    return PerformanceSummaryResponse(
        symbol=symbol,
        total_signals=total,
        open_signals=open_signals,
        closed_signals=closed_signals,
        target_hit=target_hit,
        invalidated=invalidated,
        expired=expired,
        win_rate_pct=win_rate_pct,
        avg_mfe=avg_mfe,
        avg_mae=avg_mae,
    )
