from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.market_state import MarketState
from app.schemas.liquidity import LiquidityMagnetOut, LiquidityMagnetsResponse
from app.schemas.v2 import HtfContextOut, V2IntelligenceResponse
from app.services.liquidity_engine import Candle, LiquiditySnapshot, compute_liquidity_snapshot


def _json_dump(value) -> str | None:
    if value is None:
        return None
    return json.dumps(value)


def _json_load(value: str | None):
    if not value:
        return None
    return json.loads(value)


def _snapshot_to_payload(snapshot: LiquiditySnapshot) -> list[dict]:
    payload: list[dict] = []
    for index, magnet in enumerate(snapshot.strong_magnets, start=1):
        item = asdict(magnet)
        item["rank"] = index
        payload.append(item)
    return payload


def _strongest_liquidity(
    h1_snapshot: LiquiditySnapshot | None,
    h4_snapshot: LiquiditySnapshot | None,
) -> dict | None:
    candidates = []
    for snapshot in (h1_snapshot, h4_snapshot):
        if snapshot is None:
            continue
        for index, magnet in enumerate(snapshot.strong_magnets, start=1):
            candidates.append(
                {
                    "timeframe": snapshot.timeframe,
                    "rank": index,
                    "type": magnet.type,
                    "label": magnet.label,
                    "price": magnet.price,
                    "side": magnet.side,
                    "distance": magnet.distance,
                    "strength": magnet.strength,
                    "reason": magnet.reason,
                    "rank_score": magnet.rank_score,
                }
            )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (item["rank_score"], item["strength"], -item["distance"]),
        reverse=True,
    )
    strongest = candidates[0]
    strongest.pop("rank_score", None)
    return strongest


def _resolve_htf_bias(
    h1_snapshot: LiquiditySnapshot | None,
    h4_snapshot: LiquiditySnapshot | None,
) -> str:
    biases = [snapshot.htf_magnet_bias for snapshot in (h1_snapshot, h4_snapshot) if snapshot is not None]
    if "bullish" in biases and "bearish" not in biases:
        return "bullish"
    if "bearish" in biases and "bullish" not in biases:
        return "bearish"
    return "neutral"


def upsert_market_state(
    db: Session,
    *,
    symbol: str,
    timestamp: datetime,
    current_price: float,
    pdh: float,
    pdl: float,
    eq: float,
    day_open: float,
    adr: float,
    adr_high: float,
    adr_low: float,
    adr_used_pct: float,
    anchor_direction: str,
    anchor_type: str,
    premium_low: float,
    premium_high: float,
    discount_low: float,
    discount_high: float,
    value_low: float,
    value_high: float,
    current_zone: str,
    bias: str,
    h1_candles: list[Candle] | None = None,
    h4_candles: list[Candle] | None = None,
    v2_snapshot: dict | None = None,
) -> MarketState:
    h1_snapshot = (
        compute_liquidity_snapshot(
            symbol=symbol,
            timeframe="H1",
            current_price=current_price,
            candles=h1_candles,
            pdh=pdh,
            pdl=pdl,
        )
        if h1_candles
        else None
    )
    h4_snapshot = (
        compute_liquidity_snapshot(
            symbol=symbol,
            timeframe="H4",
            current_price=current_price,
            candles=h4_candles,
            pdh=pdh,
            pdl=pdl,
        )
        if h4_candles
        else None
    )

    row = db.scalar(select(MarketState).where(MarketState.symbol == symbol))
    if row is None:
        row = MarketState(symbol=symbol, timestamp=timestamp, pdh=pdh, pdl=pdl, eq=eq, day_open=day_open, adr=adr, adr_high=adr_high, adr_low=adr_low, adr_used_pct=adr_used_pct)
        db.add(row)

    row.timestamp = timestamp
    row.current_price = current_price
    row.pdh = pdh
    row.pdl = pdl
    row.eq = eq
    row.day_open = day_open
    row.adr = adr
    row.adr_high = adr_high
    row.adr_low = adr_low
    row.adr_used_pct = adr_used_pct
    row.anchor_direction = anchor_direction
    row.anchor_type = anchor_type
    row.premium_low = premium_low
    row.premium_high = premium_high
    row.discount_low = discount_low
    row.discount_high = discount_high
    row.value_low = value_low
    row.value_high = value_high
    row.current_zone = current_zone
    row.bias = bias
    row.h1_liquidity = _json_dump(_snapshot_to_payload(h1_snapshot) if h1_snapshot else None)
    row.h4_liquidity = _json_dump(_snapshot_to_payload(h4_snapshot) if h4_snapshot else None)
    row.strongest_liquidity = _json_dump(_strongest_liquidity(h1_snapshot, h4_snapshot))
    row.htf_magnet_bias = _resolve_htf_bias(h1_snapshot, h4_snapshot)
    row.v2_snapshot = _json_dump(v2_snapshot)

    db.commit()
    db.refresh(row)
    return row


def get_market_state_row(db: Session, symbol: str) -> MarketState | None:
    return db.scalar(select(MarketState).where(MarketState.symbol == symbol))


def get_v2_intelligence(db: Session, symbol: str) -> V2IntelligenceResponse | None:
    row = get_market_state_row(db, symbol)
    if row is None or not row.v2_snapshot:
        return None

    snapshot = _json_load(row.v2_snapshot)
    if not snapshot:
        return None

    return V2IntelligenceResponse.model_validate(snapshot)


def get_htf_context(db: Session, symbol: str, action: str | None) -> HtfContextOut | None:
    row = get_market_state_row(db, symbol)
    if row is None:
        return None

    strongest = _json_load(row.strongest_liquidity)
    strongest_price = None
    if strongest and isinstance(strongest, dict):
        strongest_price = strongest.get("price")

    normalized_action = (action or "").upper()
    if normalized_action == "BUY":
        alignment = "aligned" if row.htf_magnet_bias == "bullish" else "against" if row.htf_magnet_bias == "bearish" else "mixed"
    elif normalized_action == "SELL":
        alignment = "aligned" if row.htf_magnet_bias == "bearish" else "against" if row.htf_magnet_bias == "bullish" else "mixed"
    else:
        alignment = "mixed"

    return HtfContextOut(
        bias=row.htf_magnet_bias or "neutral",
        strongest_magnet=strongest_price,
        alignment=alignment,
    )


def get_liquidity_magnets(
    db: Session,
    *,
    symbol: str,
    timeframe: str,
) -> LiquidityMagnetsResponse:
    normalized_timeframe = timeframe.upper()
    row = db.scalar(select(MarketState).where(MarketState.symbol == symbol))
    if row is None:
        return LiquidityMagnetsResponse(
            symbol=symbol,
            timeframe=normalized_timeframe,  # type: ignore[arg-type]
            current_price=0.0,
            strong_magnets=[],
            htf_magnet_bias="neutral",
        )

    payload = _json_load(row.h1_liquidity if normalized_timeframe == "H1" else row.h4_liquidity) or []
    magnets = [
        LiquidityMagnetOut(
            rank=item["rank"],
            type=item["type"],
            label=item["label"],
            price=item["price"],
            side=item["side"],
            distance=item["distance"],
            strength=item["strength"],
            reason=item["reason"],
        )
        for item in payload
    ]
    return LiquidityMagnetsResponse(
        symbol=row.symbol,
        timeframe=normalized_timeframe,  # type: ignore[arg-type]
        current_price=round(row.current_price or 0.0, 5),
        strong_magnets=magnets,
        htf_magnet_bias=row.htf_magnet_bias or "neutral",
    )
