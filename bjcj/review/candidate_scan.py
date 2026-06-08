from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Callable
from urllib.request import Request, urlopen

from bjcj.review.core import DailyQuote, IntradayBar, StockMeta
from bjcj.review.tencent_finance import (
    TencentRealtimeQuote,
    fetch_minute_bars,
    fetch_realtime_quotes,
    is_active_a_share_quote,
)


@dataclass(frozen=True)
class LimitCandidate:
    symbol: str
    name: str
    close: Decimal
    previous_close: Decimal
    limit_up: Decimal
    turnover_amount: int
    turnover_rate: Decimal
    high: Decimal = Decimal("0")


@dataclass(frozen=True)
class CandidateScanResult:
    candidates: list[LimitCandidate]
    quotes: dict[str, DailyQuote]
    intraday: dict[str, list[IntradayBar]]
    quote_count: int


def load_stock_pool(path: str | Path) -> list[StockMeta]:
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        StockMeta(
            symbol=row["symbol"],
            name=row["name"],
            market=row.get("market", ""),
            is_st=bool(row.get("is_st", False)),
        )
        for row in rows
    ]


def fetch_limit_candidates(
    stocks: list[StockMeta],
    *,
    batch_size: int = 200,
    opener: Callable[[Request, float], object] = urlopen,
    timeout: float = 10,
) -> CandidateScanResult:
    stock_by_symbol = {stock.symbol: stock for stock in stocks}
    all_quotes: dict[str, DailyQuote] = {}
    candidates: list[LimitCandidate] = []
    quote_count = 0

    for batch in _chunks([stock.symbol for stock in stocks], batch_size):
        quotes = fetch_realtime_quotes(batch, opener=opener, timeout=timeout)
        quote_count += len(quotes)

        for quote in quotes:
            stock = stock_by_symbol.get(quote.symbol)
            if stock is None or _is_excluded_stock(stock):
                continue
            if not is_active_a_share_quote(quote):
                continue

            all_quotes[quote.symbol] = _to_daily_quote(quote)
            if _is_limit_candidate(quote):
                candidates.append(_to_limit_candidate(quote))

    candidates.sort(key=lambda item: (item.turnover_amount, item.symbol), reverse=True)
    intraday = {
        candidate.symbol: fetch_minute_bars(candidate.symbol, opener=opener, timeout=timeout)
        for candidate in candidates
    }

    return CandidateScanResult(
        candidates=candidates,
        quotes=all_quotes,
        intraday=intraday,
        quote_count=quote_count,
    )


def limit_candidates_to_jsonable(candidates: list[LimitCandidate]) -> list[dict[str, object]]:
    return [
        {
            "symbol": candidate.symbol,
            "name": candidate.name,
            "close": str(candidate.close),
            "previous_close": str(candidate.previous_close),
            "high": str(candidate.high),
            "limit_up": str(candidate.limit_up),
            "turnover_amount": candidate.turnover_amount,
            "turnover_rate": str(candidate.turnover_rate),
        }
        for candidate in candidates
    ]


def _is_limit_candidate(quote: TencentRealtimeQuote) -> bool:
    return quote.limit_up > 0 and quote.high >= quote.limit_up


def _to_limit_candidate(quote: TencentRealtimeQuote) -> LimitCandidate:
    return LimitCandidate(
        symbol=quote.symbol,
        name=quote.name,
        close=quote.close,
        previous_close=quote.previous_close,
        limit_up=quote.limit_up,
        turnover_amount=quote.turnover_amount,
        turnover_rate=quote.turnover_rate,
        high=quote.high,
    )


def _to_daily_quote(quote: TencentRealtimeQuote) -> DailyQuote:
    return DailyQuote(
        symbol=quote.symbol,
        previous_close=quote.previous_close,
        close=quote.close,
        open=quote.open,
        turnover_amount=quote.turnover_amount,
        turnover_rate=quote.turnover_rate,
    )


def _is_excluded_stock(stock: StockMeta) -> bool:
    return stock.is_st or "退市" in stock.name


def _chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]
