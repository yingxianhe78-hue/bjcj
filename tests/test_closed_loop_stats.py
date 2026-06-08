import unittest
from decimal import Decimal

from bjcj.review.attribution import AttributionRecord
from bjcj.review.close_results import CloseResultRecord
from bjcj.review.closed_loop_models import WatchRecord
from bjcj.review.closed_loop_stats import DailyClosedLoopSummary, build_daily_summary, build_weekly_summary


class ClosedLoopStatsTest(unittest.TestCase):
    def test_build_daily_summary_counts_levels_and_tags(self):
        watch_records = [
            WatchRecord(
                trade_date="2026-06-08",
                session="morning_watch_925",
                symbol="600516",
                name="方大炭素",
                watch_level="强观察",
                open_premium_pct=Decimal("3.00"),
                current_pct_925=Decimal("4.00"),
                turnover_amount_925=100_000_000,
                first_limit_time="09:37",
                open_limit_count=0,
                watch_reasons=["红盘承接"],
            ),
            WatchRecord(
                trade_date="2026-06-08",
                session="morning_watch_925",
                symbol="002471",
                name="中超控股",
                watch_level="降级",
                open_premium_pct=Decimal("-1.00"),
                current_pct_925=Decimal("-2.00"),
                turnover_amount_925=80_000_000,
                first_limit_time="09:32",
                open_limit_count=1,
                watch_reasons=["低开或走弱"],
            ),
        ]
        close_results = [
            CloseResultRecord(
                trade_date="2026-06-08",
                session="morning_watch_925",
                symbol="600516",
                name="方大炭素",
                high_pct=Decimal("10.00"),
                close_pct=Decimal("8.00"),
                close_turnover_amount=500_000_000,
                hit_limit_up=True,
                sealed_limit_up=True,
                broken_limit_up=False,
                has_next_day_watch_value=True,
                subjective_outcome_tags=["超预期"],
            ),
            CloseResultRecord(
                trade_date="2026-06-08",
                session="morning_watch_925",
                symbol="002471",
                name="中超控股",
                high_pct=Decimal("1.00"),
                close_pct=Decimal("-3.00"),
                close_turnover_amount=200_000_000,
                hit_limit_up=False,
                sealed_limit_up=False,
                broken_limit_up=False,
                has_next_day_watch_value=False,
                subjective_outcome_tags=["低于预期", "全天弱势"],
            ),
        ]
        attribution_records = [
            AttributionRecord(
                trade_date="2026-06-08",
                session="morning_watch_925",
                symbol="600516",
                name="方大炭素",
                attribution_tags=["竞价强", "承接强"],
                custom_attribution_tags=[],
            ),
            AttributionRecord(
                trade_date="2026-06-08",
                session="morning_watch_925",
                symbol="002471",
                name="中超控股",
                attribution_tags=["竞价弱"],
                custom_attribution_tags=[],
            ),
        ]

        summary = build_daily_summary(watch_records, close_results, attribution_records)

        self.assertEqual(summary.watch_count, 2)
        self.assertEqual(summary.level_counts["强观察"], 1)
        self.assertEqual(summary.success_counts["sealed_limit_up"], 1)

    def test_build_weekly_summary_aggregates_multiple_days(self):
        day_one = DailyClosedLoopSummary(
            trade_date="2026-06-06",
            watch_count=3,
            level_counts={"强观察": 1, "正常观察": 1, "降级": 1},
            success_counts={"close_positive": 2, "hit_limit_up": 1, "sealed_limit_up": 1},
            outcome_tag_counts={"超预期": 1},
            attribution_tag_counts={"竞价强": 2, "承接强": 1},
            focus_symbols=["600516"],
        )
        day_two = DailyClosedLoopSummary(
            trade_date="2026-06-08",
            watch_count=3,
            level_counts={"强观察": 1, "正常观察": 0, "降级": 2},
            success_counts={"close_positive": 1, "hit_limit_up": 0, "sealed_limit_up": 0},
            outcome_tag_counts={"低于预期": 2},
            attribution_tag_counts={"竞价强": 1, "冲高回落": 2},
            focus_symbols=["002471"],
        )

        summary = build_weekly_summary([day_one, day_two])

        self.assertEqual(summary.trade_day_count, 2)
        self.assertEqual(summary.watch_count, 6)
        self.assertEqual(summary.level_counts["强观察"], 2)


if __name__ == "__main__":
    unittest.main()
