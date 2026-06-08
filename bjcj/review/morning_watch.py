from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from bjcj.review.tencent_finance import TencentRealtimeQuote


@dataclass(frozen=True)
class MorningWatchConfig:
    strong_pct_min: Decimal = Decimal("6")
    normal_pct_min: Decimal = Decimal("0")
    weak_pct_max: Decimal = Decimal("-5")


@dataclass(frozen=True)
class MorningWatchRow:
    symbol: str
    name: str
    level: str
    pct_chg: Decimal
    open_premium: Decimal
    current_price: Decimal
    previous_close: Decimal
    turnover_amount: int
    turnover_rate: Decimal
    first_limit_time: str
    open_limit_count: int
    strength_score: str
    notes: list[str]


@dataclass(frozen=True)
class MorningWatchResult:
    trade_date: str
    rows: list[MorningWatchRow]


def load_review_payload(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def extract_watch_pool_symbols(payload: dict[str, Any]) -> list[str]:
    return [item["symbol"] for item in payload.get("watch_pool", []) if item.get("symbol")]


def build_morning_watch(
    review_payload: dict[str, Any],
    quotes: dict[str, TencentRealtimeQuote],
    *,
    config: MorningWatchConfig | None = None,
) -> MorningWatchResult:
    config = config or MorningWatchConfig()
    rows: list[MorningWatchRow] = []

    for item in review_payload.get("watch_pool", []):
        symbol = item.get("symbol")
        if not symbol or symbol not in quotes:
            continue

        quote = quotes[symbol]
        pct_chg = _pct(quote.close, quote.previous_close)
        open_premium = _pct(quote.open, quote.previous_close)
        notes = _notes(item, quote, pct_chg, open_premium)
        rows.append(
            MorningWatchRow(
                symbol=symbol,
                name=item.get("name") or quote.name,
                level=_level(item, quote, pct_chg, config),
                pct_chg=pct_chg,
                open_premium=open_premium,
                current_price=quote.close,
                previous_close=quote.previous_close,
                turnover_amount=quote.turnover_amount,
                turnover_rate=quote.turnover_rate,
                first_limit_time=item.get("first_limit_time") or "",
                open_limit_count=int(item.get("open_limit_count") or 0),
                strength_score=str(item.get("strength_score", "")),
                notes=notes,
            )
        )

    rows.sort(key=lambda row: (_level_rank(row.level), row.pct_chg, row.turnover_amount), reverse=True)
    return MorningWatchResult(trade_date=str(review_payload.get("trade_date", "latest")), rows=rows)


def render_morning_watch_markdown(result: MorningWatchResult) -> str:
    lines = [
        f"# {result.trade_date} 次日观察池 9:25 盯盘",
        "",
        "## 分层说明",
        "",
        "- 强观察：竞价或早盘明显超预期，接近涨停或高开较强。",
        "- 正常观察：红盘或小幅高开，继续看承接。",
        "- 降级：低开、走弱，或昨日炸板后没有转强。",
        "- 风险：明显低于预期，只观察不追。",
        "",
        "## 观察池",
        "",
        "| 代码 | 名称 | 分层 | 当前涨幅 | 开盘溢价 | 当前成交额 | 昨日首封 | 昨日炸板 | 原因 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for row in result.rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row.symbol,
                    row.name,
                    row.level,
                    _fmt_pct(row.pct_chg),
                    _fmt_pct(row.open_premium),
                    _money_yi(row.turnover_amount),
                    row.first_limit_time,
                    str(row.open_limit_count),
                    "；".join(row.notes),
                ]
            )
            + " |"
        )

    return "\n".join(lines) + "\n"


def _level(item: dict[str, Any], quote: TencentRealtimeQuote, pct_chg: Decimal, config: MorningWatchConfig) -> str:
    open_limit_count = int(item.get("open_limit_count") or 0)
    if quote.limit_up > 0 and quote.close >= quote.limit_up:
        return "强观察"
    if pct_chg >= config.strong_pct_min and open_limit_count <= 1:
        return "强观察"
    if pct_chg <= config.weak_pct_max:
        return "风险"
    if pct_chg < config.normal_pct_min or open_limit_count > 0:
        return "降级"
    return "正常观察"


def _notes(item: dict[str, Any], quote: TencentRealtimeQuote, pct_chg: Decimal, open_premium: Decimal) -> list[str]:
    notes: list[str] = []
    if quote.limit_up > 0 and quote.close >= quote.limit_up:
        notes.append("一字或接近涨停")
    if pct_chg > 0:
        notes.append("红盘承接")
    if open_premium > 0:
        notes.append("竞价高开")
    if int(item.get("open_limit_count") or 0) > 0:
        notes.append("昨日炸板需确认弱转强")
    if pct_chg < 0:
        notes.append("低开或走弱")
    if not notes:
        notes.append("等待方向确认")
    return notes


def _pct(value: Decimal, base: Decimal) -> Decimal:
    if base == 0:
        return Decimal("0")
    return ((value - base) / base * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _fmt_pct(value: Decimal) -> str:
    return f"{value:.2f}%"


def _money_yi(value: int) -> str:
    return f"{value / 100_000_000:.2f} 亿"


def _level_rank(level: str) -> int:
    return {"强观察": 4, "正常观察": 3, "降级": 2, "风险": 1}.get(level, 0)
