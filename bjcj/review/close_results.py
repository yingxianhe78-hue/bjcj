from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP

from bjcj.review.closed_loop_models import IntradaySnapshotRecord, WatchRecord
from bjcj.review.tencent_finance import TencentRealtimeQuote


@dataclass(frozen=True)
class CloseResultRecord:
    trade_date: str
    session: str
    symbol: str
    name: str
    high_pct: Decimal
    close_pct: Decimal
    close_turnover_amount: int
    hit_limit_up: bool
    sealed_limit_up: bool
    broken_limit_up: bool
    has_next_day_watch_value: bool
    subjective_outcome_tags: list[str] = field(default_factory=list)


def build_close_results(
    watch_records: list[WatchRecord],
    snapshots: list[IntradaySnapshotRecord],
    close_quotes: dict[str, TencentRealtimeQuote],
) -> list[CloseResultRecord]:
    snapshot_map = _group_snapshots_by_symbol(snapshots)
    rows: list[CloseResultRecord] = []
    for record in watch_records:
        quote = close_quotes.get(record.symbol)
        if quote is None:
            continue
        symbol_snapshots = snapshot_map.get(record.symbol, [])
        hit_limit_up = any(item.hit_limit_up for item in symbol_snapshots) or quote.high >= quote.limit_up > Decimal("0")
        sealed_limit_up = quote.close >= quote.limit_up > Decimal("0")
        broken_limit_up = any(item.broken_limit_up for item in symbol_snapshots) or (hit_limit_up and not sealed_limit_up)
        rows.append(
            CloseResultRecord(
                trade_date=record.trade_date,
                session=record.session,
                symbol=record.symbol,
                name=record.name,
                high_pct=_pct(quote.high, quote.previous_close),
                close_pct=_pct(quote.close, quote.previous_close),
                close_turnover_amount=quote.turnover_amount,
                hit_limit_up=hit_limit_up,
                sealed_limit_up=sealed_limit_up,
                broken_limit_up=broken_limit_up,
                has_next_day_watch_value=_has_watch_value(record.watch_level, _pct(quote.close, quote.previous_close)),
                subjective_outcome_tags=_outcome_tags(record.watch_level, symbol_snapshots, _pct(quote.close, quote.previous_close), broken_limit_up),
            )
        )
    return rows


def _group_snapshots_by_symbol(snapshots: list[IntradaySnapshotRecord]) -> dict[str, list[IntradaySnapshotRecord]]:
    rows: dict[str, list[IntradaySnapshotRecord]] = {}
    for item in snapshots:
        rows.setdefault(item.symbol, []).append(item)
    return rows


def _outcome_tags(
    watch_level: str,
    snapshots: list[IntradaySnapshotRecord],
    close_pct: Decimal,
    broken_limit_up: bool,
) -> list[str]:
    tags: list[str] = []
    snapshot_tags = {tag for item in snapshots for tag in item.subjective_state_tags}
    if "转强" in snapshot_tags:
        tags.append("弱转强")
    if "冲高回落" in snapshot_tags or broken_limit_up:
        tags.append("冲高回落")
    if close_pct >= Decimal("5"):
        tags.append("超预期")
    elif close_pct > Decimal("0"):
        tags.append("符合预期")
    else:
        tags.append("低于预期")
    if close_pct < Decimal("0"):
        tags.append("全天弱势")
    if watch_level == "强观察" and "超预期" not in tags and close_pct > Decimal("0"):
        tags.append("符合预期")
    return sorted(set(tags), key=tags.index)


def _has_watch_value(watch_level: str, close_pct: Decimal) -> bool:
    return close_pct > Decimal("0") or watch_level in {"强观察", "正常观察"}


def _pct(value: Decimal, base: Decimal) -> Decimal:
    if base == 0:
        return Decimal("0")
    return ((value - base) / base * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
