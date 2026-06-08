import unittest
from decimal import Decimal

from bjcj.review.closed_loop_models import WatchRecord
from bjcj.review.intraday_snapshots import build_intraday_snapshots
from bjcj.review.tencent_finance import TencentRealtimeQuote


class IntradaySnapshotsTest(unittest.TestCase):
    def test_build_intraday_snapshots_marks_limit_and_state(self):
        records = [
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
        quotes = {
            "600516": TencentRealtimeQuote(
                symbol="600516",
                name="方大炭素",
                close=Decimal("11.00"),
                previous_close=Decimal("10.00"),
                open=Decimal("10.30"),
                high=Decimal("11.00"),
                low=Decimal("10.20"),
                turnover_amount=300_000_000,
                turnover_rate=Decimal("5.20"),
                limit_up=Decimal("11.00"),
                limit_down=Decimal("9.00"),
                stock_type="GP-A",
            )
        }

        snapshots = build_intraday_snapshots(records, quotes, snapshot_time="10:00")

        self.assertEqual(snapshots[0].snapshot_time, "10:00")
        self.assertTrue(snapshots[0].hit_limit_up)
        self.assertIn("转强", snapshots[0].subjective_state_tags)


if __name__ == "__main__":
    unittest.main()
