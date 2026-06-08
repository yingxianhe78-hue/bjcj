import unittest

from bjcj.review.closed_loop_report import (
    render_daily_closed_loop_markdown,
    render_weekly_closed_loop_markdown,
)
from bjcj.review.closed_loop_stats import DailyClosedLoopSummary, WeeklyClosedLoopSummary


class ClosedLoopReportTest(unittest.TestCase):
    def test_render_daily_closed_loop_markdown_contains_top_sections(self):
        summary = DailyClosedLoopSummary(
            trade_date="2026-06-08",
            watch_count=2,
            level_counts={"强观察": 1, "正常观察": 0, "降级": 1},
            success_counts={"close_positive": 1, "hit_limit_up": 1, "sealed_limit_up": 1},
            outcome_tag_counts={"超预期": 1, "低于预期": 1},
            attribution_tag_counts={"竞价强": 1, "承接强": 1},
            focus_symbols=["600516"],
        )

        markdown = render_daily_closed_loop_markdown(summary)

        self.assertIn("# 2026-06-08 闭环日报", markdown)
        self.assertIn("## 层级表现", markdown)
        self.assertIn("## 高频成功归因", markdown)

    def test_render_weekly_closed_loop_markdown_contains_rule_sections(self):
        summary = WeeklyClosedLoopSummary(
            end_date="2026-06-08",
            trade_day_count=2,
            watch_count=6,
            level_counts={"强观察": 2, "正常观察": 1, "降级": 3},
            success_counts={"close_positive": 3, "hit_limit_up": 1, "sealed_limit_up": 1},
            attribution_tag_counts={"竞价强": 3, "冲高回落": 2},
            strong_tags=[("竞价强", 3)],
            weak_tags=[("冲高回落", 2)],
        )

        markdown = render_weekly_closed_loop_markdown(summary)

        self.assertIn("# 2026-06-08 闭环周报", markdown)
        self.assertIn("## 最近有效标签", markdown)
        self.assertIn("## 最近失效标签", markdown)


if __name__ == "__main__":
    unittest.main()
