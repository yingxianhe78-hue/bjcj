from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from bjcj.review.attribution import AttributionRecord
from bjcj.review.close_results import CloseResultRecord
from bjcj.review.closed_loop_models import WatchRecord


@dataclass(frozen=True)
class DailyClosedLoopSummary:
    trade_date: str
    watch_count: int
    level_counts: dict[str, int]
    success_counts: dict[str, int]
    outcome_tag_counts: dict[str, int]
    attribution_tag_counts: dict[str, int]
    focus_symbols: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WeeklyClosedLoopSummary:
    end_date: str
    trade_day_count: int
    watch_count: int
    level_counts: dict[str, int]
    success_counts: dict[str, int]
    attribution_tag_counts: dict[str, int]
    strong_tags: list[tuple[str, int]] = field(default_factory=list)
    weak_tags: list[tuple[str, int]] = field(default_factory=list)


def build_daily_summary(
    watch_records: list[WatchRecord],
    close_results: list[CloseResultRecord],
    attribution_records: list[AttributionRecord],
) -> DailyClosedLoopSummary:
    return DailyClosedLoopSummary(
        trade_date=watch_records[0].trade_date if watch_records else "latest",
        watch_count=len(watch_records),
        level_counts=dict(Counter(item.watch_level for item in watch_records)),
        success_counts={
            "close_positive": sum(1 for item in close_results if item.close_pct > 0),
            "hit_limit_up": sum(1 for item in close_results if item.hit_limit_up),
            "sealed_limit_up": sum(1 for item in close_results if item.sealed_limit_up),
        },
        outcome_tag_counts=dict(Counter(tag for item in close_results for tag in item.subjective_outcome_tags)),
        attribution_tag_counts=dict(Counter(tag for item in attribution_records for tag in item.attribution_tags)),
        focus_symbols=[item.symbol for item in sorted(close_results, key=lambda item: (item.sealed_limit_up, item.close_pct), reverse=True)[:5]],
    )


def build_weekly_summary(days: list[DailyClosedLoopSummary]) -> WeeklyClosedLoopSummary:
    level_counts: Counter[str] = Counter()
    success_counts: Counter[str] = Counter()
    attribution_counts: Counter[str] = Counter()

    for day in days:
        level_counts.update(day.level_counts)
        success_counts.update(day.success_counts)
        attribution_counts.update(day.attribution_tag_counts)

    return WeeklyClosedLoopSummary(
        end_date=days[-1].trade_date if days else "latest",
        trade_day_count=len(days),
        watch_count=sum(day.watch_count for day in days),
        level_counts=dict(level_counts),
        success_counts=dict(success_counts),
        attribution_tag_counts=dict(attribution_counts),
        strong_tags=attribution_counts.most_common(5),
        weak_tags=sorted(attribution_counts.items(), key=lambda item: item[1])[:5],
    )
