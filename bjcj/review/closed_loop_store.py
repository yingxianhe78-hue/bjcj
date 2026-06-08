from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from bjcj.review.closed_loop_models import (
    IntradaySnapshotRecord,
    WatchRecord,
    intraday_snapshot_to_jsonable,
    watch_record_to_jsonable,
)
from bjcj.review.close_results import CloseResultRecord
from bjcj.review.attribution import AttributionRecord


def write_watch_records(path: str | Path, records: list[WatchRecord]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "count": len(records),
        "records": [watch_record_to_jsonable(record) for record in records],
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_watch_records(path: str | Path) -> list[WatchRecord]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows: list[WatchRecord] = []
    for item in payload.get("records", []):
        rows.append(
            WatchRecord(
                trade_date=str(item["trade_date"]),
                session=str(item["session"]),
                symbol=str(item["symbol"]),
                name=str(item["name"]),
                watch_level=str(item["watch_level"]),
                open_premium_pct=Decimal(str(item["open_premium_pct"])),
                current_pct_925=Decimal(str(item["current_pct_925"])),
                turnover_amount_925=int(item["turnover_amount_925"]),
                first_limit_time=str(item.get("first_limit_time", "")),
                open_limit_count=int(item.get("open_limit_count", 0)),
                watch_reasons=[str(reason) for reason in item.get("watch_reasons", [])],
            )
        )
    return rows


def append_intraday_snapshots(path: str | Path, records: list[IntradaySnapshotRecord]) -> None:
    existing = read_intraday_snapshots(path)
    payload = {
        "count": len(existing) + len(records),
        "records": [intraday_snapshot_to_jsonable(item) for item in [*existing, *records]],
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_intraday_snapshots(path: str | Path) -> list[IntradaySnapshotRecord]:
    target = Path(path)
    if not target.exists():
        return []

    payload = json.loads(target.read_text(encoding="utf-8"))
    rows: list[IntradaySnapshotRecord] = []
    for item in payload.get("records", []):
        rows.append(
            IntradaySnapshotRecord(
                trade_date=str(item["trade_date"]),
                session=str(item["session"]),
                symbol=str(item["symbol"]),
                name=str(item["name"]),
                snapshot_time=str(item["snapshot_time"]),
                price_change_pct=Decimal(str(item["price_change_pct"])),
                change_vs_open_pct=Decimal(str(item["change_vs_open_pct"])),
                turnover_amount=int(item["turnover_amount"]),
                hit_limit_up=bool(item["hit_limit_up"]),
                sealed_limit_up=bool(item["sealed_limit_up"]),
                broken_limit_up=bool(item["broken_limit_up"]),
                subjective_state_tags=[str(tag) for tag in item.get("subjective_state_tags", [])],
                snapshot_note=str(item.get("snapshot_note", "")),
            )
        )
    return rows


def write_close_results(path: str | Path, records: list[CloseResultRecord]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "count": len(records),
        "records": [
            {
                "trade_date": record.trade_date,
                "session": record.session,
                "symbol": record.symbol,
                "name": record.name,
                "high_pct": f"{record.high_pct:.2f}",
                "close_pct": f"{record.close_pct:.2f}",
                "close_turnover_amount": record.close_turnover_amount,
                "hit_limit_up": record.hit_limit_up,
                "sealed_limit_up": record.sealed_limit_up,
                "broken_limit_up": record.broken_limit_up,
                "has_next_day_watch_value": record.has_next_day_watch_value,
                "subjective_outcome_tags": list(record.subjective_outcome_tags),
            }
            for record in records
        ],
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_attribution_records(path: str | Path, records: list[AttributionRecord]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "count": len(records),
        "records": [
            {
                "trade_date": record.trade_date,
                "session": record.session,
                "symbol": record.symbol,
                "name": record.name,
                "attribution_tags": list(record.attribution_tags),
                "custom_attribution_tags": list(record.custom_attribution_tags),
                "attribution_note": record.attribution_note,
            }
            for record in records
        ],
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_close_results(path: str | Path) -> list[CloseResultRecord]:
    target = Path(path)
    if not target.exists():
        return []

    payload = json.loads(target.read_text(encoding="utf-8"))
    rows: list[CloseResultRecord] = []
    for item in payload.get("records", []):
        rows.append(
            CloseResultRecord(
                trade_date=str(item["trade_date"]),
                session=str(item["session"]),
                symbol=str(item["symbol"]),
                name=str(item["name"]),
                high_pct=Decimal(str(item["high_pct"])),
                close_pct=Decimal(str(item["close_pct"])),
                close_turnover_amount=int(item["close_turnover_amount"]),
                hit_limit_up=bool(item["hit_limit_up"]),
                sealed_limit_up=bool(item["sealed_limit_up"]),
                broken_limit_up=bool(item["broken_limit_up"]),
                has_next_day_watch_value=bool(item["has_next_day_watch_value"]),
                subjective_outcome_tags=[str(tag) for tag in item.get("subjective_outcome_tags", [])],
            )
        )
    return rows


def read_attribution_records(path: str | Path) -> list[AttributionRecord]:
    target = Path(path)
    if not target.exists():
        return []

    payload = json.loads(target.read_text(encoding="utf-8"))
    rows: list[AttributionRecord] = []
    for item in payload.get("records", []):
        rows.append(
            AttributionRecord(
                trade_date=str(item["trade_date"]),
                session=str(item["session"]),
                symbol=str(item["symbol"]),
                name=str(item["name"]),
                attribution_tags=[str(tag) for tag in item.get("attribution_tags", [])],
                custom_attribution_tags=[str(tag) for tag in item.get("custom_attribution_tags", [])],
                attribution_note=str(item.get("attribution_note", "")),
            )
        )
    return rows
