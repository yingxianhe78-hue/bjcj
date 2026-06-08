import unittest
from decimal import Decimal

from bjcj.review.core import (
    DailyQuote,
    IntradayBar,
    ReviewConfig,
    StockMeta,
    generate_first_board_review,
    limit_up_price,
)
from bjcj.review.export import stock_pool_to_csv_text, stock_pool_to_jsonable
from bjcj.review.tencent_finance import (
    a_share_candidate_symbols,
    encode_tencent_symbol,
    fetch_a_share_stock_pool,
    fetch_realtime_quotes,
    fetch_review_inputs,
    is_active_a_share_quote,
    minute_quote_url,
    parse_minute_bars,
    parse_realtime_quote,
    parse_realtime_quotes,
    quotes_to_daily_quotes,
    realtime_quote_url,
)


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self.text.encode("gbk")


class FakeOpener:
    def __init__(self, text):
        self.text = text
        self.urls = []

    def __call__(self, request, timeout):
        self.urls.append(request.full_url)
        return FakeResponse(self.text)


class UrlMapOpener:
    def __init__(self, responses):
        self.responses = responses
        self.urls = []

    def __call__(self, request, timeout):
        self.urls.append(request.full_url)
        return FakeResponse(self.responses[request.full_url])


class LimitUpPriceTest(unittest.TestCase):
    def test_main_board_limit_up_price_uses_ten_percent_tick_rounding(self):
        price = limit_up_price(Decimal("10.03"), "600000", is_st=False)

        self.assertEqual(price, Decimal("11.03"))

    def test_chinext_and_star_market_use_twenty_percent(self):
        self.assertEqual(limit_up_price(Decimal("10.00"), "300001", is_st=False), Decimal("12.00"))
        self.assertEqual(limit_up_price(Decimal("10.00"), "688001", is_st=False), Decimal("12.00"))

    def test_st_stock_uses_five_percent(self):
        self.assertEqual(limit_up_price(Decimal("10.00"), "600000", is_st=True), Decimal("10.50"))


class IntradayBoardReviewTest(unittest.TestCase):
    def test_generates_first_board_review_from_intraday_bars(self):
        stocks = [
            StockMeta(symbol="600001", name="强势首板", industry="机器人"),
            StockMeta(symbol="002001", name="弱回封", industry="机器人"),
            StockMeta(symbol="300001", name="创业首板", industry="AI"),
            StockMeta(symbol="600002", name="二连板", industry="机器人"),
            StockMeta(symbol="600003", name="炸板未封", industry="消费"),
        ]
        quotes = {
            "600001": DailyQuote("600001", Decimal("10.00"), Decimal("11.00"), Decimal("9.90"), 500_000_000, Decimal("8.2")),
            "002001": DailyQuote("002001", Decimal("10.00"), Decimal("11.00"), Decimal("9.95"), 350_000_000, Decimal("6.1")),
            "300001": DailyQuote("300001", Decimal("10.00"), Decimal("12.00"), Decimal("10.10"), 420_000_000, Decimal("10.5")),
            "600002": DailyQuote("600002", Decimal("10.00"), Decimal("11.00"), Decimal("10.10"), 800_000_000, Decimal("12.0")),
            "600003": DailyQuote("600003", Decimal("10.00"), Decimal("10.70"), Decimal("9.80"), 300_000_000, Decimal("9.0")),
        }
        intraday = {
            "600001": [
                IntradayBar("09:31", Decimal("10.20")),
                IntradayBar("09:45", Decimal("11.00")),
                IntradayBar("15:00", Decimal("11.00")),
            ],
            "002001": [
                IntradayBar("10:10", Decimal("11.00")),
                IntradayBar("10:35", Decimal("10.88")),
                IntradayBar("14:40", Decimal("11.00")),
                IntradayBar("15:00", Decimal("11.00")),
            ],
            "300001": [
                IntradayBar("13:05", Decimal("12.00")),
                IntradayBar("15:00", Decimal("12.00")),
            ],
            "600002": [
                IntradayBar("09:35", Decimal("11.00")),
                IntradayBar("15:00", Decimal("11.00")),
            ],
            "600003": [
                IntradayBar("10:00", Decimal("11.00")),
                IntradayBar("13:20", Decimal("10.70")),
                IntradayBar("15:00", Decimal("10.70")),
            ],
        }
        previous_limit_days = {
            "600001": 0,
            "002001": 0,
            "300001": 0,
            "600002": 1,
            "600003": 0,
        }

        review = generate_first_board_review(
            trade_date="2026-06-05",
            stocks=stocks,
            quotes=quotes,
            intraday=intraday,
            previous_limit_days=previous_limit_days,
            config=ReviewConfig(min_turnover_amount=300_000_000),
        )

        self.assertEqual([item.symbol for item in review.first_boards], ["600001", "300001", "002001"])
        self.assertEqual(review.stats.first_board_count, 3)
        self.assertEqual(review.stats.touched_first_board_count, 4)
        self.assertEqual(review.stats.broken_count, 1)
        self.assertEqual(review.stats.resealed_count, 1)
        self.assertEqual(review.stats.broken_rate, Decimal("0.25"))

        weak = next(item for item in review.first_boards if item.symbol == "002001")
        self.assertEqual(weak.open_limit_count, 1)
        self.assertIn("炸板 1 次", weak.risk_tags)

        watch_symbols = [item.symbol for item in review.watch_pool]
        self.assertEqual(watch_symbols, ["600001", "300001", "002001"])
        self.assertIn("封板强度进入前 30%", review.watch_pool[0].watch_reason)


class TencentFinanceAdapterTest(unittest.TestCase):
    def test_encodes_tencent_market_prefix(self):
        self.assertEqual(encode_tencent_symbol("600000"), "sh600000")
        self.assertEqual(encode_tencent_symbol("688001"), "sh688001")
        self.assertEqual(encode_tencent_symbol("000001"), "sz000001")
        self.assertEqual(encode_tencent_symbol("300001"), "sz300001")

    def test_builds_realtime_and_minute_urls(self):
        self.assertEqual(realtime_quote_url(["600000", "000001"]), "https://qt.gtimg.cn/q=sh600000,sz000001")
        self.assertEqual(
            minute_quote_url("600000"),
            "https://web.ifzq.gtimg.cn/appstock/app/minute/query?code=sh600000",
        )

    def test_parses_realtime_quote_line(self):
        line = 'v_sh600000="1~浦发银行~600000~8.80~8.70~8.72~1000~500~500~8.79~100~8.78~200~8.77~300~8.76~400~8.75~500~8.80~120~8.81~130~8.82~140~8.83~150~8.84~160~~20260605150000~0.10~1.15~8.90~8.60~8.80/1000/880000~1000~88~1.20~5.00~~8.90~8.60~1.15~1000000000~1200000000~1.00~9.57~7.83~";'

        quote = parse_realtime_quote(line)

        self.assertEqual(quote.symbol, "600000")
        self.assertEqual(quote.name, "浦发银行")
        self.assertEqual(quote.close, Decimal("8.80"))
        self.assertEqual(quote.previous_close, Decimal("8.70"))
        self.assertEqual(quote.turnover_amount, 880000)
        self.assertEqual(quote.turnover_rate, Decimal("1.20"))
        self.assertEqual(quote.stock_type, "GP-A")
        self.assertEqual(quote.limit_up, Decimal("9.57"))
        self.assertEqual(quote.limit_down, Decimal("7.83"))
        self.assertTrue(is_active_a_share_quote(quote))

    def test_skips_blank_realtime_quote_lines(self):
        text = '\n'.join(
            [
                'v_sz999999="";',
                'v_pv_none_match="1";',
                'v_sh600000="1~浦发银行~600000~8.80~8.70~8.72~1000~500~500~8.79~100~8.78~200~8.77~300~8.76~400~8.75~500~8.80~120~8.81~130~8.82~140~8.83~150~8.84~160~~20260605150000~0.10~1.15~8.90~8.60~8.80/1000/880000~1000~88~1.20~5.00~~8.90~8.60~1.15~1000000000~1200000000~1.00~9.57~7.83~";',
            ]
        )

        quotes = parse_realtime_quotes(text)

        self.assertEqual([quote.symbol for quote in quotes], ["600000"])

    def test_filters_inactive_a_share_quotes(self):
        retired = parse_realtime_quote('v_sh600001="1~邯郸钢铁~600001~5.29~5.29~0.00~0~0~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~~20260605090000~0.00~0.00~0.00~0.00~5.29/0/0~0~0~0.00~-673.65~D~0.00~0.00~0.00~148.99~148.99~1.20~-1~-1~0.00~0~0.00~55.62~24.86~~~~0.0000~0.0000~0~ ~GP-A~0.00~0.00~0.00~-0.18~-0.08~~~0.00~0.00~0.00~2816456569~2816456569~~0.00~2816456569~~~0.00~0.00~~CNY~0~~0.00~0~";')

        self.assertFalse(is_active_a_share_quote(retired))

    def test_keeps_chinext_and_star_market_stock_types(self):
        chinext = parse_realtime_quote('v_sz300001="1~特锐德~300001~41.00~40.99~41.00~1000~500~500~41.00~100~40.99~200~40.98~300~40.97~400~40.96~500~41.00~120~41.01~130~41.02~140~41.03~150~41.04~160~~20260605150000~0.01~0.02~41.50~40.50~41.00/1000/41000000~1000~4100~1.20~5.00~~41.50~40.50~0.02~1000000000~1200000000~1.00~49.19~32.79~1.00~0~0~0~0~~~0~0~0~0~ ~GP-A-CYB~";')
        star = parse_realtime_quote('v_sh688001="1~华兴源创~688001~75.20~75.19~75.20~1000~500~500~75.20~100~75.19~200~75.18~300~75.17~400~75.16~500~75.20~120~75.21~130~75.22~140~75.23~150~75.24~160~~20260605150000~0.01~0.01~76.00~74.00~75.20/1000/75200000~1000~7520~1.20~5.00~~76.00~74.00~0.01~1000000000~1200000000~1.00~90.23~60.15~1.00~0~0~0~0~~~0~0~0~0~ ~GP-A-KCB~";')

        self.assertTrue(is_active_a_share_quote(chinext))
        self.assertTrue(is_active_a_share_quote(star))

    def test_fetches_realtime_quotes_with_injected_opener(self):
        text = '\n'.join(
            [
                'v_sh600000="1~浦发银行~600000~8.80~8.70~8.72~1000~500~500~8.79~100~8.78~200~8.77~300~8.76~400~8.75~500~8.80~120~8.81~130~8.82~140~8.83~150~8.84~160~~20260605150000~0.10~1.15~8.90~8.60~8.80/1000/880000~1000~88~1.20~5.00~~8.90~8.60~1.15~1000000000~1200000000~1.00~9.57~7.83~";',
                'v_sz000001="1~平安银行~000001~10.10~10.00~10.05~1000~500~500~10.09~100~10.08~200~10.07~300~10.06~400~10.05~500~10.10~120~10.11~130~10.12~140~10.13~150~10.14~160~~20260605150000~0.10~1.00~10.30~9.90~10.10/1000/1010000~1000~101~2.30~5.00~~10.30~9.90~1.00~1000000000~1200000000~1.00~11.00~9.00~";',
            ]
        )
        opener = FakeOpener(text)

        quotes = fetch_realtime_quotes(["600000", "000001"], opener=opener)

        self.assertEqual([quote.symbol for quote in quotes], ["600000", "000001"])
        self.assertEqual(opener.urls, ["https://qt.gtimg.cn/q=sh600000,sz000001"])

    def test_converts_tencent_quotes_to_daily_quote_map(self):
        line = 'v_sh600000="1~浦发银行~600000~8.80~8.70~8.72~1000~500~500~8.79~100~8.78~200~8.77~300~8.76~400~8.75~500~8.80~120~8.81~130~8.82~140~8.83~150~8.84~160~~20260605150000~0.10~1.15~8.90~8.60~8.80/1000/880000~1000~88~1.20~5.00~~8.90~8.60~1.15~1000000000~1200000000~1.00~9.57~7.83~";'

        quote_map = quotes_to_daily_quotes([parse_realtime_quote(line)])

        self.assertEqual(quote_map["600000"], DailyQuote("600000", Decimal("8.70"), Decimal("8.80"), Decimal("8.72"), 880000, Decimal("1.20")))

    def test_parses_minute_bars_from_tencent_json(self):
        text = """
        {
          "code": 0,
          "data": {
            "sh600000": {
              "data": {
                "date": "20260605",
                "data": ["0930 8.70 100", "0931 8.80 200", "1500 8.90 300"]
              }
            }
          }
        }
        """

        bars = parse_minute_bars(text, "600000")

        self.assertEqual(
            bars,
            [
                IntradayBar("09:30", Decimal("8.70")),
                IntradayBar("09:31", Decimal("8.80")),
                IntradayBar("15:00", Decimal("8.90")),
            ],
        )

    def test_fetches_review_inputs_for_core_review(self):
        realtime_url = "https://qt.gtimg.cn/q=sh600000,sz000001"
        sh_minute_url = "https://web.ifzq.gtimg.cn/appstock/app/minute/query?code=sh600000"
        sz_minute_url = "https://web.ifzq.gtimg.cn/appstock/app/minute/query?code=sz000001"
        opener = UrlMapOpener(
            {
                realtime_url: '\n'.join(
                    [
                        'v_sh600000="1~浦发银行~600000~8.80~8.70~8.72~1000~500~500~8.79~100~8.78~200~8.77~300~8.76~400~8.75~500~8.80~120~8.81~130~8.82~140~8.83~150~8.84~160~~20260605150000~0.10~1.15~8.90~8.60~8.80/1000/880000~1000~88~1.20~5.00~~8.90~8.60~1.15~1000000000~1200000000~1.00~9.57~7.83~";',
                        'v_sz000001="1~平安银行~000001~10.10~10.00~10.05~1000~500~500~10.09~100~10.08~200~10.07~300~10.06~400~10.05~500~10.10~120~10.11~130~10.12~140~10.13~150~10.14~160~~20260605150000~0.10~1.00~10.30~9.90~10.10/1000/1010000~1000~101~2.30~5.00~~10.30~9.90~1.00~1000000000~1200000000~1.00~11.00~9.00~";',
                    ]
                ),
                sh_minute_url: '{"data":{"sh600000":{"data":{"data":["0930 8.72 100","1500 8.80 200"]}}}}',
                sz_minute_url: '{"data":{"sz000001":{"data":{"data":["0930 10.05 100","1500 10.10 200"]}}}}',
            }
        )

        inputs = fetch_review_inputs(["600000", "000001"], opener=opener)

        self.assertEqual([stock.symbol for stock in inputs.stocks], ["600000", "000001"])
        self.assertEqual(inputs.stocks[0].name, "浦发银行")
        self.assertEqual(inputs.quotes["000001"].close, Decimal("10.10"))
        self.assertEqual(inputs.intraday["600000"][-1], IntradayBar("15:00", Decimal("8.80")))
        self.assertEqual(opener.urls, [realtime_url, sh_minute_url, sz_minute_url])

    def test_generates_a_share_candidate_symbols(self):
        symbols = a_share_candidate_symbols()

        self.assertIn("000001", symbols)
        self.assertIn("002001", symbols)
        self.assertIn("300001", symbols)
        self.assertIn("301001", symbols)
        self.assertIn("600000", symbols)
        self.assertIn("605001", symbols)
        self.assertIn("688001", symbols)
        self.assertNotIn("200001", symbols)
        self.assertNotIn("900001", symbols)

    def test_fetches_a_share_stock_pool_from_candidates(self):
        url = "https://qt.gtimg.cn/q=sh600000,sh600001,sz000001"
        opener = UrlMapOpener(
            {
                url: '\n'.join(
                    [
                        'v_sh600000="1~浦发银行~600000~8.80~8.70~8.72~1000~500~500~8.79~100~8.78~200~8.77~300~8.76~400~8.75~500~8.80~120~8.81~130~8.82~140~8.83~150~8.84~160~~20260605150000~0.10~1.15~8.90~8.60~8.80/1000/880000~1000~88~1.20~5.00~~8.90~8.60~1.15~1000000000~1200000000~1.00~9.57~7.83~1.01~-28525~9.28~4.35~6.22~~~0.25~69208.9681~0.0000~0~ ~GP-A~";',
                        'v_sh600001="1~邯郸钢铁~600001~5.29~5.29~0.00~0~0~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~~20260605090000~0.00~0.00~0.00~0.00~5.29/0/0~0~0~0.00~-673.65~D~0.00~0.00~0.00~148.99~148.99~1.20~-1~-1~0.00~0~0.00~55.62~24.86~~~~0.0000~0.0000~0~ ~GP-A~";',
                        'v_sz000001="1~平安银行~000001~10.10~10.00~10.05~1000~500~500~10.09~100~10.08~200~10.07~300~10.06~400~10.05~500~10.10~120~10.11~130~10.12~140~10.13~150~10.14~160~~20260605150000~0.10~1.00~10.30~9.90~10.10/1000/1010000~1000~101~2.30~5.00~~10.30~9.90~1.00~11.00~9.00~1.00~0~0~0~0~~~0~0~0~0~ ~GP-A~";',
                    ]
                )
            }
        )

        stocks = fetch_a_share_stock_pool(
            candidates=["600000", "600001", "000001"],
            batch_size=3,
            opener=opener,
        )

        self.assertEqual([stock.symbol for stock in stocks], ["000001", "600000"])
        self.assertEqual([stock.name for stock in stocks], ["平安银行", "浦发银行"])


class StockPoolExportTest(unittest.TestCase):
    def test_converts_stock_pool_to_jsonable_rows(self):
        stocks = [
            StockMeta(symbol="000001", name="平安银行", market="sz"),
            StockMeta(symbol="000004", name="*ST国华", is_st=True, market="sz"),
        ]

        rows = stock_pool_to_jsonable(stocks)

        self.assertEqual(
            rows,
            [
                {"symbol": "000001", "name": "平安银行", "market": "sz", "is_st": False},
                {"symbol": "000004", "name": "*ST国华", "market": "sz", "is_st": True},
            ],
        )

    def test_converts_stock_pool_to_csv_text(self):
        stocks = [
            StockMeta(symbol="000001", name="平安银行", market="sz"),
            StockMeta(symbol="000004", name="*ST国华", is_st=True, market="sz"),
        ]

        text = stock_pool_to_csv_text(stocks)

        self.assertEqual(
            text,
            "symbol,name,market,is_st\r\n000001,平安银行,sz,false\r\n000004,*ST国华,sz,true\r\n",
        )


if __name__ == "__main__":
    unittest.main()
