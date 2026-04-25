from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import rate_limit
from app.core.symbols import DEFAULT_SYMBOL, normalize_symbol
from app.db.session import get_db
from app.schemas.v2 import (
    BestDirectionNowOut,
    DashboardScalpSignalOut,
    V2DashboardSummaryResponse,
    V2DashboardSymbolSummaryOut,
    V2IntelligenceResponse,
)
from app.services.best_signal_service import is_tradeable_signal
from app.services.market_state_service import get_v2_intelligence
from app.services.news_context import compute_news_context
from app.services.signal_service import get_latest_signal
from app.services.v2_intelligence import empty_v2_intelligence

router = APIRouter(prefix="/v2", tags=["v2"])


def _resolve_intelligence(db: Session, symbol: str) -> V2IntelligenceResponse:
    intelligence = get_v2_intelligence(db, symbol)
    if intelligence is not None:
        return intelligence

    return empty_v2_intelligence(symbol).model_copy(
        update={"news_context": compute_news_context(symbol)}
    )


def _to_scalp_signal(db: Session, symbol: str) -> DashboardScalpSignalOut | None:
    latest = get_latest_signal(db, symbol).item
    if latest is None:
        return None

    return DashboardScalpSignalOut(
        action=latest.intent.action,
        bias=latest.resolved_bias,
        confidence=latest.confidence,
        target=latest.dashboard_target or latest.intent.target,
        liquidity_target=latest.liquidity_target,
        dashboard_target=latest.dashboard_target,
        ea_tp=latest.ea_tp,
        target_type=latest.target_type,
        nearest_magnet=latest.nearest_magnet,
        major_magnet=latest.major_magnet,
        lifecycle=latest.lifecycle.state,
        tradeable=is_tradeable_signal(latest),
        created_at=latest.created_at,
    )


@router.get("/intelligence", response_model=V2IntelligenceResponse)
def v2_intelligence(
    symbol: str = DEFAULT_SYMBOL,
    _: None = Depends(rate_limit("v2_intelligence", limit=60, window_seconds=60)),
    db: Session = Depends(get_db),
) -> V2IntelligenceResponse:
    return _resolve_intelligence(db, normalize_symbol(symbol))


@router.get("/dashboard-summary", response_model=V2DashboardSummaryResponse)
def v2_dashboard_summary(
    _: None = Depends(rate_limit("v2_dashboard_summary", limit=60, window_seconds=60)),
    db: Session = Depends(get_db),
) -> V2DashboardSummaryResponse:
    settings = get_settings()
    symbols: list[V2DashboardSymbolSummaryOut] = []
    updated_at_candidates: list[datetime] = []

    for symbol in settings.runner_symbols:
        intelligence = _resolve_intelligence(db, symbol)
        updated_at_candidates.append(intelligence.updated_at)
        strongest_h1 = intelligence.liquidity_magnets.h1_magnets[0] if intelligence.liquidity_magnets.h1_magnets else None
        strongest_h4 = intelligence.liquidity_magnets.h4_magnets[0] if intelligence.liquidity_magnets.h4_magnets else None
        symbols.append(
            V2DashboardSymbolSummaryOut(
                symbol=symbol,
                current_price=intelligence.current_price,
                anchor_bias=intelligence.anchor_0801.bias,
                strongest_h1_magnet=strongest_h1,
                strongest_h4_magnet=strongest_h4,
                strongest_magnet=intelligence.liquidity_magnets.strongest_magnet,
                zone_to_zone=intelligence.zone_to_zone,
                volatility_state=intelligence.volatility.state,
                highest_probability_direction=intelligence.highest_probability_direction,
                news_context=intelligence.news_context,
                scalp_signal=_to_scalp_signal(db, symbol),
            )
        )

    if symbols:
        strongest = max(
            symbols,
            key=lambda item: (
                1 if item.highest_probability_direction.direction != "wait" else 0,
                item.highest_probability_direction.confidence,
                1 if item.scalp_signal and item.scalp_signal.tradeable else 0,
                item.current_price,
            ),
        )
        best_direction_now = BestDirectionNowOut(
            symbol=strongest.symbol,
            current_price=strongest.current_price,
            confidence=strongest.highest_probability_direction.confidence,
            direction=strongest.highest_probability_direction.direction,
            anchor_bias=strongest.anchor_bias,
            trade_policy=strongest.news_context.trade_policy,
        )
    else:
        best_direction_now = None

    updated_at = max(updated_at_candidates) if updated_at_candidates else datetime.utcnow()
    return V2DashboardSummaryResponse(
        updated_at=updated_at,
        best_direction_now=best_direction_now,
        symbols=symbols,
    )
