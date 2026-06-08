from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from bjcj.review.closed_loop_models import IntradaySnapshotRecord, WatchRecord
from bjcj.review.tencent_finance import TencentRealtimeQuote


def build_intraday_snapshots(
    watch_records: list[WatchRecord],
    quotes: dict[str, TencentRealtimeQuote],
    *,
    snapshot_time: str,
) -> list[IntradaySnapshotRecord]:
    rows: list[IntradaySnapshotRecord] = []
    for record in watch_records:
        quote = quotes.get(record.symbol)
        if quote is None:
            continue

        price_change_pct = _pct(quote.close, quote.previous_close)
        change_vs_open_pct = _pct(quote.close, quote.open)
        hit_limit_up = quote.high >= quote.limit_up > Decimal("0")
        sealed_limit_up = quote.close >= quote.limit_up > Decimal("0")

        rows.append(
            IntradaySnapshotRecord(
                trade_date=record.trade_date,
                session=record.session,
                symbol=record.symbol,
                name=record.name,
                snapshot_time=snapshot_time,
                price_change_pct=price_change_pct,
                change_vs_open_pct=change_vs_open_pct,
                turnover_amount=quote.turnover_amount,
                hit_limit_up=hit_limit_up,
                sealed_limit_up=sealed_limit_up,
                broken_limit_up=hit_limit_up and not sealed_limit_up,
                subjective_state_tags=_snapshot_tags(record.watch_level, price_change_pct, change_vs_open_pct),
            )
        )
    return rows


def _snapshot_tags(watch_level: str, price_change_pct: Decimal, change_vs_open_pct: Decimal) -> list[str]:
    tags: list[str] = []
    if price_change_pct >= Decimal("6") or change_vs_open_pct >= Decimal("2"):
        tags.append("转强")
    if price_change_pct > Decimal("0"):
        tags.append("承接强")
    if price_change_pct < Decimal("0"):
        tags.append("弱化")
    if not tags:
        tags.append("横住待确认")
    if watch_level == "强观察" and "转强" not in tags:
        tags.append("承接强")
    return tags


def _pct(value: Decimal, base: Decimal) -> Decimal:
    if base == 0:
        return Decimal("0")
    return ((value - base) / base * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
