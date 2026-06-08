import unittest

from bjcj.review.markdown_report import render_first_board_markdown


class MarkdownReportTest(unittest.TestCase):
    def test_renders_first_board_review_markdown(self):
        payload = {
            "trade_date": "2026-06-05",
            "history_available": False,
            "source": {
                "stock_pool_count": 5206,
                "quotes_fetched": 5206,
                "limit_candidate_count": 124,
                "intraday_fetched": 124,
                "next_limit_day_count": 74,
            },
            "stats": {
                "first_board_count": 74,
                "touched_first_board_count": 119,
                "broken_count": 45,
                "resealed_count": 33,
                "broken_rate": "0.38",
            },
            "first_boards": [
                {
                    "symbol": "600516",
                    "name": "方大炭素",
                    "turnover_amount": 751947918,
                    "turnover_rate": "3.23",
                    "first_limit_time": "09:37",
                    "last_limit_time": "15:00",
                    "open_limit_count": 0,
                    "strength_score": "85.00",
                    "risk_tags": [],
                }
            ],
            "broken_boards": [
                {
                    "symbol": "002585",
                    "name": "双星新材",
                    "turnover_amount": 3646255746,
                    "turnover_rate": "33.39",
                    "first_limit_time": "09:30",
                    "last_limit_time": "09:33",
                    "open_limit_count": 1,
                    "strength_score": "35.00",
                    "risk_tags": ["炸板 1 次", "炸板未封死"],
                }
            ],
            "watch_pool": [
                {
                    "symbol": "600516",
                    "name": "方大炭素",
                    "turnover_amount": 751947918,
                    "turnover_rate": "3.23",
                    "first_limit_time": "09:37",
                    "open_limit_count": 0,
                    "strength_score": "85.00",
                    "watch_reason": ["成交额达到 3 亿以上", "未分类题材出现 2 只以上首板", "封板强度进入前 30%"],
                }
            ],
        }

        markdown = render_first_board_markdown(payload, top_n=10)

        self.assertIn("# 2026-06-05 首板复盘", markdown)
        self.assertIn("- 首板数量：74", markdown)
        self.assertIn("- 炸板率：0.38", markdown)
        self.assertIn("历史连板状态：不可用", markdown)
        self.assertIn("| 600516 | 方大炭素 | 7.52 亿 | 3.23% | 09:37 | 0 | 85.00 |  |", markdown)
        self.assertIn("| 002585 | 双星新材 | 36.46 亿 | 33.39% | 09:30 | 1 | 35.00 | 炸板 1 次；炸板未封死 |", markdown)
        self.assertIn("| 600516 | 方大炭素 | 7.52 亿 | 09:37 | 0 | 85.00 | 成交额达到 3 亿以上；封板强度进入前 30% |", markdown)
        self.assertNotIn("未分类题材", markdown)


if __name__ == "__main__":
    unittest.main()
