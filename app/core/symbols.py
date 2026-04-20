SUPPORTED_SYMBOLS = {'XAUUSD'}


def normalize_symbol(symbol: str) -> str:
    return symbol.upper().strip()


def is_supported_symbol(symbol: str) -> bool:
    return normalize_symbol(symbol) in SUPPORTED_SYMBOLS
