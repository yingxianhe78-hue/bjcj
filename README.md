# 北京炒家 A 股助手

这是一个贴近“北京炒家”交易体系的 A 股复盘助手。当前第一阶段聚焦“首板复盘模块”：

- 自动识别当日首板。
- 计算首次封板时间、炸板次数、是否封死。
- 统计首板炸板率和回封数量。
- 按封板强度、成交额、题材联动生成次日观察池。

当前实现采用“计算核心”和“数据源适配”分离：

- `bjcj/review/core.py`: 首板复盘核心算法，不依赖外部网络。
- `bjcj/review/tencent_finance.py`: 腾讯财经实时行情适配骨架。
- `tests/test_first_board_review.py`: 核心行为测试。
- `docs/first-board-review-module.md`: 模块设计文档。
- `docs/tencent-finance-data-source.md`: 腾讯财经数据源接入说明。

## 运行测试

```powershell
python -m unittest tests.test_first_board_review
```

## 当前能力

核心算法已经支持：

- 主板 10%、创业板/科创板 20%、ST 5% 的涨停价计算。
- 从分时价格序列推导首封时间、最后封板时间、炸板次数、收盘是否封死。
- 通过上一交易日连板高度筛出首板，排除二板及以上。
- 生成首板列表、炸板统计和次日观察池。
- 从腾讯财经拉取指定股票的实时行情和当日分时数据。

## 下一步

腾讯财经真实数据已经接入到指定股票维度：

```powershell
python -c "from bjcj.review.tencent_finance import fetch_review_inputs; data=fetch_review_inputs(['600000','000001']); print([s.name for s in data.stocks]); print({k: v.close for k,v in data.quotes.items()}); print({k: len(v) for k,v in data.intraday.items()})"
```

返回的数据可以直接喂给 `generate_first_board_review`：

- `data.stocks`: 股票基础信息。
- `data.quotes`: 每只股票的收盘价、昨收、开盘、成交额、换手率。
- `data.intraday`: 每只股票的分钟分时价格。

## 拉取全 A 股票池

已支持通过腾讯实时行情接口批量探测沪深 A 股股票池：

```powershell
python scripts/fetch_a_share_pool.py
```

默认输出：

- `data/a_share_pool.json`
- `data/a_share_pool.csv`

股票池字段：

- `symbol`: 股票代码
- `name`: 股票名称
- `market`: `sh` 或 `sz`
- `is_st`: 是否 ST / *ST

当前全 A 股票池采用代码段候选 + 腾讯行情有效性过滤：

- 深市主板：`000001` 至 `003999`
- 创业板：`300001` 至 `301999`
- 沪市主板：`600000` 至 `605999`
- 科创板：`688000` 至 `689999`

后续建议：

1. 读取 `data/a_share_pool.json`。
2. 批量拉取全 A 当日实时/收盘行情。
3. 先按涨幅和涨停价初筛曾涨停候选。
4. 只对候选股拉取分时，降低请求量。
5. 调用 `generate_first_board_review` 生成首板复盘结果。

第一版可以先做收盘后离线复盘，等字段稳定后再扩展盘中监控。

## 扫描涨停候选

已支持执行首板复盘链路的第 1-3 步：

```powershell
python scripts/scan_limit_candidates.py
```

处理流程：

1. 读取 `data/a_share_pool.json`。
2. 批量拉取全 A 实时/收盘行情。
3. 剔除 ST。
4. 根据腾讯返回的日内最高价和涨停价筛出曾触及涨停候选。
5. 只对候选股拉取当日分钟分时。

默认输出：

- `data/candidates/latest_limit_candidates.json`
- `data/candidates/latest_intraday_summary.json`

最近一次本地扫描结果：

- 股票池：5206 只
- 行情：5206 只
- 曾触及涨停候选：124 只
- 候选分时：124 只

## 生成首板复盘

已支持执行首板复盘链路的第 4 步：

```powershell
python scripts/build_first_board_review.py --trade-date latest
```

处理流程：

1. 重新执行全 A 行情和曾触板候选扫描。
2. 拉取候选股完整分钟分时。
3. 根据分时识别首次封板时间、最后封板时间、炸板次数、是否封死。
4. 读取上一交易日连板高度文件 `data/limit_days/latest.json`。
5. 生成首板复盘 JSON。

默认输出：

- `data/reviews/latest_first_board_review.json`

最近一次本地复盘结果：

- 曾触及涨停候选：124 只
- 分时拉取：124 只
- 收盘封死首板候选：74 只
- 炸板未封：45 只
- 炸板率：0.38
- 次日观察池：30 只

注意：当前还没有上一交易日连板高度文件，所以 `history_available` 为 `false`。这意味着当前结果是“首板候选口径”，后续接入历史连板状态后，才能严格排除二板及以上。

## 维护连板状态

第 5 步已经接入历史连板状态。运行第 4 步脚本时会同时保存本交易日的收盘封死涨停状态：

```powershell
python scripts/build_first_board_review.py --trade-date latest
```

默认保存：

- `data/limit_days/latest.json`

保存口径：

- 只保存收盘封死涨停的股票。
- 如果上一交易日该股是 1 板，今天继续封死，则保存为 2。
- 如果今天未封死，则不进入下一交易日连板状态。
- 同一 `trade_date` 重复运行时，历史文件会被识别为“同日历史”，不会被当作上一交易日使用，避免把今天的涨停误判成昨天的连板。

最近一次本地保存：

- `trade_date`: `latest`
- 连板状态数量：74 只

下一次使用真实交易日时，建议传入明确日期：

```powershell
python scripts/build_first_board_review.py --trade-date 2026-06-05 --archive
```

这样后续交易日运行时，历史状态就能严格排除二板及以上，得到真正的首板。

如果要使用上一交易日连板状态，显式传入历史文件：

```powershell
python scripts/build_first_board_review.py --trade-date 2026-06-08 --archive --history data/limit_days/2026-06-05.json
```

## 生成 Markdown 复盘报告

第 6 步已经支持把 JSON 复盘结果渲染成适合人工阅读的 Markdown：

```powershell
python scripts/render_first_board_report.py
```

默认输入：

- `data/reviews/latest_first_board_review.json`

默认输出：

- `reports/latest_first_board_review.md`

报告包含：

- 市场概览
- 首板强度榜
- 炸板榜
- 次日观察池
- 历史连板状态提示

默认每个榜单展示 Top 20，可以通过 `--top-n` 调整：

```powershell
python scripts/render_first_board_report.py --top-n 50
```

按日期归档生成报告：

```powershell
python scripts/render_first_board_report.py --trade-date 2026-06-05
```

对应输出：

- `data/reviews/2026-06-05-first-board.json`
- `data/limit_days/2026-06-05.json`
- `reports/2026-06-05-first-board.md`

## 9:25 次日观察池盯盘

已支持读取最新复盘里的次日观察池，并在早盘拉腾讯实时行情做观察分层：

```powershell
python scripts/morning_watch_925.py
```

默认输入：

- `data/reviews/latest_first_board_review.json`

默认输出：

- `reports/morning_watch/latest_9_25_watch.md`

报告分层：

- `强观察`: 竞价或早盘明显超预期，接近涨停或高开较强。
- `正常观察`: 红盘或小幅高开，继续看承接。
- `降级`: 低开、走弱，或昨日炸板后没有转强。
- `风险`: 明显低于预期，只观察不追。

也可以按日期读取归档复盘：

```powershell
python scripts/morning_watch_925.py --trade-date 2026-06-05
```

已创建工作日 9:25 自动任务：`A股观察池 9:25 盯盘`。自动任务会运行盯盘脚本并汇总观察池分层，不输出买卖建议。
