# 腾讯财经数据源接入说明

## 接入原则

腾讯财经只作为数据源适配层，不直接污染首板复盘核心算法。

推荐数据流：

```text
腾讯财经接口
  -> 字段解析
  -> 标准数据模型
  -> 首板复盘核心算法
  -> Markdown / CSV / 页面输出
```

这样做的好处是：即使后续增加东方财富、同花顺问财或本地题材库，核心复盘口径不用重写。

## 当前适配层

文件位置：

```text
bjcj/review/tencent_finance.py
```

当前提供：

- `encode_tencent_symbol(symbol)`: 转换腾讯行情代码，例如 `600000` -> `sh600000`。
- `a_share_candidate_symbols()`: 生成沪深 A 股候选代码段。
- `realtime_quote_url(symbols)`: 生成腾讯实时行情 URL。
- `minute_quote_url(symbol)`: 生成腾讯当日分时 URL。
- `fetch_a_share_stock_pool()`: 批量探测并过滤活跃沪深 A 股股票池。
- `fetch_realtime_quotes(symbols)`: 拉取多只股票实时行情。
- `fetch_minute_bars(symbol)`: 拉取单只股票当日分时。
- `fetch_review_inputs(symbols)`: 拉取复盘核心所需的标准输入。
- `parse_realtime_quote(line)`: 解析单行腾讯实时行情。
- `parse_realtime_quotes(text)`: 解析多行腾讯实时行情。
- `parse_minute_bars(text, symbol)`: 解析腾讯分时 JSON。
- `quotes_to_daily_quotes(quotes)`: 转换为核心层 `DailyQuote`。

## 已验证接口

截至当前开发验证，以下接口已经能在本地请求成功：

```text
https://qt.gtimg.cn/q=sh600000,sz000001
https://web.ifzq.gtimg.cn/appstock/app/minute/query?code=sh600000
```

本地验证命令：

```powershell
python -c "from bjcj.review.tencent_finance import fetch_review_inputs; data=fetch_review_inputs(['600000','000001']); print([s.name for s in data.stocks]); print({k: v.close for k,v in data.quotes.items()}); print({k: len(v) for k,v in data.intraday.items()})"
```

验证结果显示可以拿到：

- 股票名称。
- 最新/收盘价、昨收、开盘、成交额、换手率。
- 当日分钟分时数据。

## 全 A 股票池

当前没有依赖腾讯的全 A 列表页，而是采用更稳的探测方式：

1. 生成沪深 A 股候选代码段。
2. 按批次请求 `https://qt.gtimg.cn/q=...`。
3. 跳过腾讯返回的空行和 `v_pv_none_match` 控制行。
4. 保留 `stock_type` 以 `GP-A` 开头，且昨收和涨跌停字段不是退市无效标记的股票。

运行命令：

```powershell
python scripts/fetch_a_share_pool.py
```

当前落盘文件：

- `data/a_share_pool.json`
- `data/a_share_pool.csv`

最近一次本地拉取数量：5206 只。

## 需要继续验证的接口

### 行业/题材补充数据

用途：

- 补充行业字段。
- 补充题材概念。
- 辅助判断当日主线和题材联动。

### 实时/收盘行情

用途：

- `previous_close`
- `close`
- `open`
- `turnover_amount`
- `turnover_rate`

### 分时行情

用途：

- `first_limit_time`
- `last_limit_time`
- `open_limit_count`
- `is_limit_up_close`

首板模块最依赖分时数据。只要分时价格序列稳定，就可以推导首封、炸板和回封。

## 可能缺口

腾讯财经可能不能稳定提供：

- 精确封单金额。
- 涨停原因。
- 同花顺式题材概念。
- 高质量连板高度字段。

初版处理方式：

- 封单金额先不作为硬条件。
- 题材先用行业兜底。
- 连板高度通过历史复盘结果递推。
- 强度评分先采用“封板时间 + 收盘封死 + 炸板次数 + 成交额 + 题材联动”。

## 后续开发建议

先完成一个交易日的离线链路：

1. 收盘后获取全 A 行情。
2. 初筛涨停或曾涨停个股。
3. 拉取候选股分时。
4. 生成首板复盘结果。
5. 保存每日结果，供次日观察池和历史回测使用。

当前第 1-3 步已经可以通过脚本执行：

```powershell
python scripts/scan_limit_candidates.py
```

默认读取：

- `data/a_share_pool.json`

默认输出：

- `data/candidates/latest_limit_candidates.json`
- `data/candidates/latest_intraday_summary.json`

最近一次本地扫描：5206 只股票行情，筛出 124 只曾触及涨停候选，并拉取 124 只候选分时。

第四步脚本：

```powershell
python scripts/build_first_board_review.py --trade-date latest
```

默认输出：

- `data/reviews/latest_first_board_review.json`

最近一次本地复盘：

- 曾触及涨停候选：124 只
- 收盘封死首板候选：74 只
- 炸板未封：45 只
- 炸板率：0.38

当前 `history_available` 为 `false`，表示还没有上一交易日连板高度文件，结果暂按“首次运行首板候选口径”处理。

按日期归档运行：

```powershell
python scripts/build_first_board_review.py --trade-date 2026-06-05 --archive
python scripts/render_first_board_report.py --trade-date 2026-06-05
```

对应输出：

- `data/reviews/2026-06-05-first-board.json`
- `data/limit_days/2026-06-05.json`
- `reports/2026-06-05-first-board.md`

如果要接入上一交易日连板状态：

```powershell
python scripts/build_first_board_review.py --trade-date 2026-06-08 --archive --history data/limit_days/2026-06-05.json
```

第五步已经接入连板状态维护。运行复盘脚本后会保存：

- `data/limit_days/latest.json`

文件结构：

```json
{
  "trade_date": "latest",
  "count": 74,
  "limit_days": {
    "000068": 1
  }
}
```

同一 `trade_date` 重复运行时，系统不会把这个文件当作上一交易日历史使用；换到下一交易日后，文件里的 `limit_days` 会参与首板过滤。

第六步已经支持将复盘 JSON 渲染为 Markdown：

```powershell
python scripts/render_first_board_report.py
```

默认输出：

- `reports/latest_first_board_review.md`

报告会展示市场概览、首板强度榜、炸板榜和次日观察池。由于题材数据尚未接入，报告会过滤“未分类题材”这类临时入池原因，避免干扰人工复盘。
