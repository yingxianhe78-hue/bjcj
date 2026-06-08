from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bjcj.review.candidate_scan import (
    fetch_limit_candidates,
    limit_candidates_to_jsonable,
    load_stock_pool,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="读取全 A 股票池，筛涨停候选并拉候选分时")
    parser.add_argument("--pool", default="data/a_share_pool.json", help="全 A 股票池 JSON")
    parser.add_argument("--candidates", default="data/candidates/latest_limit_candidates.json", help="候选输出 JSON")
    parser.add_argument("--intraday-summary", default="data/candidates/latest_intraday_summary.json", help="候选分时摘要输出 JSON")
    parser.add_argument("--batch-size", type=int, default=200, help="腾讯实时行情批量请求大小")
    args = parser.parse_args()

    stocks = load_stock_pool(args.pool)
    result = fetch_limit_candidates(stocks, batch_size=args.batch_size)

    candidates_path = Path(args.candidates)
    summary_path = Path(args.intraday_summary)
    candidates_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    candidates_path.write_text(
        json.dumps(limit_candidates_to_jsonable(result.candidates), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    summary_path.write_text(
        json.dumps(_intraday_summary(result.intraday), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"stock pool: {len(stocks)}")
    print(f"quotes fetched: {result.quote_count}")
    print(f"limit candidates: {len(result.candidates)}")
    print(f"intraday fetched: {len(result.intraday)}")
    print(f"candidates: {candidates_path}")
    print(f"intraday summary: {summary_path}")


def _intraday_summary(intraday):
    rows = []
    for symbol, bars in sorted(intraday.items()):
        rows.append(
            {
                "symbol": symbol,
                "bar_count": len(bars),
                "first": _bar_to_jsonable(bars[0]) if bars else None,
                "last": _bar_to_jsonable(bars[-1]) if bars else None,
            }
        )
    return rows


def _bar_to_jsonable(bar):
    return {"time": bar.time, "price": str(bar.price)}


if __name__ == "__main__":
    main()
