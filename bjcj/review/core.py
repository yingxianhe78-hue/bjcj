from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from math import ceil


MONEY_1Y = 100_000_000


@dataclass(frozen=True)
class StockMeta:
    symbol: str
    name: str
    industry: str = ""
    concepts: tuple[str, ...] = ()
    is_st: bool = False
    is_new_unopened: bool = False
    market: str = ""


@dataclass(frozen=True)
class DailyQuote:
    symbol: str
    previous_close: Decimal
    close: Decimal
    open: Decimal
    turnover_amount: int
    turnover_rate: Decimal


@dataclass(frozen=True)
class IntradayBar:
    time: str
    price: Decimal


@dataclass(frozen=True)
class ReviewConfig:
    min_turnover_amount: int = 300_000_000
    watch_strength_percent: Decimal = Decimal("0.30")
    max_watch_open_limit_count: int = 1


@dataclass(frozen=True)
class BoardState:
    touched: bool
    first_limit_time: str | None
    last_limit_time: str | None
    open_limit_count: int
    is_limit_up_close: bool


@dataclass(frozen=True)
class ReviewItem:
    trade_date: str
    symbol: str
    name: str
    industry: str
    concepts: tuple[str, ...]
    close: Decimal
    pct_chg: Decimal
    turnover_amount: int
    turnover_rate: Decimal
    limit_up_price: Decimal
    first_limit_time: str | None
    last_limit_time: str | None
    open_limit_count: int
    is_limit_up_close: bool
    limit_up_days: int
    strength_score: Decimal
    next_day_watch: bool = False
    watch_reason: list[str] = field(default_factory=list)
    risk_tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReviewStats:
    first_board_count: int
    touched_first_board_count: int
    broken_count: int
    resealed_count: int
    broken_rate: Decimal


@dataclass(frozen=True)
class FirstBoardReview:
    trade_date: str
    first_boards: list[ReviewItem]
    touched_first_boards: list[ReviewItem]
    broken_boards: list[ReviewItem]
    watch_pool: list[ReviewItem]
    stats: ReviewStats


def limit_up_price(previous_close: Decimal, symbol: str, is_st: bool = False) -> Decimal:
    rate = _limit_up_rate(symbol, is_st)
    return (previous_close * (Decimal("1") + rate)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def generate_first_board_review(
    *,
    trade_date: str,
    stocks: list[StockMeta],
    quotes: dict[str, DailyQuote],
    intraday: dict[str, list[IntradayBar]],
    previous_limit_days: dict[str, int],
    config: ReviewConfig | None = None,
) -> FirstBoardReview:
    config = config or ReviewConfig()
    metas = {stock.symbol: stock for stock in stocks}
    touched_items: list[ReviewItem] = []
    first_boards: list[ReviewItem] = []
    broken_boards: list[ReviewItem] = []

    for stock in stocks:
        if _is_excluded(stock):
            continue

        quote = quotes.get(stock.symbol)
        bars = intraday.get(stock.symbol, [])
        if quote is None or not bars:
            continue

        price_limit = limit_up_price(quote.previous_close, stock.symbol, stock.is_st)
        state = _analyze_board_state(bars, quote.close, price_limit)
        if not state.touched or previous_limit_days.get(stock.symbol, 0) != 0:
            continue

        item = _make_review_item(trade_date, stock, quote, price_limit, state)
        touched_items.append(item)
        if state.is_limit_up_close:
            first_boards.append(item)
        else:
            broken_boards.append(item)

    theme_counts = _theme_counts(first_boards)
    first_boards = [_score_item(item, theme_counts) for item in first_boards]
    broken_boards = [_score_item(item, theme_counts) for item in broken_boards]
    touched_items = [_score_item(item, theme_counts) for item in touched_items]

    first_boards.sort(key=lambda item: (item.strength_score, item.turnover_amount), reverse=True)
    broken_boards.sort(key=lambda item: (item.strength_score, item.turnover_amount), reverse=True)
    touched_items.sort(key=lambda item: (item.strength_score, item.turnover_amount), reverse=True)

    watch_pool = _build_watch_pool(first_boards, theme_counts, config)
    broken_count = len(broken_boards)
    touched_count = len(touched_items)
    stats = ReviewStats(
        first_board_count=len(first_boards),
        touched_first_board_count=touched_count,
        broken_count=broken_count,
        resealed_count=sum(1 for item in first_boards if item.open_limit_count > 0),
        broken_rate=_safe_ratio(broken_count, touched_count),
    )
    return FirstBoardReview(trade_date, first_boards, touched_items, broken_boards, watch_pool, stats)


def _limit_up_rate(symbol: str, is_st: bool) -> Decimal:
    if is_st:
        return Decimal("0.05")
    if symbol.startswith(("300", "301", "688", "689")):
        return Decimal("0.20")
    return Decimal("0.10")


def _is_excluded(stock: StockMeta) -> bool:
    if stock.is_st or stock.is_new_unopened:
        return True
    if stock.market == "bj" or stock.symbol.startswith(("8", "4")):
        return True
    return False


def _analyze_board_state(bars: list[IntradayBar], close: Decimal, price_limit: Decimal) -> BoardState:
    touched = False
    first_time: str | None = None
    last_time: str | None = None
    was_at_limit = False
    open_count = 0

    for bar in bars:
        at_limit = bar.price >= price_limit
        if at_limit:
            if not touched:
                first_time = bar.time
            touched = True
            last_time = bar.time
        elif touched and was_at_limit:
            open_count += 1
        was_at_limit = at_limit

    return BoardState(
        touched=touched,
        first_limit_time=first_time,
        last_limit_time=last_time,
        open_limit_count=open_count,
        is_limit_up_close=close >= price_limit,
    )


def _make_review_item(
    trade_date: str,
    stock: StockMeta,
    quote: DailyQuote,
    price_limit: Decimal,
    state: BoardState,
) -> ReviewItem:
    pct_chg = ((quote.close - quote.previous_close) / quote.previous_close * Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    risk_tags: list[str] = []
    if state.open_limit_count:
        risk_tags.append(f"炸板 {state.open_limit_count} 次")
    if state.first_limit_time and state.first_limit_time >= "14:30":
        risk_tags.append("尾盘封板")
    if not state.is_limit_up_close:
        risk_tags.append("炸板未封死")

    return ReviewItem(
        trade_date=trade_date,
        symbol=stock.symbol,
        name=stock.name,
        industry=stock.industry,
        concepts=stock.concepts,
        close=quote.close,
        pct_chg=pct_chg,
        turnover_amount=quote.turnover_amount,
        turnover_rate=quote.turnover_rate,
        limit_up_price=price_limit,
        first_limit_time=state.first_limit_time,
        last_limit_time=state.last_limit_time,
        open_limit_count=state.open_limit_count,
        is_limit_up_close=state.is_limit_up_close,
        limit_up_days=1 if state.is_limit_up_close else 0,
        strength_score=Decimal("0"),
        risk_tags=risk_tags,
    )


def _theme_counts(items: list[ReviewItem]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = item.industry or "未分类"
        counts[key] = counts.get(key, 0) + 1
    return counts


def _score_item(item: ReviewItem, theme_counts: dict[str, int]) -> ReviewItem:
    score = Decimal("0")
    if item.first_limit_time:
        score += _time_score(item.first_limit_time)
    if item.is_limit_up_close:
        score += Decimal("25")
    score -= Decimal(item.open_limit_count * 25)
    score += min(Decimal("12"), Decimal(item.turnover_amount) / Decimal(MONEY_1Y) * Decimal("2"))
    if theme_counts.get(item.industry or "未分类", 0) >= 2:
        score += Decimal("8")
    return _replace_item(item, strength_score=score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _time_score(first_limit_time: str) -> Decimal:
    if first_limit_time <= "09:45":
        return Decimal("40")
    if first_limit_time <= "10:30":
        return Decimal("32")
    if first_limit_time <= "11:30":
        return Decimal("24")
    if first_limit_time <= "14:00":
        return Decimal("16")
    return Decimal("8")


def _build_watch_pool(
    first_boards: list[ReviewItem],
    theme_counts: dict[str, int],
    config: ReviewConfig,
) -> list[ReviewItem]:
    if not first_boards:
        return []

    top_count = max(1, ceil(len(first_boards) * float(config.watch_strength_percent)))
    top_symbols = {item.symbol for item in first_boards[:top_count]}
    pool: list[ReviewItem] = []

    for item in first_boards:
        if item.turnover_amount < config.min_turnover_amount:
            continue
        if item.open_limit_count > config.max_watch_open_limit_count:
            continue

        reasons = [f"成交额达到 {config.min_turnover_amount // MONEY_1Y} 亿以上"]
        if item.symbol in top_symbols:
            reasons.append("封板强度进入前 30%")
        if theme_counts.get(item.industry or "未分类", 0) >= 2:
            reasons.append(f"{item.industry or '未分类'}题材出现 2 只以上首板")
        if item.open_limit_count == 0:
            reasons.append("收盘封死且未炸板")

        pool.append(_replace_item(item, next_day_watch=True, watch_reason=reasons))

    return pool


def _safe_ratio(numerator: int, denominator: int) -> Decimal:
    if denominator == 0:
        return Decimal("0")
    return (Decimal(numerator) / Decimal(denominator)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _replace_item(item: ReviewItem, **changes: object) -> ReviewItem:
    values = item.__dict__.copy()
    values.update(changes)
    return ReviewItem(**values)
