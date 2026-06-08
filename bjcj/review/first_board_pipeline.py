from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from bjcj.review.candidate_scan import CandidateScanResult
from bjcj.review.core import FirstBoardReview, ReviewItem, StockMeta, generate_first_board_review


@dataclass(frozen=True)
class PreviousLimitDays:
    days: dict[str, int]
    history_available: bool


def load_previous_limit_days(
    path: str | Path,
    symbols: list[str],
    *,
    trade_date: str | None = None,
) -> PreviousLimitDays:
    source = Path(path)
    if not source.exists():
        return PreviousLimitDays(days={symbol: 0 for symbol in symbols}, history_available=False)

    raw = json.loads(source.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and trade_date is not None and raw.get("trade_date") == trade_date:
        return PreviousLimitDays(days={symbol: 0 for symbol in symbols}, history_available=False)
    if isinstance(raw, dict) and "limit_days" in raw:
        raw = raw["limit_days"]
    days = {symbol: int(raw.get(symbol, 0)) for symbol in symbols}
    return PreviousLimitDays(days=days, history_available=True)


def build_first_board_review(
    *,
    trade_date: str,
    stocks: list[StockMeta],
    scan: CandidateScanResult,
    previous_limit_days: dict[str, int],
) -> FirstBoardReview:
    candidate_symbols = {candidate.symbol for candidate in scan.candidates}
    touched_symbols = set(scan.intraday)
    relevant_symbols = candidate_symbols | touched_symbols
    relevant_stocks = [stock for stock in stocks if stock.symbol in relevant_symbols]

    return generate_first_board_review(
        trade_date=trade_date,
        stocks=relevant_stocks,
        quotes=scan.quotes,
        intraday=scan.intraday,
        previous_limit_days=previous_limit_days,
    )


def first_board_review_to_jsonable(
    review: FirstBoardReview,
    *,
    history_available: bool,
) -> dict[str, object]:
    return {
        "trade_date": review.trade_date,
        "history_available": history_available,
        "stats": {
            "first_board_count": review.stats.first_board_count,
            "touched_first_board_count": review.stats.touched_first_board_count,
            "broken_count": review.stats.broken_count,
            "resealed_count": review.stats.resealed_count,
            "broken_rate": str(review.stats.broken_rate),
        },
        "first_boards": [_review_item_to_jsonable(item) for item in review.first_boards],
        "touched_first_boards": [_review_item_to_jsonable(item) for item in review.touched_first_boards],
        "broken_boards": [_review_item_to_jsonable(item) for item in review.broken_boards],
        "watch_pool": [_review_item_to_jsonable(item) for item in review.watch_pool],
    }


def build_next_limit_days(
    scan: CandidateScanResult,
    *,
    previous_limit_days: dict[str, int],
) -> dict[str, int]:
    next_days: dict[str, int] = {}
    for candidate in scan.candidates:
        if candidate.limit_up > 0 and candidate.close >= candidate.limit_up:
            next_days[candidate.symbol] = previous_limit_days.get(candidate.symbol, 0) + 1
    return next_days


def limit_days_to_jsonable(trade_date: str, limit_days: dict[str, int]) -> dict[str, object]:
    ordered = {symbol: limit_days[symbol] for symbol in sorted(limit_days)}
    return {
        "trade_date": trade_date,
        "count": len(ordered),
        "limit_days": ordered,
    }


def _review_item_to_jsonable(item: ReviewItem) -> dict[str, object]:
    return {
        "symbol": item.symbol,
        "name": item.name,
        "industry": item.industry,
        "close": str(item.close),
        "pct_chg": str(item.pct_chg),
        "turnover_amount": item.turnover_amount,
        "turnover_rate": str(item.turnover_rate),
        "limit_up_price": str(item.limit_up_price),
        "first_limit_time": item.first_limit_time,
        "last_limit_time": item.last_limit_time,
        "open_limit_count": item.open_limit_count,
        "is_limit_up_close": item.is_limit_up_close,
        "limit_up_days": item.limit_up_days,
        "strength_score": str(item.strength_score),
        "next_day_watch": item.next_day_watch,
        "watch_reason": item.watch_reason,
        "risk_tags": item.risk_tags,
    }
