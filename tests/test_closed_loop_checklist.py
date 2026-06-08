from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bjcj.review.closed_loop_checklist import build_acceptance_checklist


def write_payload(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"count": len(records), "records": records}, ensure_ascii=False), encoding="utf-8")


class ClosedLoopChecklistTests(unittest.TestCase):
    def test_build_acceptance_checklist_reports_complete_day(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            trade_date = "2026-06-05"
            loop_dir = root / "data" / "closed_loop" / trade_date
            reports_dir = root / "reports" / "closed_loop"

            write_payload(loop_dir / "watch.json", [{"symbol": "600000"}, {"symbol": "000001"}])
            write_payload(
                loop_dir / "snapshots.json",
                [
                    {"symbol": "600000", "snapshot_time": "09:35"},
                    {"symbol": "000001", "snapshot_time": "09:35"},
                    {"symbol": "600000", "snapshot_time": "10:00"},
                    {"symbol": "000001", "snapshot_time": "10:00"},
                    {"symbol": "600000", "snapshot_time": "10:30"},
                    {"symbol": "000001", "snapshot_time": "10:30"},
                    {"symbol": "600000", "snapshot_time": "14:30"},
                    {"symbol": "000001", "snapshot_time": "14:30"},
                ],
            )
            write_payload(loop_dir / "close.json", [{"symbol": "600000"}, {"symbol": "000001"}])
            write_payload(loop_dir / "attribution.json", [{"symbol": "600000"}, {"symbol": "000001"}])
            daily_report = reports_dir / f"{trade_date}-daily.md"
            daily_report.parent.mkdir(parents=True, exist_ok=True)
            daily_report.write_text("# daily", encoding="utf-8")

            checklist = build_acceptance_checklist(trade_date, runtime_root=root)

        self.assertTrue(checklist.passed)
        self.assertEqual(checklist.watch_count, 2)
        self.assertEqual(checklist.snapshot_times, ["09:35", "10:00", "10:30", "14:30"])
        self.assertEqual([item.status for item in checklist.items], ["OK", "OK", "OK", "OK", "OK"])

    def test_build_acceptance_checklist_marks_missing_and_incomplete_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            trade_date = "2026-06-05"
            loop_dir = root / "data" / "closed_loop" / trade_date

            write_payload(loop_dir / "watch.json", [{"symbol": "600000"}])
            write_payload(loop_dir / "snapshots.json", [{"symbol": "600000", "snapshot_time": "09:35"}])

            checklist = build_acceptance_checklist(trade_date, runtime_root=root)

        self.assertFalse(checklist.passed)
        statuses = {item.name: item.status for item in checklist.items}
        self.assertEqual(statuses["watch"], "OK")
        self.assertEqual(statuses["snapshots"], "WARN")
        self.assertEqual(statuses["close"], "MISSING")
        self.assertEqual(statuses["attribution"], "MISSING")
        self.assertEqual(statuses["daily_report"], "MISSING")


if __name__ == "__main__":
    unittest.main()
