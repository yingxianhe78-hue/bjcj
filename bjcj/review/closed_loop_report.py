from __future__ import annotations

from pathlib import Path

from bjcj.review.closed_loop_stats import DailyClosedLoopSummary, WeeklyClosedLoopSummary


def render_daily_closed_loop_markdown(summary: DailyClosedLoopSummary) -> str:
    lines = [
        f"# {summary.trade_date} 闭环日报",
        "",
        "## 层级表现",
        "",
        f"- 观察池数量：{summary.watch_count}",
        f"- 强观察：{summary.level_counts.get('强观察', 0)}",
        f"- 正常观察：{summary.level_counts.get('正常观察', 0)}",
        f"- 降级：{summary.level_counts.get('降级', 0)}",
        f"- 风险：{summary.level_counts.get('风险', 0)}",
        "",
        "## 结果统计",
        "",
        f"- 收盘红盘：{summary.success_counts.get('close_positive', 0)}",
        f"- 日内摸板：{summary.success_counts.get('hit_limit_up', 0)}",
        f"- 收盘封板：{summary.success_counts.get('sealed_limit_up', 0)}",
        "",
        "## 高频成功归因",
        "",
    ]
    for tag, count in sorted(summary.attribution_tag_counts.items(), key=lambda item: item[1], reverse=True)[:5]:
        lines.append(f"- {tag}: {count}")
    lines.extend(
        [
            "",
            "## 重点观察",
            "",
            f"- {'、'.join(summary.focus_symbols) if summary.focus_symbols else '无'}",
            "",
        ]
    )
    return "\n".join(lines)


def write_daily_closed_loop_markdown(path: str | Path, summary: DailyClosedLoopSummary) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_daily_closed_loop_markdown(summary), encoding="utf-8")


def render_weekly_closed_loop_markdown(summary: WeeklyClosedLoopSummary) -> str:
    lines = [
        f"# {summary.end_date} 闭环周报",
        "",
        "## 周度概览",
        "",
        f"- 交易日数量：{summary.trade_day_count}",
        f"- 观察池总量：{summary.watch_count}",
        f"- 强观察：{summary.level_counts.get('强观察', 0)}",
        f"- 正常观察：{summary.level_counts.get('正常观察', 0)}",
        f"- 降级：{summary.level_counts.get('降级', 0)}",
        "",
        "## 最近有效标签",
        "",
    ]
    for tag, count in summary.strong_tags:
        lines.append(f"- {tag}: {count}")
    lines.extend(["", "## 最近失效标签", ""])
    for tag, count in summary.weak_tags:
        lines.append(f"- {tag}: {count}")
    lines.append("")
    return "\n".join(lines)


def write_weekly_closed_loop_markdown(path: str | Path, summary: WeeklyClosedLoopSummary) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_weekly_closed_loop_markdown(summary), encoding="utf-8")
