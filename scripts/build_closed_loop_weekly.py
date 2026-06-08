from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bjcj.review.closed_loop_report import write_weekly_closed_loop_markdown
from bjcj.review.closed_loop_stats import build_daily_summary, build_weekly_summary
from bjcj.review.closed_loop_store import read_attribution_records, read_close_results, read_watch_records
from bjcj.review.paths import closed_loop_paths


def main() -> None:
    parser = argparse.ArgumentParser(description="生成闭环周报")
    parser.add_argument("--end-date", required=True, help="截止交易日，例如 2026-06-08")
    parser.add_argument("--days", type=int, default=5, help="向前聚合的交易日数量")
    parser.add_argument("--runtime-root", default=None, help="runtime output root")
    args = parser.parse_args()

    base = Path(args.runtime_root) if args.runtime_root else Path(".")
    root = base / "data/closed_loop"
    trade_dates = sorted(path.name for path in root.iterdir() if path.is_dir() and path.name <= args.end_date)[-args.days :]
    daily_summaries = []
    for trade_date in trade_dates:
        paths = closed_loop_paths(trade_date, runtime_root=args.runtime_root)
        watch_records = read_watch_records(paths.watch_json)
        close_results = read_close_results(paths.close_json)
        attribution_records = read_attribution_records(paths.attribution_json)
        daily_summaries.append(build_daily_summary(watch_records, close_results, attribution_records))

    summary = build_weekly_summary(daily_summaries)
    output_path = base / f"reports/closed_loop/{args.end_date}-weekly.md"
    write_weekly_closed_loop_markdown(output_path, summary)

    print(f"trade days: {len(daily_summaries)}")
    print(f"weekly report: {output_path}")


if __name__ == "__main__":
    main()
