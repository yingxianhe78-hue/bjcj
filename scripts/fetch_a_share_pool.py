from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bjcj.review.export import stock_pool_to_csv_text, stock_pool_to_jsonable
from bjcj.review.tencent_finance import fetch_a_share_stock_pool


def main() -> None:
    parser = argparse.ArgumentParser(description="从腾讯财经拉取沪深 A 股股票池")
    parser.add_argument("--json", default="data/a_share_pool.json", help="JSON 输出路径")
    parser.add_argument("--csv", default="data/a_share_pool.csv", help="CSV 输出路径")
    parser.add_argument("--batch-size", type=int, default=250, help="腾讯行情批量请求大小")
    args = parser.parse_args()

    stocks = fetch_a_share_stock_pool(batch_size=args.batch_size)

    json_path = Path(args.json)
    csv_path = Path(args.csv)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    json_path.write_text(
        json.dumps(stock_pool_to_jsonable(stocks), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    csv_path.write_text(stock_pool_to_csv_text(stocks), encoding="utf-8", newline="")

    print(f"fetched {len(stocks)} A-share stocks")
    print(f"json: {json_path}")
    print(f"csv: {csv_path}")


if __name__ == "__main__":
    main()
