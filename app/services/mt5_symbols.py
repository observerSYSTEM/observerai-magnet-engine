from __future__ import annotations

from typing import Any

from app.core.symbols import normalize_symbol


def get_mt5_module() -> Any:
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise RuntimeError(
            "MetaTrader5 package is required for MT5-backed features. Install it from requirements-runner-py313.txt."
        ) from exc
    return mt5


def _collapsed_symbol(name: str) -> str:
    return "".join(ch for ch in name.upper() if ch.isalnum())


def resolve_broker_symbol(mt5: Any, requested_symbol: str) -> str:
    """
    Resolve broker-specific MT5 symbols such as XAUUSDm or XAUUSD.pro.

    The requested symbol remains the canonical ObserverAI symbol while the
    returned broker symbol is used for MT5 market-data access.
    """

    normalized = normalize_symbol(requested_symbol)
    symbol_info = mt5.symbol_info(normalized)
    if symbol_info is not None:
        broker_symbol = str(symbol_info.name)
        if not symbol_info.visible and not mt5.symbol_select(broker_symbol, True):
            raise RuntimeError(
                f"MT5 symbol is unavailable in Market Watch: {broker_symbol}. The runner could not select it for live use."
            )
        return broker_symbol

    candidates = mt5.symbols_get()
    if not candidates:
        raise RuntimeError(
            f"MT5 symbol is unavailable: {normalized}. Verify the broker offers this symbol name and check for any suffix in Market Watch."
        )

    normalized_collapsed = _collapsed_symbol(normalized)
    ranked: list[tuple[int, int, int, str]] = []

    for item in candidates:
        name = str(getattr(item, "name", "") or "")
        if not name:
            continue
        upper_name = name.upper()
        collapsed_name = _collapsed_symbol(name)
        if upper_name != normalized and not upper_name.startswith(normalized) and not collapsed_name.startswith(normalized_collapsed):
            continue

        exact_score = 2 if upper_name == normalized else 1
        visible_score = 1 if getattr(item, "visible", False) else 0
        length_score = -len(name)
        ranked.append((exact_score, visible_score, length_score, name))

    if not ranked:
        raise RuntimeError(
            f"MT5 symbol is unavailable: {normalized}. Verify the broker offers this symbol name and check for any suffix in Market Watch."
        )

    ranked.sort(reverse=True)
    broker_symbol = ranked[0][3]
    if not mt5.symbol_select(broker_symbol, True):
        raise RuntimeError(
            f"MT5 symbol is unavailable in Market Watch: {broker_symbol}. The runner could not select it for live use."
        )
    return broker_symbol
