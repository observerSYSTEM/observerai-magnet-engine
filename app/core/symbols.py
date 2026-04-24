from __future__ import annotations

from collections.abc import Iterable

DEFAULT_SYMBOL = "XAUUSD"
SUPPORTED_SYMBOLS = (DEFAULT_SYMBOL, "GBPJPY", "BTCUSD")


def normalize_symbol(symbol: str) -> str:
    return symbol.upper().strip()


def is_supported_symbol(symbol: str) -> bool:
    return normalize_symbol(symbol) in SUPPORTED_SYMBOLS


def parse_symbol_list(
    raw_symbols: str | None,
    *,
    fallback: Iterable[str] = SUPPORTED_SYMBOLS,
) -> list[str]:
    source = raw_symbols.split(",") if raw_symbols and raw_symbols.strip() else list(fallback)
    parsed: list[str] = []
    seen: set[str] = set()

    for symbol in source:
        normalized = normalize_symbol(symbol)
        if not normalized or normalized in seen:
            continue
        parsed.append(normalized)
        seen.add(normalized)

    return parsed
