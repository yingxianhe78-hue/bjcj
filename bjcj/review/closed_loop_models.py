from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path


@dataclass(frozen=True)
class WatchRecord:
    trade_date: str
    session: str
    symbol: str
    name: str
    watch_level: str
    open_premium_pct: Decimal
    current_pct_925: Decimal
    turnover_amount_925: int
    first_limit_time: str
    open_limit_count: int
    watch_reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class IntradaySnapshotRecord:
    trade_date: str
    session: str
    symbol: str
    name: str
    snapshot_time: str
    price_change_pct: Decimal
    change_vs_open_pct: Decimal
    turnover_amount: int
    hit_limit_up: bool
    sealed_limit_up: bool
    broken_limit_up: bool
    subjective_state_tags: list[str] = field(default_factory=list)
    snapshot_note: str = ""


@dataclass(frozen=True)
class ClosedLoopPaths:
    root_dir: Path
    watch_json: Path
    snapshots_json: Path
    close_json: Path
    attribution_json: Path
    daily_report_markdown: Path


def watch_record_to_jsonable(record: WatchRecord) -> dict[str, object]:
    return {
        "trade_date": record.trade_date,
        "session": record.session,
        "symbol": record.symbol,
        "name": record.name,
        "watch_level": record.watch_level,
        "open_premium_pct": f"{record.open_premium_pct:.2f}",
        "current_pct_925": f"{record.current_pct_925:.2f}",
        "turnover_amount_925": record.turnover_amount_925,
        "first_limit_time": record.first_limit_time,
        "open_limit_count": record.open_limit_count,
        "watch_reasons": list(record.watch_reasons),
    }


def intraday_snapshot_to_jsonable(record: IntradaySnapshotRecord) -> dict[str, object]:
    return {
        "trade_date": record.trade_date,
        "session": record.session,
        "symbol": record.symbol,
        "name": record.name,
        "snapshot_time": record.snapshot_time,
        "price_change_pct": f"{record.price_change_pct:.2f}",
        "change_vs_open_pct": f"{record.change_vs_open_pct:.2f}",
        "turnover_amount": record.turnover_amount,
        "hit_limit_up": record.hit_limit_up,
        "sealed_limit_up": record.sealed_limit_up,
        "broken_limit_up": record.broken_limit_up,
        "subjective_state_tags": list(record.subjective_state_tags),
        "snapshot_note": record.snapshot_note,
    }
