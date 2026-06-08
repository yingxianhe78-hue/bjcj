from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bjcj.review.attribution import build_attribution_records
from bjcj.review.close_results import build_close_results
from bjcj.review.closed_loop_report import write_daily_closed_loop_markdown
from bjcj.review.closed_loop_stats import build_daily_summary
from bjcj.review.closed_loop_store import (
    read_intraday_snapshots,
    read_watch_records,
    write_attribution_records,
    write_close_results,
)
from bjcj.review.paths import closed_loop_paths
from bjcj.review.tencent_finance import fetch_realtime_quotes


def main() -> None:
    parser = argparse.ArgumentParser(description="收盘后生成闭环日报")
    parser.add_argument("--trade-date", required=True, help="交易日，例如 2026-06-08")
    parser.add_argument("--runtime-root", default=None, help="runtime output root")
    args = parser.parse_args()

    paths = closed_loop_paths(args.trade_date, runtime_root=args.runtime_root)
    watch_records = read_watch_records(paths.watch_json)
    snapshots = read_intraday_snapshots(paths.snapshots_json)
    symbols = [item.symbol for item in watch_records]
    close_quotes = {quote.symbol: quote for quote in fetch_realtime_quotes(symbols)}

    close_results = build_close_results(watch_records, snapshots, close_quotes)
    attribution_records = build_attribution_records(watch_records, snapshots, close_results)
    write_close_results(paths.close_json, close_results)
    write_attribution_records(paths.attribution_json, attribution_records)

    summary = build_daily_summary(watch_records, close_results, attribution_records)
    write_daily_closed_loop_markdown(paths.daily_report_markdown, summary)

    print(f"watch records: {len(watch_records)}")
    print(f"snapshots: {len(snapshots)}")
    print(f"close results: {len(close_results)}")
    print(f"attribution records: {len(attribution_records)}")
    print(f"daily report: {paths.daily_report_markdown}")


if __name__ == "__main__":
    main()
