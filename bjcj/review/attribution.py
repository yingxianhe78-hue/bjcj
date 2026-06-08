from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from bjcj.review.close_results import CloseResultRecord
from bjcj.review.closed_loop_models import IntradaySnapshotRecord, WatchRecord


@dataclass(frozen=True)
class AttributionRecord:
    trade_date: str
    session: str
    symbol: str
    name: str
    attribution_tags: list[str]
    custom_attribution_tags: list[str]
    attribution_note: str = ""


def build_attribution_records(
    watch_records: list[WatchRecord],
    snapshots: list[IntradaySnapshotRecord],
    close_results: list[CloseResultRecord],
) -> list[AttributionRecord]:
    close_map = {item.symbol: item for item in close_results}
    snapshot_map = _group_snapshots_by_symbol(snapshots)
    rows: list[AttributionRecord] = []
    for record in watch_records:
        result = close_map.get(record.symbol)
        if result is None:
            continue

        tags: list[str] = []
        if record.open_premium_pct > Decimal("0"):
            tags.append("竞价强")
        if record.open_premium_pct < Decimal("0"):
            tags.append("竞价弱")
        if any("转强" in item.subjective_state_tags for item in snapshot_map.get(record.symbol, [])):
            tags.append("承接强")
        if any("弱化" in item.subjective_state_tags for item in snapshot_map.get(record.symbol, [])):
            tags.append("承接弱")
        if "冲高回落" in result.subjective_outcome_tags:
            tags.append("冲高回落")
        if result.broken_limit_up:
            tags.append("炸板修复")

        rows.append(
            AttributionRecord(
                trade_date=record.trade_date,
                session=record.session,
                symbol=record.symbol,
                name=record.name,
                attribution_tags=sorted(set(tags)),
                custom_attribution_tags=[],
            )
        )
    return rows


def _group_snapshots_by_symbol(snapshots: list[IntradaySnapshotRecord]) -> dict[str, list[IntradaySnapshotRecord]]:
    rows: dict[str, list[IntradaySnapshotRecord]] = {}
    for item in snapshots:
        rows.setdefault(item.symbol, []).append(item)
    return rows
