from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bjcj.review.closed_loop_store import append_intraday_snapshots, read_watch_records
from bjcj.review.intraday_snapshots import build_intraday_snapshots
from bjcj.review.paths import closed_loop_paths
from bjcj.review.tencent_finance import fetch_realtime_quotes


def main() -> None:
    parser = argparse.ArgumentParser(description="捕获观察池盘中固定时点快照")
    parser.add_argument("--trade-date", required=True, help="交易日，例如 2026-06-08")
    parser.add_argument("--time-label", required=True, choices=["09:35", "10:00", "10:30", "14:30"])
    parser.add_argument("--runtime-root", default=None, help="runtime output root")
    args = parser.parse_args()

    paths = closed_loop_paths(args.trade_date, runtime_root=args.runtime_root)
    watch_records = read_watch_records(paths.watch_json)
    symbols = [item.symbol for item in watch_records]
    quotes = {quote.symbol: quote for quote in fetch_realtime_quotes(symbols)}
    snapshots = build_intraday_snapshots(watch_records, quotes, snapshot_time=args.time_label)
    append_intraday_snapshots(paths.snapshots_json, snapshots)

    print(f"watch records: {len(watch_records)}")
    print(f"quotes fetched: {len(quotes)}")
    print(f"snapshots appended: {len(snapshots)}")
    print(f"snapshot file: {paths.snapshots_json}")


if __name__ == "__main__":
    main()
