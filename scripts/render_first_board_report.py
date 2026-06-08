from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bjcj.review.markdown_report import write_first_board_markdown
from bjcj.review.paths import archive_paths


def main() -> None:
    parser = argparse.ArgumentParser(description="将首板复盘 JSON 渲染为 Markdown 报告")
    parser.add_argument("--input", default="data/reviews/latest_first_board_review.json", help="首板复盘 JSON")
    parser.add_argument("--output", default="reports/latest_first_board_review.md", help="Markdown 输出路径")
    parser.add_argument("--trade-date", default=None, help="按交易日自动使用归档输入输出路径")
    parser.add_argument("--top-n", type=int, default=20, help="每个榜单展示条数")
    args = parser.parse_args()

    if args.trade_date:
        paths = archive_paths(args.trade_date)
        args.input = str(paths.review_json)
        args.output = str(paths.report_markdown)

    write_first_board_markdown(args.input, args.output, top_n=args.top_n)
    print(f"report: {args.output}")


if __name__ == "__main__":
    main()
