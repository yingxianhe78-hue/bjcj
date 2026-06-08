import unittest

from bjcj.review.paths import archive_paths


class ArchivePathsTest(unittest.TestCase):
    def test_builds_dated_archive_paths(self):
        paths = archive_paths("2026-06-05")

        self.assertEqual(str(paths.review_json), "data\\reviews\\2026-06-05-first-board.json")
        self.assertEqual(str(paths.limit_days_json), "data\\limit_days\\2026-06-05.json")
        self.assertEqual(str(paths.report_markdown), "reports\\2026-06-05-first-board.md")

    def test_keeps_latest_paths_for_latest_label(self):
        paths = archive_paths("latest")

        self.assertEqual(str(paths.review_json), "data\\reviews\\latest_first_board_review.json")
        self.assertEqual(str(paths.limit_days_json), "data\\limit_days\\latest.json")
        self.assertEqual(str(paths.report_markdown), "reports\\latest_first_board_review.md")


if __name__ == "__main__":
    unittest.main()
