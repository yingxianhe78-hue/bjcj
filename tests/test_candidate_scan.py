import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from bjcj.review.candidate_scan import (
    LimitCandidate,
    fetch_limit_candidates,
    limit_candidates_to_jsonable,
    load_stock_pool,
)
from bjcj.review.core import IntradayBar, StockMeta


class FakeResponse:
    def __init__(self, text, encoding="gbk"):
        self.text = text
        self.encoding = encoding

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self.text.encode(self.encoding)


class UrlMapOpener:
    def __init__(self, responses):
        self.responses = responses
        self.urls = []

    def __call__(self, request, timeout):
        self.urls.append(request.full_url)
        text, encoding = self.responses[request.full_url]
        return FakeResponse(text, encoding)


class CandidateScanTest(unittest.TestCase):
    def test_loads_stock_pool_from_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "pool.json"
            path.write_text(
                json.dumps(
                    [
                        {"symbol": "600001", "name": "首板样本", "market": "sh", "is_st": False},
                        {"symbol": "000004", "name": "*ST国华", "market": "sz", "is_st": True},
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            stocks = load_stock_pool(path)

        self.assertEqual(
            stocks,
            [
                StockMeta(symbol="600001", name="首板样本", market="sh", is_st=False),
                StockMeta(symbol="000004", name="*ST国华", market="sz", is_st=True),
            ],
        )

    def test_fetches_quotes_filters_touched_limit_candidates_and_fetches_only_candidate_minutes(self):
        realtime_url = "https://qt.gtimg.cn/q=sh600001,sh600002,sz000004,sh600421"
        minute_url = "https://web.ifzq.gtimg.cn/appstock/app/minute/query?code=sh600001"
        broken_minute_url = "https://web.ifzq.gtimg.cn/appstock/app/minute/query?code=sh600002"
        opener = UrlMapOpener(
            {
                realtime_url: (
                    "\n".join(
                        [
                            'v_sh600001="1~首板样本~600001~11.00~10.00~10.10~1000~500~500~10.99~100~10.98~200~10.97~300~10.96~400~10.95~500~11.00~120~11.01~130~11.02~140~11.03~150~11.04~160~~20260605150000~1.00~10.00~11.00~10.00~11.00/1000/500000000~1000~50000~8.20~5.00~~11.00~10.00~10.00~1000000000~1200000000~1.00~11.00~9.00~1.00~0~0~0~0~~~0~0~0~0~ ~GP-A~";',
                            'v_sh600002="1~炸板样本~600002~10.50~10.00~10.10~1000~500~500~10.49~100~10.48~200~10.47~300~10.46~400~10.45~500~10.50~120~10.51~130~10.52~140~10.53~150~10.54~160~~20260605150000~0.50~5.00~11.00~10.00~10.50/1000/300000000~1000~30000~6.10~5.00~~11.00~10.00~5.00~1000000000~1200000000~1.00~11.00~9.00~1.00~0~0~0~0~~~0~0~0~0~ ~GP-A~";',
                            'v_sz000004="1~*ST国华~000004~5.25~5.00~5.00~1000~500~500~5.24~100~5.23~200~5.22~300~5.21~400~5.20~500~5.25~120~5.26~130~5.27~140~5.28~150~5.29~160~~20260605150000~0.25~5.00~5.25~5.00~5.25/1000/100000000~1000~10000~2.10~5.00~~5.25~5.00~5.00~1000000000~1200000000~1.00~5.25~4.75~1.00~0~0~0~0~~~0~0~0~0~ ~GP-A~";',
                            'v_sh600421="1~退市华嵘~600421~0.36~0.33~0.33~1000~500~500~0.35~100~0.34~200~0.33~300~0.32~400~0.31~500~0.36~120~0.37~130~0.38~140~0.39~150~0.40~160~~20260605150000~0.03~9.09~0.36~0.33~0.36/1000/6786388~1000~678~10.00~5.00~~0.36~0.33~9.09~1000000000~1200000000~1.00~0.36~0.30~1.00~0~0~0~0~~~0~0~0~0~ ~GP-A~";',
                        ]
                    ),
                    "gbk",
                ),
                minute_url: (
                    '{"data":{"sh600001":{"data":{"data":["0930 10.10 100","0945 11.00 200","1500 11.00 300"]}}}}',
                    "utf-8",
                ),
                broken_minute_url: (
                    '{"data":{"sh600002":{"data":{"data":["0930 10.10 100","1000 11.00 200","1500 10.50 300"]}}}}',
                    "utf-8",
                ),
            }
        )
        stocks = [
            StockMeta(symbol="600001", name="首板样本", market="sh"),
            StockMeta(symbol="600002", name="炸板样本", market="sh"),
            StockMeta(symbol="000004", name="*ST国华", market="sz", is_st=True),
            StockMeta(symbol="600421", name="退市华嵘", market="sh"),
        ]

        result = fetch_limit_candidates(stocks, batch_size=4, opener=opener)

        self.assertEqual([candidate.symbol for candidate in result.candidates], ["600001", "600002"])
        self.assertEqual(result.quote_count, 4)
        self.assertEqual(result.intraday["600001"][-1], IntradayBar("15:00", Decimal("11.00")))
        self.assertEqual(result.intraday["600002"][-1], IntradayBar("15:00", Decimal("10.50")))
        self.assertEqual(opener.urls, [realtime_url, minute_url, broken_minute_url])

    def test_converts_candidates_to_jsonable_rows(self):
        rows = limit_candidates_to_jsonable(
            [
                LimitCandidate(
                    symbol="600001",
                    name="首板样本",
                    close=Decimal("11.00"),
                    previous_close=Decimal("10.00"),
                    limit_up=Decimal("11.00"),
                    turnover_amount=500_000_000,
                    turnover_rate=Decimal("8.20"),
                )
            ]
        )

        self.assertEqual(
            rows,
            [
                {
                    "symbol": "600001",
                    "name": "首板样本",
                    "close": "11.00",
                    "previous_close": "10.00",
                    "high": "0",
                    "limit_up": "11.00",
                    "turnover_amount": 500_000_000,
                    "turnover_rate": "8.20",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
