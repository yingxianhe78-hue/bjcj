from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Callable
from urllib.request import Request, urlopen

from bjcj.review.core import DailyQuote, IntradayBar, StockMeta


@dataclass(frozen=True)
class TencentRealtimeQuote:
    symbol: str
    name: str
    close: Decimal
    previous_close: Decimal
    open: Decimal
    high: Decimal
    low: Decimal
    turnover_amount: int
    turnover_rate: Decimal
    limit_up: Decimal
    limit_down: Decimal
    stock_type: str


@dataclass(frozen=True)
class TencentReviewInputs:
    stocks: list[StockMeta]
    quotes: dict[str, DailyQuote]
    intraday: dict[str, list[IntradayBar]]


def encode_tencent_symbol(symbol: str) -> str:
    normalized = symbol.strip().lower()
    if normalized.startswith(("sh", "sz")):
        return normalized
    if normalized.startswith(("6", "9")):
        return f"sh{normalized}"
    return f"sz{normalized}"


def a_share_candidate_symbols() -> list[str]:
    symbols: list[str] = []
    symbols.extend(f"{code:06d}" for code in range(1, 4000))
    symbols.extend(f"{code:06d}" for code in range(300001, 302000))
    symbols.extend(f"{code:06d}" for code in range(600000, 606000))
    symbols.extend(f"{code:06d}" for code in range(688000, 690000))
    return symbols


def realtime_quote_url(symbols: list[str]) -> str:
    query = ",".join(encode_tencent_symbol(symbol) for symbol in symbols)
    return f"https://qt.gtimg.cn/q={query}"


def minute_quote_url(symbol: str) -> str:
    return f"https://web.ifzq.gtimg.cn/appstock/app/minute/query?code={encode_tencent_symbol(symbol)}"


def fetch_text(
    url: str,
    *,
    opener: Callable[[Request, float], object] = urlopen,
    timeout: float = 10,
    encoding: str = "gbk",
) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with opener(request, timeout=timeout) as response:
        return response.read().decode(encoding, errors="replace")


def fetch_realtime_quotes(
    symbols: list[str],
    *,
    opener: Callable[[Request, float], object] = urlopen,
    timeout: float = 10,
) -> list[TencentRealtimeQuote]:
    if not symbols:
        return []
    text = fetch_text(realtime_quote_url(symbols), opener=opener, timeout=timeout, encoding="gbk")
    return parse_realtime_quotes(text)


def fetch_a_share_stock_pool(
    *,
    candidates: list[str] | None = None,
    batch_size: int = 200,
    opener: Callable[[Request, float], object] = urlopen,
    timeout: float = 10,
) -> list[StockMeta]:
    symbols = candidates or a_share_candidate_symbols()
    stocks: list[StockMeta] = []

    for batch in _chunks(symbols, batch_size):
        quotes = fetch_realtime_quotes(batch, opener=opener, timeout=timeout)
        for quote in quotes:
            if is_active_a_share_quote(quote):
                stocks.append(
                    StockMeta(
                        symbol=quote.symbol,
                        name=quote.name,
                        is_st=_is_st_name(quote.name),
                        market=_market_of_symbol(quote.symbol),
                    )
                )

    return sorted(stocks, key=lambda stock: stock.symbol)


def fetch_minute_bars(
    symbol: str,
    *,
    opener: Callable[[Request, float], object] = urlopen,
    timeout: float = 10,
) -> list[IntradayBar]:
    text = fetch_text(minute_quote_url(symbol), opener=opener, timeout=timeout, encoding="utf-8")
    return parse_minute_bars(text, symbol)


def fetch_review_inputs(
    symbols: list[str],
    *,
    opener: Callable[[Request, float], object] = urlopen,
    timeout: float = 10,
) -> TencentReviewInputs:
    realtime_quotes = fetch_realtime_quotes(symbols, opener=opener, timeout=timeout)
    stocks = [StockMeta(symbol=quote.symbol, name=quote.name) for quote in realtime_quotes]
    quote_map = quotes_to_daily_quotes(realtime_quotes)
    intraday = {
        quote.symbol: fetch_minute_bars(quote.symbol, opener=opener, timeout=timeout)
        for quote in realtime_quotes
    }
    return TencentReviewInputs(stocks=stocks, quotes=quote_map, intraday=intraday)


def parse_realtime_quote(line: str) -> TencentRealtimeQuote:
    payload = _extract_payload(line)
    return _parse_realtime_payload(payload)


def parse_realtime_quotes(text: str) -> list[TencentRealtimeQuote]:
    quotes: list[TencentRealtimeQuote] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        if not line.startswith(("v_sh", "v_sz")):
            continue
        payload = _extract_payload(line)
        if not payload:
            continue
        quotes.append(_parse_realtime_payload(payload))
    return quotes


def is_active_a_share_quote(quote: TencentRealtimeQuote) -> bool:
    return (
        quote.stock_type.startswith("GP-A")
        and quote.previous_close > 0
        and quote.limit_up != Decimal("-1")
        and quote.limit_down != Decimal("-1")
    )


def quotes_to_daily_quotes(quotes: list[TencentRealtimeQuote]) -> dict[str, DailyQuote]:
    return {
        quote.symbol: DailyQuote(
            symbol=quote.symbol,
            previous_close=quote.previous_close,
            close=quote.close,
            open=quote.open,
            turnover_amount=quote.turnover_amount,
            turnover_rate=quote.turnover_rate,
        )
        for quote in quotes
    }


def parse_minute_bars(text: str, symbol: str) -> list[IntradayBar]:
    payload = json.loads(text)
    node = _find_symbol_node(payload, encode_tencent_symbol(symbol))
    rows = _extract_minute_rows(node)
    return [_parse_minute_row(row) for row in rows]


def _extract_payload(line: str) -> str:
    if '="' not in line:
        raise ValueError("腾讯财经实时行情格式无效")
    return line.split('="', 1)[1].rsplit('";', 1)[0]


def _parse_realtime_payload(payload: str) -> TencentRealtimeQuote:
    fields = payload.split("~")
    if len(fields) < 39:
        raise ValueError("腾讯财经实时行情字段数量不足")

    turnover_amount = _parse_turnover_amount(fields)
    return TencentRealtimeQuote(
        symbol=fields[2],
        name=fields[1],
        close=_decimal(fields[3]),
        previous_close=_decimal(fields[4]),
        open=_decimal(fields[5]),
        high=_decimal_at(fields, 33),
        low=_decimal_at(fields, 34),
        turnover_amount=turnover_amount,
        turnover_rate=_decimal(fields[38]),
        limit_up=_decimal_at(fields, 47),
        limit_down=_decimal_at(fields, 48),
        stock_type=_stock_type(fields),
    )


def _parse_turnover_amount(fields: list[str]) -> int:
    if len(fields) > 35 and "/" in fields[35]:
        parts = fields[35].split("/")
        if len(parts) >= 3 and parts[2]:
            return int(Decimal(parts[2]))
    if len(fields) > 37 and fields[37]:
        return int(Decimal(fields[37]) * Decimal("10000"))
    return 0


def _decimal(value: str) -> Decimal:
    return Decimal(value or "0")


def _decimal_at(fields: list[str], index: int) -> Decimal:
    if len(fields) <= index:
        return Decimal("0")
    return _decimal(fields[index])


def _stock_type(fields: list[str]) -> str:
    if len(fields) > 61 and fields[61]:
        return fields[61]
    symbol = fields[2] if len(fields) > 2 else ""
    if symbol.startswith(("0", "3", "6")):
        return "GP-A"
    return ""


def _is_st_name(name: str) -> bool:
    return "ST" in name.upper()


def _market_of_symbol(symbol: str) -> str:
    return "sh" if symbol.startswith("6") else "sz"


def _chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _find_symbol_node(payload: object, encoded_symbol: str) -> object:
    if isinstance(payload, dict):
        if encoded_symbol in payload:
            return payload[encoded_symbol]
        for value in payload.values():
            try:
                return _find_symbol_node(value, encoded_symbol)
            except ValueError:
                continue
    raise ValueError(f"腾讯财经分时数据中未找到 {encoded_symbol}")


def _extract_minute_rows(node: object) -> list[object]:
    if isinstance(node, dict):
        if "data" in node:
            data = node["data"]
            if isinstance(data, dict) and isinstance(data.get("data"), list):
                return data["data"]
            if isinstance(data, list):
                return data
        for key in ("m1", "minute", "minutes"):
            rows = node.get(key)
            if isinstance(rows, list):
                return rows
        for value in node.values():
            try:
                return _extract_minute_rows(value)
            except ValueError:
                continue
    raise ValueError("腾讯财经分时数据格式无效")


def _parse_minute_row(row: object) -> IntradayBar:
    if isinstance(row, str):
        parts = row.split()
    elif isinstance(row, list):
        parts = [str(part) for part in row]
    else:
        raise ValueError("腾讯财经分时行格式无效")

    if len(parts) < 2:
        raise ValueError("腾讯财经分时行字段不足")

    return IntradayBar(_format_minute_time(parts[0]), Decimal(parts[1]))


def _format_minute_time(value: str) -> str:
    if " " in value:
        value = value.rsplit(" ", 1)[1]
    value = value.replace(":", "")
    if len(value) != 4:
        raise ValueError(f"腾讯财经分时时间格式无效: {value}")
    return f"{value[:2]}:{value[2:]}"
