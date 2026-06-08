from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import run_closed_loop_task


class ClosedLoopRunnerTests(unittest.TestCase):
    def test_latest_watch_trade_date_returns_latest_watch_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for trade_date in ["2026-06-04", "2026-06-05"]:
                day_dir = root / "data" / "closed_loop" / trade_date
                day_dir.mkdir(parents=True)
                (day_dir / "watch.json").write_text("[]", encoding="utf-8")
            ignored_dir = root / "data" / "closed_loop" / "2026-06-06"
            ignored_dir.mkdir()

            with patch.object(run_closed_loop_task, "PROJECT_ROOT", root):
                self.assertEqual(run_closed_loop_task.latest_watch_trade_date(), "2026-06-05")

    def test_build_morning_watch_command_uses_standard_paths_by_default(self) -> None:
        command = run_closed_loop_task.build_command("morning-watch")

        self.assertIn("morning_watch_925.py", command[1])
        self.assertNotIn("--runtime-root", command)

    def test_build_snapshot_command_uses_latest_watch_trade_date(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            watch_dir = root / "runtime_outputs" / "data" / "closed_loop" / "2026-06-05"
            watch_dir.mkdir(parents=True)
            (watch_dir / "watch.json").write_text("[]", encoding="utf-8")

            with patch.object(run_closed_loop_task, "PROJECT_ROOT", root):
                command = run_closed_loop_task.build_command(
                    "snapshot",
                    time_label="09:35",
                    runtime_root="runtime_outputs",
                )

        self.assertIn("capture_intraday_snapshot.py", command[1])
        self.assertIn("--trade-date", command)
        self.assertIn("2026-06-05", command)
        self.assertIn("--time-label", command)
        self.assertIn("09:35", command)
        self.assertIn("--runtime-root", command)
        self.assertIn("runtime_outputs", command)


if __name__ == "__main__":
    unittest.main()
