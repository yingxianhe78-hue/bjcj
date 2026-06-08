from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bjcj.review.closed_loop_checklist import build_acceptance_checklist, render_acceptance_checklist
from scripts.run_closed_loop_task import latest_watch_trade_date


def main() -> None:
    parser = argparse.ArgumentParser(description="Check whether closed-loop automation outputs are complete.")
    parser.add_argument("--trade-date", default=None, help="Trade date to check. Defaults to latest watch.json date.")
    parser.add_argument("--runtime-root", default=None, help="Fallback output root for restricted environments.")
    args = parser.parse_args()

    trade_date = args.trade_date or latest_watch_trade_date(args.runtime_root)
    checklist = build_acceptance_checklist(trade_date, runtime_root=args.runtime_root)
    print(render_acceptance_checklist(checklist))
    raise SystemExit(0 if checklist.passed else 1)


if __name__ == "__main__":
    main()
