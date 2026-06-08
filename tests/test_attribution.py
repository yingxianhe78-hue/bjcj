import unittest
from decimal import Decimal

from bjcj.review.attribution import build_attribution_records
from bjcj.review.close_results import CloseResultRecord
from bjcj.review.closed_loop_models import IntradaySnapshotRecord, WatchRecord


class AttributionTest(unittest.TestCase):
    def test_build_attribution_records_assigns_fixed_tags(self):
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
                sealed_limit_up=False,
                broken_limit_up=True,
                has_next_day_watch_value=True,
                subjective_outcome_tags=["弱转强", "冲高回落", "超预期"],
            )
        ]

        rows = build_attribution_records(watch_records, snapshots, close_results)

        self.assertIn("竞价强", rows[0].attribution_tags)
        self.assertIn("冲高回落", rows[0].attribution_tags)
        self.assertEqual(rows[0].custom_attribution_tags, [])


if __name__ == "__main__":
    unittest.main()
