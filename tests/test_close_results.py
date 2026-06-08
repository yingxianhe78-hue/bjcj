import unittest
from decimal import Decimal

from bjcj.review.close_results import build_close_results
from bjcj.review.closed_loop_models import IntradaySnapshotRecord, WatchRecord
from bjcj.review.tencent_finance import TencentRealtimeQuote


class CloseResultsTest(unittest.TestCase):
    def test_build_close_results_uses_snapshots_for_subjective_tags(self):
        watch_records = [
            WatchRecord(
                trade_date="2026-06-08",
                session="morning_watch_925",
                symbol="600516",
                name="方大炭素",
                watch_level="正常观察",
                open_premium_pct=Decimal("3.00"),
                current_pct_925=Decimal("4.00"),
                turnover_amount_925=100_000_000,
                first_limit_time="09:37",
                open_limit_count=0,
                watch_reasons=["红盘承接"],
            )
        ]
        snapshots = [
            IntradaySnapshotRecord(
                trade_date="2026-06-08",
                session="morning_watch_925",
                symbol="600516",
                name="方大炭素",
                snapshot_time="10:00",
                price_change_pct=Decimal("7.50"),
                change_vs_open_pct=Decimal("4.00"),
                turnover_amount=300_000_000,
                hit_limit_up=True,
                sealed_limit_up=False,
                broken_limit_up=True,
                subjective_state_tags=["转强", "冲高回落"],
            )
        ]
        close_quotes = {
            "600516": TencentRealtimeQuote(
                symbol="600516",
                name="方大炭素",
                close=Decimal("10.80"),
                previous_close=Decimal("10.00"),
                open=Decimal("10.30"),
                high=Decimal("11.00"),
                low=Decimal("10.20"),
                turnover_amount=500_000_000,
                turnover_rate=Decimal("7.10"),
                limit_up=Decimal("11.00"),
                limit_down=Decimal("9.00"),
                stock_type="GP-A",
            )
        }

        results = build_close_results(watch_records, snapshots, close_quotes)

        self.assertTrue(results[0].broken_limit_up)
        self.assertIn("冲高回落", results[0].subjective_outcome_tags)


if __name__ == "__main__":
    unittest.main()
