from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Protocol


BiasName = Literal[
    "bullish_continuation",
    "bearish_continuation",
    "bullish_reversal",
    "bearish_reversal",
    "neutral_outside_value",
    "neutral_wait",
]


@dataclass(frozen=True)
class TradeIntent:
    """Normalized trade intent derived from resolved bias and target magnets."""

    action: Literal["BUY", "SELL", "WAIT"]
    entry_type: Literal["continuation", "reversal", "none"]
    reason: str
    target: Optional[float]
    stop_hint: Optional[str]


class MagnetLike(Protocol):
    """Structural type for magnet objects used by the intent layer."""

    name: str
    price: float
    direction: str


class SweepLike(Protocol):
    type: str
    strength: float


class StructureLike(Protocol):
    type: str
    direction: str


class MomentumLike(Protocol):
    direction: str
    classification: str


class MidPointLike(Protocol):
    name: str
    price: float


class MidTargetsLike(Protocol):
    current_mid: Optional[MidPointLike]
    next_mid: Optional[MidPointLike]
    flow: str


def _event_direction(event_type: str) -> Optional[str]:
    if "above" in event_type:
        return "bullish"
    if "below" in event_type:
        return "bearish"
    return None


def _dominant_magnet(
    major_magnet: Optional[MagnetLike],
    nearest_magnet: Optional[MagnetLike],
) -> Optional[MagnetLike]:
    return major_magnet or nearest_magnet


def _supports_reversal(
    expected_direction: str,
    structure: Optional[StructureLike],
    sweep: Optional[SweepLike],
    momentum: Optional[MomentumLike],
) -> bool:
    structure_support = (
        structure is not None
        and structure.type == "mss"
        and structure.direction == expected_direction
    )
    sweep_support = (
        sweep is not None
        and (
            (expected_direction == "bullish" and sweep.type == "sellside")
            or (expected_direction == "bearish" and sweep.type == "buyside")
        )
        and sweep.strength >= 1.0
    )
    momentum_support = (
        momentum is not None
        and momentum.direction == expected_direction
        and momentum.classification == "strong"
    )
    return structure_support or sweep_support or momentum_support


def _supports_continuation(
    expected_direction: str,
    structure: Optional[StructureLike],
    momentum: Optional[MomentumLike],
) -> bool:
    structure_support = (
        structure is not None
        and structure.type == "bos"
        and structure.direction == expected_direction
    )
    momentum_support = (
        momentum is not None
        and momentum.direction == expected_direction
        and momentum.classification in {"moderate", "strong"}
    )
    return structure_support or momentum_support


def resolve_bias(
    *,
    anchor_direction: str,
    event_type: str,
    current_price: float,
    value_low: float,
    value_high: float,
    bullish_nearest_magnet: Optional[MagnetLike],
    bullish_major_magnet: Optional[MagnetLike],
    bearish_nearest_magnet: Optional[MagnetLike],
    bearish_major_magnet: Optional[MagnetLike],
    structure: Optional[StructureLike] = None,
    sweep: Optional[SweepLike] = None,
    momentum: Optional[MomentumLike] = None,
) -> BiasName:
    """
    Resolve a stronger directional bias using anchor, event, and magnet alignment.

    The resolution layer upgrades weak anchor-only bias when event direction and the
    dominant target magnet agree on the same side of the market.
    """

    event_direction = _event_direction(event_type)
    bullish_magnet = _dominant_magnet(bullish_major_magnet, bullish_nearest_magnet)
    bearish_magnet = _dominant_magnet(bearish_major_magnet, bearish_nearest_magnet)

    bullish_alignment = bullish_magnet is not None and bullish_magnet.direction == "bullish"
    bearish_alignment = bearish_magnet is not None and bearish_magnet.direction == "bearish"
    bullish_continuation_support = _supports_continuation("bullish", structure, momentum)
    bearish_continuation_support = _supports_continuation("bearish", structure, momentum)
    bullish_reversal_support = _supports_reversal("bullish", structure, sweep, momentum)
    bearish_reversal_support = _supports_reversal("bearish", structure, sweep, momentum)

    if anchor_direction == "bullish" and event_direction == "bullish" and bullish_alignment:
        return "bullish_continuation"

    if anchor_direction == "bearish" and event_direction == "bearish" and bearish_alignment:
        return "bearish_continuation"

    if (
        anchor_direction == "bullish"
        and event_direction == "bearish"
        and bearish_alignment
        and bearish_reversal_support
    ):
        return "bearish_reversal"

    if (
        anchor_direction == "bearish"
        and event_direction == "bullish"
        and bullish_alignment
        and bullish_reversal_support
    ):
        return "bullish_reversal"

    if event_direction is None:
        if anchor_direction == "bullish" and bullish_alignment and bullish_continuation_support:
            return "bullish_continuation"
        if anchor_direction == "bearish" and bearish_alignment and bearish_continuation_support:
            return "bearish_continuation"
        if anchor_direction == "bullish" and bearish_alignment and bearish_reversal_support:
            return "bearish_reversal"
        if anchor_direction == "bearish" and bullish_alignment and bullish_reversal_support:
            return "bullish_reversal"

    if (current_price < value_low or current_price > value_high) and event_direction is None:
        return "neutral_outside_value"

    return "neutral_wait"


def build_trade_intent(
    *,
    resolved_bias: BiasName,
    event_type: str,
    nearest_magnet: Optional[MagnetLike],
    major_magnet: Optional[MagnetLike],
    structure: Optional[StructureLike] = None,
    sweep: Optional[SweepLike] = None,
    momentum: Optional[MomentumLike] = None,
    mid_targets: Optional[MidTargetsLike] = None,
) -> TradeIntent:
    """
    Convert resolved bias into an actionable trade intent.

    The major magnet is preferred as the target because it represents the highest
    ranked liquidity draw. The nearest magnet is used as a fallback.
    """

    target_magnet = major_magnet or nearest_magnet
    if target_magnet is not None:
        target = round(target_magnet.price, 5)
    elif mid_targets is not None and mid_targets.next_mid is not None:
        target = round(mid_targets.next_mid.price, 5)
    else:
        target = None

    reason_suffix = []
    if structure is not None and structure.type != "none":
        reason_suffix.append(f"structure={structure.type}:{structure.direction}")
    if sweep is not None and sweep.type != "none":
        reason_suffix.append(f"sweep={sweep.type}:{sweep.strength:.2f}")
    if momentum is not None:
        reason_suffix.append(f"momentum={momentum.classification}:{momentum.direction}")
    if mid_targets is not None:
        reason_suffix.append(f"mid_flow={mid_targets.flow}")

    detail = ""
    if reason_suffix:
        detail = " " + " | ".join(reason_suffix) + "."

    if resolved_bias == "bullish_continuation":
        return TradeIntent(
            action="BUY",
            entry_type="continuation",
            reason=f"Bullish continuation confirmed by {event_type} with upside magnet alignment.{detail}",
            target=target,
            stop_hint="below_value_low",
        )

    if resolved_bias == "bearish_continuation":
        return TradeIntent(
            action="SELL",
            entry_type="continuation",
            reason=f"Bearish continuation confirmed by {event_type} with downside magnet alignment.{detail}",
            target=target,
            stop_hint="above_value_high",
        )

    if resolved_bias == "bullish_reversal":
        return TradeIntent(
            action="BUY",
            entry_type="reversal",
            reason=f"Bullish reversal detected because {event_type} opposes the anchor and upside magnets dominate.{detail}",
            target=target,
            stop_hint="below_recent_low",
        )

    if resolved_bias == "bearish_reversal":
        return TradeIntent(
            action="SELL",
            entry_type="reversal",
            reason=f"Bearish reversal detected because {event_type} opposes the anchor and downside magnets dominate.{detail}",
            target=target,
            stop_hint="above_recent_high",
        )

    reason = "Price is outside the anchor value area without a strong directional event."
    if resolved_bias == "neutral_wait":
        reason = "Directional agreement is incomplete, so the engine is waiting for cleaner alignment."

    return TradeIntent(
        action="WAIT",
        entry_type="none",
        reason=reason,
        target=target,
        stop_hint=None,
    )
