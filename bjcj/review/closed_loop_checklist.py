from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from bjcj.review.paths import closed_loop_paths


EXPECTED_SNAPSHOT_TIMES = ["09:35", "10:00", "10:30", "14:30"]


@dataclass(frozen=True)
class ChecklistItem:
    name: str
    status: str
    detail: str
    path: Path


@dataclass(frozen=True)
class AcceptanceChecklist:
    trade_date: str
    passed: bool
    watch_count: int
    snapshot_times: list[str]
    items: list[ChecklistItem]


def read_json_payload(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def records_from_payload(path: Path) -> list[dict[str, object]] | None:
    payload = read_json_payload(path)
    if payload is None:
        return None
    records = payload.get("records", [])
    if not isinstance(records, list):
        return []
    return [record for record in records if isinstance(record, dict)]


def build_acceptance_checklist(trade_date: str, runtime_root: str | Path | None = None) -> AcceptanceChecklist:
    paths = closed_loop_paths(trade_date, runtime_root=runtime_root)
    items: list[ChecklistItem] = []

    watch_records = records_from_payload(paths.watch_json)
    watch_count = len(watch_records or [])
    if watch_records is None:
        items.append(ChecklistItem("watch", "MISSING", "watch.json not found", paths.watch_json))
    elif watch_count == 0:
        items.append(ChecklistItem("watch", "WARN", "watch.json has no records", paths.watch_json))
    else:
        items.append(ChecklistItem("watch", "OK", f"{watch_count} watch records", paths.watch_json))

    snapshot_records = records_from_payload(paths.snapshots_json)
    snapshot_times = sorted(
        {
            str(record.get("snapshot_time"))
            for record in (snapshot_records or [])
            if record.get("snapshot_time") in EXPECTED_SNAPSHOT_TIMES
        },
        key=EXPECTED_SNAPSHOT_TIMES.index,
    )
    missing_times = [time for time in EXPECTED_SNAPSHOT_TIMES if time not in snapshot_times]
    if snapshot_records is None:
        items.append(ChecklistItem("snapshots", "MISSING", "snapshots.json not found", paths.snapshots_json))
    elif missing_times:
        items.append(
            ChecklistItem(
                "snapshots",
                "WARN",
                f"captured {len(snapshot_times)}/4 times; missing {', '.join(missing_times)}",
                paths.snapshots_json,
            )
        )
    else:
        items.append(ChecklistItem("snapshots", "OK", f"all 4 snapshot times captured", paths.snapshots_json))

    close_records = records_from_payload(paths.close_json)
    if close_records is None:
        items.append(ChecklistItem("close", "MISSING", "close.json not found", paths.close_json))
    elif watch_count and len(close_records) != watch_count:
        items.append(ChecklistItem("close", "WARN", f"{len(close_records)}/{watch_count} close records", paths.close_json))
    else:
        items.append(ChecklistItem("close", "OK", f"{len(close_records)} close records", paths.close_json))

    attribution_records = records_from_payload(paths.attribution_json)
    if attribution_records is None:
        items.append(ChecklistItem("attribution", "MISSING", "attribution.json not found", paths.attribution_json))
    elif watch_count and len(attribution_records) != watch_count:
        items.append(
            ChecklistItem(
                "attribution",
                "WARN",
                f"{len(attribution_records)}/{watch_count} attribution records",
                paths.attribution_json,
            )
        )
    else:
        items.append(
            ChecklistItem("attribution", "OK", f"{len(attribution_records)} attribution records", paths.attribution_json)
        )

    if not paths.daily_report_markdown.exists():
        items.append(
            ChecklistItem("daily_report", "MISSING", "daily markdown report not found", paths.daily_report_markdown)
        )
    elif paths.daily_report_markdown.stat().st_size == 0:
        items.append(ChecklistItem("daily_report", "WARN", "daily markdown report is empty", paths.daily_report_markdown))
    else:
        items.append(ChecklistItem("daily_report", "OK", "daily markdown report exists", paths.daily_report_markdown))

    passed = all(item.status == "OK" for item in items)
    return AcceptanceChecklist(
        trade_date=trade_date,
        passed=passed,
        watch_count=watch_count,
        snapshot_times=snapshot_times,
        items=items,
    )


def render_acceptance_checklist(checklist: AcceptanceChecklist) -> str:
    status = "PASS" if checklist.passed else "CHECK"
    lines = [
        f"# Closed Loop Acceptance Checklist - {checklist.trade_date}",
        "",
        f"Overall: {status}",
        f"Watch count: {checklist.watch_count}",
        f"Snapshot times: {', '.join(checklist.snapshot_times) if checklist.snapshot_times else '-'}",
        "",
        "| Item | Status | Detail | Path |",
        "| --- | --- | --- | --- |",
    ]
    for item in checklist.items:
        lines.append(f"| {item.name} | {item.status} | {item.detail} | {item.path} |")
    return "\n".join(lines) + "\n"
