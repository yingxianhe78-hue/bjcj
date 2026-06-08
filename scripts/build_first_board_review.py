from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bjcj.review.candidate_scan import fetch_limit_candidates, load_stock_pool
from bjcj.review.first_board_pipeline import (
    build_first_board_review,
    build_next_limit_days,
    first_board_review_to_jsonable,
    limit_days_to_jsonable,
    load_previous_limit_days,
)
from bjcj.review.paths import archive_paths


def main() -> None:
    parser = argparse.ArgumentParser(description="执行首板复盘第 4 步：识别首封、炸板和首板")
    parser.add_argument("--pool", default="data/a_share_pool.json", help="全 A 股票池 JSON")
    parser.add_argument("--history", default=None, help="上一交易日连板高度 JSON；不传则按无历史处理")
    parser.add_argument("--save-history", default=None, help="保存本交易日连板高度 JSON")
    parser.add_argument("--output", default="data/reviews/latest_first_board_review.json", help="首板复盘输出 JSON")
    parser.add_argument("--trade-date", default="latest", help="交易日标签，例如 2026-06-05")
    parser.add_argument("--archive", action="store_true", help="按 trade-date 自动生成归档输出路径")
    parser.add_argument("--batch-size", type=int, default=200, help="腾讯实时行情批量请求大小")
    args = parser.parse_args()

    if args.archive:
        paths = archive_paths(args.trade_date)
        args.output = str(paths.review_json)
        args.save_history = args.save_history or str(paths.limit_days_json)
    else:
        args.save_history = args.save_history or "data/limit_days/latest.json"

    stocks = load_stock_pool(args.pool)
    scan = fetch_limit_candidates(stocks, batch_size=args.batch_size)
    previous = load_previous_limit_days(
        args.history or "__missing_previous_limit_days__.json",
        [candidate.symbol for candidate in scan.candidates],
        trade_date=args.trade_date,
    )
    review = build_first_board_review(
        trade_date=args.trade_date,
        stocks=stocks,
        scan=scan,
        previous_limit_days=previous.days,
    )
    next_limit_days = build_next_limit_days(scan, previous_limit_days=previous.days)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "source": {
                    "stock_pool_count": len(stocks),
                    "quotes_fetched": scan.quote_count,
                    "limit_candidate_count": len(scan.candidates),
                    "intraday_fetched": len(scan.intraday),
                    "history_path": args.history,
                    "save_history_path": args.save_history,
                    "next_limit_day_count": len(next_limit_days),
                },
                **first_board_review_to_jsonable(review, history_available=previous.history_available),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    history_path = Path(args.save_history)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(
        json.dumps(limit_days_to_jsonable(args.trade_date, next_limit_days), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"stock pool: {len(stocks)}")
    print(f"quotes fetched: {scan.quote_count}")
    print(f"limit candidates: {len(scan.candidates)}")
    print(f"intraday fetched: {len(scan.intraday)}")
    print(f"history available: {previous.history_available}")
    print(f"first boards: {review.stats.first_board_count}")
    print(f"broken boards: {review.stats.broken_count}")
    print(f"watch pool: {len(review.watch_pool)}")
    print(f"next limit days: {len(next_limit_days)}")
    print(f"output: {output_path}")
    print(f"saved history: {history_path}")


if __name__ == "__main__":
    main()
