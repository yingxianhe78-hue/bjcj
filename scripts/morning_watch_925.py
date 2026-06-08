from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bjcj.review.markdown_report import load_review_json
from bjcj.review.closed_loop_store import write_watch_records
from bjcj.review.morning_watch import (
    build_morning_watch,
    extract_watch_pool_symbols,
    morning_watch_to_watch_records,
    render_morning_watch_markdown,
)
from bjcj.review.paths import archive_paths, closed_loop_paths
from bjcj.review.tencent_finance import fetch_realtime_quotes


def main() -> None:
    parser = argparse.ArgumentParser(description="9:25 自动盯盘：读取次日观察池并拉腾讯实时行情分层")
    parser.add_argument("--trade-date", default=None, help="复盘交易日，例如 2026-06-05")
    parser.add_argument("--input", default="data/reviews/latest_first_board_review.json", help="首板复盘 JSON")
    parser.add_argument("--output", default="reports/morning_watch/latest_9_25_watch.md", help="盯盘 Markdown 输出")
    parser.add_argument("--runtime-root", default=None, help="runtime output root")
    args = parser.parse_args()

    if args.trade_date:
        paths = archive_paths(args.trade_date)
        args.input = str(paths.review_json)
        args.output = f"reports/morning_watch/{args.trade_date}-9-25-watch.md"

    payload = load_review_json(args.input)
    symbols = extract_watch_pool_symbols(payload)
    quotes = {quote.symbol: quote for quote in fetch_realtime_quotes(symbols)}
    result = build_morning_watch(payload, quotes)

    base = Path(args.runtime_root) if args.runtime_root else Path(".")
    output_path = base / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_morning_watch_markdown(result), encoding="utf-8")

    loop_paths = closed_loop_paths(result.trade_date, runtime_root=args.runtime_root)
    write_watch_records(loop_paths.watch_json, morning_watch_to_watch_records(result))

    print(f"watch pool: {len(symbols)}")
    print(f"quotes fetched: {len(quotes)}")
    print(f"report: {output_path}")


if __name__ == "__main__":
    main()
