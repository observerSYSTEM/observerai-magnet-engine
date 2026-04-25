from __future__ import annotations

from app.core.config import get_settings
from app.core.symbols import normalize_symbol
from app.schemas.v2 import NewsContextOut


SYMBOL_NEWS_CURRENCIES = {
    "XAUUSD": "USD",
    "GBPJPY": "GBP/JPY",
    "BTCUSD": "USD",
}


def _manual_news_context(symbol: str) -> NewsContextOut:
    return NewsContextOut(
        has_high_impact_news=False,
        event=None,
        currency=SYMBOL_NEWS_CURRENCIES.get(symbol),
        time=None,
        impact="none",
        expected_direction="neutral",
        trade_policy="normal",
    )


def compute_news_context(symbol: str) -> NewsContextOut:
    """
    Return news-aware trade context without making external APIs mandatory.

    MT5 remains the primary data path for FX, metals, crypto, and indices.
    News is an optional risk filter, so missing provider credentials resolve to
    a safe neutral state instead of a hard failure.
    """

    settings = get_settings()
    normalized_symbol = normalize_symbol(symbol)
    provider = settings.news_api_provider.strip().lower()

    if provider in {"", "manual"}:
        return _manual_news_context(normalized_symbol)

    if provider == "finnhub" and not settings.finnhub_api_key:
        return _manual_news_context(normalized_symbol)

    if provider == "alphavantage" and not settings.alphavantage_api_key:
        return _manual_news_context(normalized_symbol)

    return _manual_news_context(normalized_symbol)
