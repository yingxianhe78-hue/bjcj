from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bjcj.review.closed_loop_models import ClosedLoopPaths


@dataclass(frozen=True)
class ArchivePaths:
    review_json: Path
    limit_days_json: Path
    report_markdown: Path


def archive_paths(trade_date: str) -> ArchivePaths:
    if trade_date == "latest":
        return ArchivePaths(
            review_json=Path("data/reviews/latest_first_board_review.json"),
            limit_days_json=Path("data/limit_days/latest.json"),
            report_markdown=Path("reports/latest_first_board_review.md"),
        )

    return ArchivePaths(
        review_json=Path(f"data/reviews/{trade_date}-first-board.json"),
        limit_days_json=Path(f"data/limit_days/{trade_date}.json"),
        report_markdown=Path(f"reports/{trade_date}-first-board.md"),
    )


def closed_loop_paths(trade_date: str, runtime_root: str | Path | None = None) -> ClosedLoopPaths:
    base = Path(runtime_root) if runtime_root else Path(".")
    root = base / f"data/closed_loop/{trade_date}"
    return ClosedLoopPaths(
        root_dir=root,
        watch_json=root / "watch.json",
        snapshots_json=root / "snapshots.json",
        close_json=root / "close.json",
        attribution_json=root / "attribution.json",
        daily_report_markdown=base / f"reports/closed_loop/{trade_date}-daily.md",
    )
