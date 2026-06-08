import unittest

from bjcj.review.paths import closed_loop_paths


class ClosedLoopPathsTest(unittest.TestCase):
    def test_builds_closed_loop_paths_for_trade_date(self):
        paths = closed_loop_paths("2026-06-08")

        self.assertEqual(paths.watch_json.as_posix(), "data/closed_loop/2026-06-08/watch.json")
        self.assertEqual(paths.snapshots_json.as_posix(), "data/closed_loop/2026-06-08/snapshots.json")
        self.assertEqual(paths.close_json.as_posix(), "data/closed_loop/2026-06-08/close.json")
        self.assertEqual(paths.attribution_json.as_posix(), "data/closed_loop/2026-06-08/attribution.json")
        self.assertEqual(paths.daily_report_markdown.as_posix(), "reports/closed_loop/2026-06-08-daily.md")

    def test_builds_closed_loop_paths_for_runtime_root(self):
        paths = closed_loop_paths("2026-06-08", runtime_root="runtime_outputs")

        self.assertEqual(paths.watch_json.as_posix(), "runtime_outputs/data/closed_loop/2026-06-08/watch.json")
        self.assertEqual(paths.snapshots_json.as_posix(), "runtime_outputs/data/closed_loop/2026-06-08/snapshots.json")
        self.assertEqual(paths.close_json.as_posix(), "runtime_outputs/data/closed_loop/2026-06-08/close.json")
        self.assertEqual(paths.attribution_json.as_posix(), "runtime_outputs/data/closed_loop/2026-06-08/attribution.json")
        self.assertEqual(paths.daily_report_markdown.as_posix(), "runtime_outputs/reports/closed_loop/2026-06-08-daily.md")


if __name__ == "__main__":
    unittest.main()
