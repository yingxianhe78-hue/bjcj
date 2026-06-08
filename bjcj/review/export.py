from __future__ import annotations

import csv
from io import StringIO

from bjcj.review.core import StockMeta


def stock_pool_to_jsonable(stocks: list[StockMeta]) -> list[dict[str, object]]:
    return [
        {
            "symbol": stock.symbol,
            "name": stock.name,
            "market": stock.market,
            "is_st": stock.is_st,
        }
        for stock in stocks
    ]


def stock_pool_to_csv_text(stocks: list[StockMeta]) -> str:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=["symbol", "name", "market", "is_st"])
    writer.writeheader()
    for row in stock_pool_to_jsonable(stocks):
        writer.writerow({**row, "is_st": str(row["is_st"]).lower()})
    return output.getvalue()
