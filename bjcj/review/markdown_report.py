from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_review_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def render_first_board_markdown(payload: dict[str, Any], *, top_n: int = 20) -> str:
    trade_date = payload.get("trade_date", "latest")
    stats = payload.get("stats", {})
    source = payload.get("source", {})
    history_available = bool(payload.get("history_available", False))

    lines: list[str] = [
        f"# {trade_date} 首板复盘",
        "",
        "## 市场概览",
        "",
        f"- 股票池：{source.get('stock_pool_count', '-')}",
        f"- 行情获取：{source.get('quotes_fetched', '-')}",
        f"- 曾触及涨停候选：{source.get('limit_candidate_count', '-')}",
        f"- 候选分时：{source.get('intraday_fetched', '-')}",
        f"- 首板数量：{stats.get('first_board_count', '-')}",
        f"- 曾触板首板候选：{stats.get('touched_first_board_count', '-')}",
        f"- 炸板未封：{stats.get('broken_count', '-')}",
        f"- 回封数量：{stats.get('resealed_count', '-')}",
        f"- 炸板率：{stats.get('broken_rate', '-')}",
        f"- 下一交易日连板状态：{source.get('next_limit_day_count', '-')}",
        f"- 历史连板状态：{'可用' if history_available else '不可用'}",
    ]

    if not history_available:
        lines.extend(
            [
                "",
                "> 当前未使用上一交易日连板状态，结果按首次运行的首板候选口径展示。",
            ]
        )

    lines.extend(
        [
            "",
            f"## 首板强度榜 Top {top_n}",
            "",
            _render_rank_table(payload.get("first_boards", [])[:top_n], include_risk=True),
            "",
            f"## 炸板榜 Top {top_n}",
            "",
            _render_rank_table(payload.get("broken_boards", [])[:top_n], include_risk=True),
            "",
            f"## 次日观察池 Top {top_n}",
            "",
            _render_watch_table(payload.get("watch_pool", [])[:top_n]),
            "",
        ]
    )

    return "\n".join(lines)


def write_first_board_markdown(
    input_path: str | Path,
    output_path: str | Path,
    *,
    top_n: int = 20,
) -> None:
    payload = load_review_json(input_path)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_first_board_markdown(payload, top_n=top_n), encoding="utf-8")


def _render_rank_table(items: list[dict[str, Any]], *, include_risk: bool) -> str:
    headers = ["代码", "名称", "成交额", "换手", "首封", "炸板", "强度", "风险"]
    rows = [
        [
            item.get("symbol", ""),
            item.get("name", ""),
            _money_yi(item.get("turnover_amount", 0)),
            _percent(item.get("turnover_rate", "")),
            item.get("first_limit_time") or "",
            str(item.get("open_limit_count", "")),
            str(item.get("strength_score", "")),
            _join_text(item.get("risk_tags", [])) if include_risk else "",
        ]
        for item in items
    ]
    return _markdown_table(headers, rows)


def _render_watch_table(items: list[dict[str, Any]]) -> str:
    headers = ["代码", "名称", "成交额", "首封", "炸板", "强度", "入池原因"]
    rows = [
        [
            item.get("symbol", ""),
            item.get("name", ""),
            _money_yi(item.get("turnover_amount", 0)),
            item.get("first_limit_time") or "",
            str(item.get("open_limit_count", "")),
            str(item.get("strength_score", "")),
            _join_text(_filter_watch_reasons(item.get("watch_reason", []))),
        ]
        for item in items
    ]
    return _markdown_table(headers, rows)


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    table = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    table.extend("| " + " | ".join(_escape_cell(cell) for cell in row) + " |" for row in rows)
    return "\n".join(table)


def _money_yi(value: object) -> str:
    amount = float(value or 0)
    return f"{amount / 100_000_000:.2f} 亿"


def _percent(value: object) -> str:
    text = str(value)
    return text if text.endswith("%") else f"{text}%"


def _join_text(values: object) -> str:
    if not values:
        return ""
    if isinstance(values, list):
        return "；".join(str(value) for value in values)
    return str(values)


def _filter_watch_reasons(values: object) -> object:
    if not isinstance(values, list):
        return values
    return [value for value in values if "未分类题材" not in str(value)]


def _escape_cell(value: object) -> str:
    return str(value).replace("|", "/")
