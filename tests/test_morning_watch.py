import unittest
from decimal import Decimal

from bjcj.review.morning_watch import (
    MorningWatchConfig,
    build_morning_watch,
    extract_watch_pool_symbols,
    morning_watch_to_watch_records,
    render_morning_watch_markdown,
)
from bjcj.review.tencent_finance import TencentRealtimeQuote


class MorningWatchTest(unittest.TestCase):
    def test_extracts_watch_pool_symbols(self):
        payload = {
            "watch_pool": [
                {"symbol": "600516", "name": "方大炭素"},
                {"symbol": "002471", "name": "中超控股"},
            ]
        }

        self.assertEqual(extract_watch_pool_symbols(payload), ["600516", "002471"])

    def test_builds_morning_watch_rows_with_levels(self):
        review = {
            "trade_date": "2026-06-05",
            "watch_pool": [
                {
                    "symbol": "600516",
                    "name": "方大炭素",
                    "turnover_amount": 751947918,
                    "first_limit_time": "09:37",
                    "open_limit_count": 0,
                    "strength_score": "85.00",
                },
                {
                    "symbol": "002471",
                    "name": "中超控股",
                    "turnover_amount": 747418123,
                    "first_limit_time": "09:32",
                    "open_limit_count": 1,
                    "strength_score": "70.00",
                },
                {
                    "symbol": "600776",
                    "name": "东方通信",
                    "turnover_amount": 449772787,
                    "first_limit_time": "09:45",
                    "open_limit_count": 0,
                    "strength_score": "82.00",
                },
            ],
        }
        quotes = {
            "600516": TencentRealtimeQuote(
                symbol="600516",
                name="方大炭素",
                close=Decimal("6.12"),
                previous_close=Decimal("5.83"),
                open=Decimal("6.02"),
                high=Decimal("6.12"),
                low=Decimal("5.98"),
                turnover_amount=120_000_000,
                turnover_rate=Decimal("1.20"),
                limit_up=Decimal("6.41"),
                limit_down=Decimal("5.25"),
                stock_type="GP-A",
            ),
            "002471": TencentRealtimeQuote(
                symbol="002471",
                name="中超控股",
                close=Decimal("7.60"),
                previous_close=Decimal("7.95"),
                open=Decimal("7.70"),
                high=Decimal("7.80"),
                low=Decimal("7.50"),
                turnover_amount=80_000_000,
                turnover_rate=Decimal("0.90"),
                limit_up=Decimal("8.75"),
                limit_down=Decimal("7.16"),
                stock_type="GP-A",
            ),
            "600776": TencentRealtimeQuote(
                symbol="600776",
                name="东方通信",
                close=Decimal("17.53"),
                previous_close=Decimal("15.94"),
                open=Decimal("17.53"),
                high=Decimal("17.53"),
                low=Decimal("17.53"),
                turnover_amount=20_000_000,
                turnover_rate=Decimal("0.20"),
                limit_up=Decimal("17.53"),
                limit_down=Decimal("14.35"),
                stock_type="GP-A",
            ),
        }

        result = build_morning_watch(review, quotes, config=MorningWatchConfig())

        self.assertEqual([row.symbol for row in result.rows], ["600776", "600516", "002471"])
        self.assertEqual(result.rows[0].level, "强观察")
        self.assertEqual(result.rows[1].level, "正常观察")
        self.assertEqual(result.rows[2].level, "降级")
        self.assertIn("一字或接近涨停", result.rows[0].notes)
        self.assertIn("低开或走弱", result.rows[2].notes)

    def test_renders_morning_watch_markdown(self):
        review = {
            "trade_date": "2026-06-05",
            "watch_pool": [
                {
                    "symbol": "600516",
                    "name": "方大炭素",
                    "turnover_amount": 751947918,
                    "first_limit_time": "09:37",
                    "open_limit_count": 0,
                    "strength_score": "85.00",
                }
            ],
        }
        quotes = {
            "600516": TencentRealtimeQuote(
                symbol="600516",
                name="方大炭素",
                close=Decimal("6.12"),
                previous_close=Decimal("5.83"),
                open=Decimal("6.02"),
                high=Decimal("6.12"),
                low=Decimal("5.98"),
                turnover_amount=120_000_000,
                turnover_rate=Decimal("1.20"),
                limit_up=Decimal("6.41"),
                limit_down=Decimal("5.25"),
                stock_type="GP-A",
            )
        }

        result = build_morning_watch(review, quotes)
        markdown = render_morning_watch_markdown(result)

        self.assertIn("# 2026-06-05 次日观察池 9:25 盯盘", markdown)
        self.assertIn("| 600516 | 方大炭素 | 正常观察 | 4.97% | 3.26% | 1.20 亿 | 09:37 | 0 |", markdown)


    def test_builds_watch_records_for_closed_loop(self):
        review = {
            "trade_date": "2026-06-05",
            "watch_pool": [
                {
                    "symbol": "600516",
                    "name": "鏂瑰ぇ鐐礌",
                    "turnover_amount": 751947918,
                    "first_limit_time": "09:37",
                    "open_limit_count": 0,
                    "strength_score": "85.00",
                }
            ],
        }
        quotes = {
            "600516": TencentRealtimeQuote(
                symbol="600516",
                name="鏂瑰ぇ鐐礌",
                close=Decimal("6.12"),
                previous_close=Decimal("5.83"),
                open=Decimal("6.02"),
                high=Decimal("6.12"),
                low=Decimal("5.98"),
                turnover_amount=120_000_000,
                turnover_rate=Decimal("1.20"),
                limit_up=Decimal("6.41"),
                limit_down=Decimal("5.25"),
                stock_type="GP-A",
            )
        }

        result = build_morning_watch(review, quotes)
        records = morning_watch_to_watch_records(result)

        self.assertEqual(records[0].trade_date, "2026-06-05")
        self.assertEqual(records[0].session, "morning_watch_925")
        self.assertEqual(records[0].symbol, "600516")
        self.assertEqual(records[0].watch_reasons, ["红盘承接", "竞价高开"])


if __name__ == "__main__":
    unittest.main()
