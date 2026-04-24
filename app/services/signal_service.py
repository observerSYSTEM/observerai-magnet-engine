from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.symbols import normalize_symbol
from app.models.signal import Signal
from app.schemas.oracle import OracleEvaluateResponse
from app.schemas.signal import LatestSignalResponse, SignalsLatestResponse, StoredSignalOut
from app.services.lifecycle_service import derive_signal_lifecycle

logger = logging.getLogger(__name__)


def _json_dump(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value)


def _json_load(value: str | None) -> Any:
    if not value:
        return None
    return json.loads(value)


def _resolve_direction(resolved_bias: str, action: str) -> str:
    if resolved_bias.startswith("bullish") or action == "BUY":
        return "bullish"
    if resolved_bias.startswith("bearish") or action == "SELL":
        return "bearish"
    return "neutral"


def signal_row_to_stored_signal(row: Signal) -> StoredSignalOut:
    intent = _json_load(row.intent) or {
        "action": "WAIT",
        "entry_type": "none",
        "reason": "",
        "target": None,
        "stop_hint": None,
    }
    outcome = row.outcome

    return StoredSignalOut(
        symbol=row.symbol,
        current_price=row.current_price or row.close_price,
        bias=row.bias or "",
        resolved_bias=row.resolved_bias or "",
        event_type=row.event_type,
        anchor_direction=row.anchor_direction or "",
        anchor_type=row.anchor_type or "",
        adr=row.adr or 0.0,
        adr_used_pct=row.adr_used_pct or 0.0,
        adr_state=row.adr_state or "",
        nearest_magnet=_json_load(row.nearest_magnet),
        major_magnet=_json_load(row.major_magnet),
        magnet_path=_json_load(row.magnet_path) or [],
        sweep=_json_load(row.sweep),
        structure=_json_load(row.structure),
        momentum=_json_load(row.momentum),
        mid_targets=_json_load(row.mid_targets),
        intent=intent,
        lifecycle=derive_signal_lifecycle(
            action=intent.get("action"),
            outcome_status=outcome.outcome_status if outcome is not None else None,
            closed_at=outcome.closed_at if outcome is not None else None,
        ),
        confidence=row.confidence,
        message=row.message,
        created_at=row.created_at,
    )


def get_previous_signal_candidate(db: Session, current_signal: Signal) -> StoredSignalOut | None:
    """
    Fetch the most recent prior stored signal with the same alert family.

    The final dedupe decision still compares the full alert key including target.
    """

    stmt = (
        select(Signal)
        .options(selectinload(Signal.outcome))
        .where(
            Signal.symbol == current_signal.symbol,
            Signal.resolved_bias == current_signal.resolved_bias,
            Signal.event_type == current_signal.event_type,
            Signal.id != current_signal.id,
        )
        .order_by(Signal.created_at.desc())
        .limit(1)
    )
    row = db.scalar(stmt)
    return signal_row_to_stored_signal(row) if row is not None else None


def save_evaluated_signal(db: Session, payload: OracleEvaluateResponse) -> Signal:
    """Persist an oracle evaluation using the existing signal table."""

    symbol = normalize_symbol(payload.symbol)
    nearest = payload.nearest_magnet.model_dump() if payload.nearest_magnet else None
    major = payload.major_magnet.model_dump() if payload.major_magnet else None
    magnet_path = [magnet.model_dump() for magnet in payload.magnet_path]
    sweep = payload.sweep.model_dump() if payload.sweep else None
    structure = payload.structure.model_dump() if payload.structure else None
    momentum = payload.momentum.model_dump() if payload.momentum else None
    mid_targets = payload.mid_targets.model_dump() if payload.mid_targets else None
    intent = payload.intent.model_dump()
    direction = _resolve_direction(payload.resolved_bias, payload.intent.action)

    row = Signal(
        symbol=symbol,
        timeframe="M15",
        event_type=payload.event_type,
        direction=direction,
        trigger_level_name=payload.event_type,
        trigger_level_price=payload.current_price,
        close_price=payload.current_price,
        nearest_magnet_name=payload.nearest_magnet.name if payload.nearest_magnet else "",
        nearest_magnet_price=payload.nearest_magnet.price if payload.nearest_magnet else 0.0,
        major_magnet_name=payload.major_magnet.name if payload.major_magnet else "",
        major_magnet_price=payload.major_magnet.price if payload.major_magnet else 0.0,
        current_price=payload.current_price,
        bias=payload.bias,
        resolved_bias=payload.resolved_bias,
        anchor_direction=payload.anchor_direction,
        anchor_type=payload.anchor_type,
        adr=payload.adr,
        adr_used_pct=payload.adr_used_pct,
        adr_state=payload.adr_state,
        nearest_magnet=_json_dump(nearest),
        major_magnet=_json_dump(major),
        magnet_path=_json_dump(magnet_path),
        sweep=_json_dump(sweep),
        structure=_json_dump(structure),
        momentum=_json_dump(momentum),
        mid_targets=_json_dump(mid_targets),
        intent=_json_dump(intent),
        confidence=payload.confidence,
        message=payload.message,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    logger.info(
        "Signal stored | symbol=%s action=%s resolved_bias=%s event=%s confidence=%s",
        row.symbol,
        payload.intent.action,
        payload.resolved_bias,
        payload.event_type,
        payload.confidence,
    )
    return row


def list_latest_signals(db: Session, symbol: str, limit: int = 20) -> SignalsLatestResponse:
    """Return stored oracle evaluations ordered from newest to oldest."""

    normalized_symbol = normalize_symbol(symbol)
    stmt = (
        select(Signal)
        .options(selectinload(Signal.outcome))
        .where(Signal.symbol == normalized_symbol)
        .order_by(Signal.created_at.desc())
        .limit(limit)
    )
    rows = list(db.scalars(stmt))

    items = [signal_row_to_stored_signal(row) for row in rows]

    return SignalsLatestResponse(symbol=normalized_symbol, count=len(items), items=items)


def get_latest_signal(db: Session, symbol: str) -> LatestSignalResponse:
    """Return the newest stored signal for the requested symbol."""

    latest = list_latest_signals(db, symbol, limit=1)
    item = latest.items[0] if latest.items else None
    return LatestSignalResponse(symbol=latest.symbol, item=item)
