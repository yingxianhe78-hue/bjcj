import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from bjcj.review.candidate_scan import CandidateScanResult, LimitCandidate
from bjcj.review.core import DailyQuote, IntradayBar, StockMeta
from bjcj.review.first_board_pipeline import (
    build_first_board_review,
    build_next_limit_days,
    first_board_review_to_jsonable,
    limit_days_to_jsonable,
    load_previous_limit_days,
)


class FirstBoardPipelineTest(unittest.TestCase):
    def test_missing_history_defaults_to_zero_limit_days(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "missing.json"

            state = load_previous_limit_days(path, ["600001", "600002"])

        self.assertFalse(state.history_available)
        self.assertEqual(state.days, {"600001": 0, "600002": 0})

    def test_loads_previous_limit_days_for_known_symbols(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "previous.json"
            path.write_text(json.dumps({"600001": 0, "600002": 1}), encoding="utf-8")

            state = load_previous_limit_days(path, ["600001", "600002", "600003"])

        self.assertTrue(state.history_available)
        self.assertEqual(state.days, {"600001": 0, "600002": 1, "600003": 0})

    def test_ignores_history_from_same_trade_date(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "latest.json"
            path.write_text(
                json.dumps({"trade_date": "2026-06-05", "limit_days": {"600001": 1}}),
                encoding="utf-8",
            )

            state = load_previous_limit_days(path, ["600001"], trade_date="2026-06-05")

        self.assertFalse(state.history_available)
        self.assertEqual(state.days, {"600001": 0})

    def test_builds_first_board_review_and_excludes_existing_limit_chain(self):
        stocks = [
            StockMeta(symbol="600001", name="首板强", industry="机器人"),
            StockMeta(symbol="600002", name="二板排除", industry="机器人"),
            StockMeta(symbol="600003", name="炸板未封", industry="AI"),
        ]
        scan = CandidateScanResult(
            candidates=[
                LimitCandidate("600001", "首板强", Decimal("11.00"), Decimal("10.00"), Decimal("11.00"), 500_000_000, Decimal("8.20")),
                LimitCandidate("600002", "二板排除", Decimal("11.00"), Decimal("10.00"), Decimal("11.00"), 700_000_000, Decimal("9.20")),
            ],
            quotes={
                "600001": DailyQuote("600001", Decimal("10.00"), Decimal("11.00"), Decimal("10.10"), 500_000_000, Decimal("8.20")),
                "600002": DailyQuote("600002", Decimal("10.00"), Decimal("11.00"), Decimal("10.10"), 700_000_000, Decimal("9.20")),
                "600003": DailyQuote("600003", Decimal("10.00"), Decimal("10.70"), Decimal("10.10"), 300_000_000, Decimal("6.20")),
            },
            intraday={
                "600001": [
                    IntradayBar("09:30", Decimal("10.10")),
                    IntradayBar("09:45", Decimal("11.00")),
                    IntradayBar("15:00", Decimal("11.00")),
                ],
                "600002": [
                    IntradayBar("09:35", Decimal("11.00")),
                    IntradayBar("15:00", Decimal("11.00")),
                ],
                "600003": [
                    IntradayBar("10:00", Decimal("11.00")),
                    IntradayBar("13:00", Decimal("10.70")),
                    IntradayBar("15:00", Decimal("10.70")),
                ],
            },
            quote_count=3,
        )

        review = build_first_board_review(
            trade_date="2026-06-05",
            stocks=stocks,
            scan=scan,
            previous_limit_days={"600001": 0, "600002": 1, "600003": 0},
        )

        self.assertEqual([item.symbol for item in review.first_boards], ["600001"])
        self.assertEqual(review.stats.first_board_count, 1)
        self.assertEqual(review.first_boards[0].first_limit_time, "09:45")
        self.assertTrue(review.first_boards[0].is_limit_up_close)

    def test_converts_first_board_review_to_jsonable(self):
        stocks = [StockMeta(symbol="600001", name="首板强", industry="机器人")]
        scan = CandidateScanResult(
            candidates=[
                LimitCandidate("600001", "首板强", Decimal("11.00"), Decimal("10.00"), Decimal("11.00"), 500_000_000, Decimal("8.20"))
            ],
            quotes={
                "600001": DailyQuote("600001", Decimal("10.00"), Decimal("11.00"), Decimal("10.10"), 500_000_000, Decimal("8.20"))
            },
            intraday={
                "600001": [
                    IntradayBar("09:30", Decimal("10.10")),
                    IntradayBar("09:45", Decimal("11.00")),
                    IntradayBar("10:10", Decimal("10.95")),
                    IntradayBar("14:10", Decimal("11.00")),
                    IntradayBar("15:00", Decimal("11.00")),
                ]
            },
            quote_count=1,
        )
        review = build_first_board_review(
            trade_date="2026-06-05",
            stocks=stocks,
            scan=scan,
            previous_limit_days={"600001": 0},
        )

        payload = first_board_review_to_jsonable(review, history_available=False)

        self.assertEqual(payload["trade_date"], "2026-06-05")
        self.assertFalse(payload["history_available"])
        self.assertEqual(payload["stats"]["first_board_count"], 1)
        self.assertEqual(payload["first_boards"][0]["symbol"], "600001")
        self.assertEqual(payload["first_boards"][0]["first_limit_time"], "09:45")
        self.assertEqual(payload["first_boards"][0]["open_limit_count"], 1)
        self.assertTrue(payload["first_boards"][0]["is_limit_up_close"])

    def test_builds_next_limit_days_from_close_limit_candidates(self):
        scan = CandidateScanResult(
            candidates=[
                LimitCandidate("600001", "首板强", Decimal("11.00"), Decimal("10.00"), Decimal("11.00"), 500_000_000, Decimal("8.20")),
                LimitCandidate("600002", "二板强", Decimal("11.00"), Decimal("10.00"), Decimal("11.00"), 700_000_000, Decimal("9.20")),
                LimitCandidate("600003", "炸板未封", Decimal("10.70"), Decimal("10.00"), Decimal("11.00"), 300_000_000, Decimal("6.20")),
            ],
            quotes={},
            intraday={},
            quote_count=3,
        )

        state = build_next_limit_days(scan, previous_limit_days={"600001": 0, "600002": 1, "600003": 0})

        self.assertEqual(state, {"600001": 1, "600002": 2})

    def test_converts_limit_days_to_jsonable_payload(self):
        payload = limit_days_to_jsonable("2026-06-05", {"600002": 2, "600001": 1})

        self.assertEqual(
            payload,
            {
                "trade_date": "2026-06-05",
                "count": 2,
                "limit_days": {"600001": 1, "600002": 2},
            },
        )


if __name__ == "__main__":
    unittest.main()
