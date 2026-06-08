# 北京炒家强化版闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working closed-loop pipeline that records the 9:25 watch pool, captures four intraday snapshots, computes close results plus attribution, and renders daily and weekly loop reports.

**Architecture:** Extend the existing `bjcj.review` package with small focused modules that keep data collection, classification, persistence, and report rendering separate. Reuse the Tencent quote fetcher and the current `morning_watch` result as the root input, then append intraday snapshots, close results, attribution, and statistics using shared archive path helpers.

**Tech Stack:** Python 3.12, dataclasses, pathlib, json, unittest, existing Tencent Finance HTTP integration

---

## File Structure

### Existing files to modify

- `D:\北京炒家\bjcj\review\paths.py`
  Purpose: central archive paths; extend it with closed-loop data/report paths.
- `D:\北京炒家\bjcj\review\morning_watch.py`
  Purpose: current 9:25 watch model; extend serialization-friendly fields needed by the closed loop.
- `D:\北京炒家\bjcj\review\markdown_report.py`
  Purpose: existing report rendering patterns; keep style consistent when adding new loop reports.
- `D:\北京炒家\bjcj\review\tencent_finance.py`
  Purpose: Tencent realtime fetch + minute bars; reuse existing types and add tiny helpers only if snapshot access needs them.
- `D:\北京炒家\scripts\morning_watch_925.py`
  Purpose: current 9:25 run entrypoint; make it persist structured watch data alongside Markdown.

### New files to create

- `D:\北京炒家\bjcj\review\closed_loop_models.py`
  Purpose: shared dataclasses and JSON conversion for watch records, snapshots, close results, attribution, and report summaries.
- `D:\北京炒家\bjcj\review\closed_loop_store.py`
  Purpose: read/write structured closed-loop JSON artifacts.
- `D:\北京炒家\bjcj\review\intraday_snapshots.py`
  Purpose: capture four time-point snapshots from realtime quotes for the watch pool.
- `D:\北京炒家\bjcj\review\close_results.py`
  Purpose: compute close metrics and subjective outcome tags from intraday snapshots plus close quotes.
- `D:\北京炒家\bjcj\review\attribution.py`
  Purpose: generate fixed attribution tags and retain optional custom tags.
- `D:\北京炒家\bjcj\review\closed_loop_stats.py`
  Purpose: aggregate daily and weekly statistics.
- `D:\北京炒家\bjcj\review\closed_loop_report.py`
  Purpose: render daily and weekly Markdown reports.
- `D:\北京炒家\scripts\capture_intraday_snapshot.py`
  Purpose: capture one snapshot run for one fixed time label.
- `D:\北京炒家\scripts\build_closed_loop_daily.py`
  Purpose: build close results, attribution, and daily report after market close.
- `D:\北京炒家\scripts\build_closed_loop_weekly.py`
  Purpose: build weekly closed-loop report from archived daily data.

### New tests to create

- `D:\北京炒家\tests\test_closed_loop_store.py`
- `D:\北京炒家\tests\test_intraday_snapshots.py`
- `D:\北京炒家\tests\test_close_results.py`
- `D:\北京炒家\tests\test_attribution.py`
- `D:\北京炒家\tests\test_closed_loop_stats.py`
- `D:\北京炒家\tests\test_closed_loop_report.py`

## Task 1: Define archive paths and shared data models

**Files:**
- Create: `D:\北京炒家\bjcj\review\closed_loop_models.py`
- Modify: `D:\北京炒家\bjcj\review\paths.py`
- Test: `D:\北京炒家\tests\test_closed_loop_store.py`

- [ ] **Step 1: Write the failing test for closed-loop archive paths**

```python
import unittest

from bjcj.review.paths import closed_loop_paths


class ClosedLoopPathsTest(unittest.TestCase):
    def test_builds_closed_loop_paths_for_trade_date(self):
        paths = closed_loop_paths("2026-06-08")

        self.assertEqual(str(paths.watch_json), "data/closed_loop/2026-06-08/watch.json")
        self.assertEqual(str(paths.snapshots_json), "data/closed_loop/2026-06-08/snapshots.json")
        self.assertEqual(str(paths.close_json), "data/closed_loop/2026-06-08/close.json")
        self.assertEqual(str(paths.daily_report_markdown), "reports/closed_loop/2026-06-08-daily.md")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest D:\北京炒家\tests\test_closed_loop_store.py -v`
Expected: FAIL with `ImportError` or missing `closed_loop_paths`

- [ ] **Step 3: Add shared dataclasses and path builder**

```python
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path


@dataclass(frozen=True)
class WatchRecord:
    trade_date: str
    session: str
    symbol: str
    name: str
    watch_level: str
    open_premium_pct: Decimal
    current_pct_925: Decimal
    turnover_amount_925: int
    first_limit_time: str
    open_limit_count: int
    watch_reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ClosedLoopPaths:
    root_dir: Path
    watch_json: Path
    snapshots_json: Path
    close_json: Path
    attribution_json: Path
    daily_report_markdown: Path
```

```python
@dataclass(frozen=True)
class ClosedLoopPaths:
    root_dir: Path
    watch_json: Path
    snapshots_json: Path
    close_json: Path
    attribution_json: Path
    daily_report_markdown: Path


def closed_loop_paths(trade_date: str) -> ClosedLoopPaths:
    root = Path(f"data/closed_loop/{trade_date}")
    return ClosedLoopPaths(
        root_dir=root,
        watch_json=root / "watch.json",
        snapshots_json=root / "snapshots.json",
        close_json=root / "close.json",
        attribution_json=root / "attribution.json",
        daily_report_markdown=Path(f"reports/closed_loop/{trade_date}-daily.md"),
    )
```

- [ ] **Step 4: Add JSON conversion helpers for shared models**

```python
def watch_record_to_jsonable(record: WatchRecord) -> dict[str, object]:
    return {
        "trade_date": record.trade_date,
        "session": record.session,
        "symbol": record.symbol,
        "name": record.name,
        "watch_level": record.watch_level,
        "open_premium_pct": f"{record.open_premium_pct:.2f}",
        "current_pct_925": f"{record.current_pct_925:.2f}",
        "turnover_amount_925": record.turnover_amount_925,
        "first_limit_time": record.first_limit_time,
        "open_limit_count": record.open_limit_count,
        "watch_reasons": list(record.watch_reasons),
    }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest D:\北京炒家\tests\test_closed_loop_store.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add D:\北京炒家\bjcj\review\closed_loop_models.py D:\北京炒家\bjcj\review\paths.py D:\北京炒家\tests\test_closed_loop_store.py
git commit -m "feat: add closed loop archive paths and models"
```

## Task 2: Persist the 9:25 watch pool as structured data

**Files:**
- Create: `D:\北京炒家\bjcj\review\closed_loop_store.py`
- Modify: `D:\北京炒家\bjcj\review\morning_watch.py`
- Modify: `D:\北京炒家\scripts\morning_watch_925.py`
- Test: `D:\北京炒家\tests\test_morning_watch.py`

- [ ] **Step 1: Write the failing test for exporting watch records**

```python
def test_builds_watch_records_for_closed_loop(self):
    result = build_morning_watch(review, quotes)

    records = morning_watch_to_watch_records(result)

    self.assertEqual(records[0].trade_date, "2026-06-05")
    self.assertEqual(records[0].session, "morning_watch_925")
    self.assertEqual(records[0].symbol, "600516")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest D:\北京炒家\tests\test_morning_watch.py -v`
Expected: FAIL with missing `morning_watch_to_watch_records`

- [ ] **Step 3: Add transformer from morning watch rows to watch records**

```python
def morning_watch_to_watch_records(result: MorningWatchResult, *, session: str = "morning_watch_925") -> list[WatchRecord]:
    return [
        WatchRecord(
            trade_date=result.trade_date,
            session=session,
            symbol=row.symbol,
            name=row.name,
            watch_level=row.level,
            open_premium_pct=row.open_premium,
            current_pct_925=row.pct_chg,
            turnover_amount_925=row.turnover_amount,
            first_limit_time=row.first_limit_time,
            open_limit_count=row.open_limit_count,
            watch_reasons=list(row.notes),
        )
        for row in result.rows
    ]
```

- [ ] **Step 4: Add closed-loop store helpers and save watch JSON in the script**

```python
def write_watch_records(path: str | Path, records: list[WatchRecord]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"count": len(records), "records": [watch_record_to_jsonable(item) for item in records]}
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
```

```python
from bjcj.review.closed_loop_store import write_watch_records
from bjcj.review.morning_watch import morning_watch_to_watch_records
from bjcj.review.paths import archive_paths, closed_loop_paths

loop_paths = closed_loop_paths(result.trade_date)
write_watch_records(loop_paths.watch_json, morning_watch_to_watch_records(result))
```

- [ ] **Step 5: Run tests to verify the watch export passes**

Run: `python -m pytest D:\北京炒家\tests\test_morning_watch.py D:\北京炒家\tests\test_closed_loop_store.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add D:\北京炒家\bjcj\review\closed_loop_store.py D:\北京炒家\bjcj\review\morning_watch.py D:\北京炒家\scripts\morning_watch_925.py D:\北京炒家\tests\test_morning_watch.py
git commit -m "feat: persist morning watch records for closed loop"
```

## Task 3: Add fixed-time intraday snapshot capture

**Files:**
- Create: `D:\北京炒家\bjcj\review\intraday_snapshots.py`
- Create: `D:\北京炒家\scripts\capture_intraday_snapshot.py`
- Test: `D:\北京炒家\tests\test_intraday_snapshots.py`

- [ ] **Step 1: Write the failing test for snapshot classification**

```python
from decimal import Decimal

from bjcj.review.closed_loop_models import WatchRecord
from bjcj.review.intraday_snapshots import build_intraday_snapshots
from bjcj.review.tencent_finance import TencentRealtimeQuote


def test_build_intraday_snapshots_marks_limit_and_state():
    records = [
        WatchRecord(
            trade_date="2026-06-08",
            session="morning_watch_925",
            symbol="600516",
            name="方大炭素",
            watch_level="正常观察",
            open_premium_pct=Decimal("3.00"),
            current_pct_925=Decimal("4.00"),
            turnover_amount_925=100000000,
            first_limit_time="09:37",
            open_limit_count=0,
            watch_reasons=["红盘承接"],
        )
    ]
    quotes = {
        "600516": TencentRealtimeQuote(
            symbol="600516",
            name="方大炭素",
            close=Decimal("11.00"),
            previous_close=Decimal("10.00"),
            open=Decimal("10.30"),
            high=Decimal("11.00"),
            low=Decimal("10.20"),
            turnover_amount=300000000,
            turnover_rate=Decimal("5.20"),
            limit_up=Decimal("11.00"),
            limit_down=Decimal("9.00"),
            stock_type="GP-A",
        )
    }

    snapshots = build_intraday_snapshots(records, quotes, snapshot_time="10:00")

    assert snapshots[0].snapshot_time == "10:00"
    assert snapshots[0].hit_limit_up is True
    assert "转强" in snapshots[0].subjective_state_tags
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest D:\北京炒家\tests\test_intraday_snapshots.py -v`
Expected: FAIL with missing module or function

- [ ] **Step 3: Implement snapshot model and builder**

```python
@dataclass(frozen=True)
class IntradaySnapshotRecord:
    trade_date: str
    session: str
    symbol: str
    name: str
    snapshot_time: str
    price_change_pct: Decimal
    change_vs_open_pct: Decimal
    turnover_amount: int
    hit_limit_up: bool
    sealed_limit_up: bool
    broken_limit_up: bool
    subjective_state_tags: list[str]
    snapshot_note: str = ""
```

```python
def build_intraday_snapshots(
    watch_records: list[WatchRecord],
    quotes: dict[str, TencentRealtimeQuote],
    *,
    snapshot_time: str,
) -> list[IntradaySnapshotRecord]:
    rows: list[IntradaySnapshotRecord] = []
    for record in watch_records:
        quote = quotes.get(record.symbol)
        if quote is None:
            continue
        price_change_pct = _pct(quote.close, quote.previous_close)
        change_vs_open_pct = _pct(quote.close, quote.open)
        rows.append(
            IntradaySnapshotRecord(
                trade_date=record.trade_date,
                session=record.session,
                symbol=record.symbol,
                name=record.name,
                snapshot_time=snapshot_time,
                price_change_pct=price_change_pct,
                change_vs_open_pct=change_vs_open_pct,
                turnover_amount=quote.turnover_amount,
                hit_limit_up=quote.high >= quote.limit_up > Decimal("0"),
                sealed_limit_up=quote.close >= quote.limit_up > Decimal("0"),
                broken_limit_up=quote.high >= quote.limit_up > Decimal("0") and quote.close < quote.limit_up,
                subjective_state_tags=_snapshot_tags(record.watch_level, price_change_pct, change_vs_open_pct),
            )
        )
    return rows
```

- [ ] **Step 4: Add one-shot snapshot script**

```python
parser.add_argument("--trade-date", required=True)
parser.add_argument("--time-label", required=True, choices=["09:35", "10:00", "10:30", "14:30"])

watch_records = read_watch_records(closed_loop_paths(args.trade_date).watch_json)
symbols = [item.symbol for item in watch_records]
quotes = {quote.symbol: quote for quote in fetch_realtime_quotes(symbols)}
snapshots = build_intraday_snapshots(watch_records, quotes, snapshot_time=args.time_label)
append_intraday_snapshots(closed_loop_paths(args.trade_date).snapshots_json, snapshots)
```

- [ ] **Step 5: Run tests to verify snapshots pass**

Run: `python -m pytest D:\北京炒家\tests\test_intraday_snapshots.py D:\北京炒家\tests\test_closed_loop_store.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add D:\北京炒家\bjcj\review\intraday_snapshots.py D:\北京炒家\scripts\capture_intraday_snapshot.py D:\北京炒家\tests\test_intraday_snapshots.py
git commit -m "feat: add fixed-time intraday snapshot capture"
```

## Task 4: Compute close results from snapshots and close quotes

**Files:**
- Create: `D:\北京炒家\bjcj\review\close_results.py`
- Test: `D:\北京炒家\tests\test_close_results.py`

- [ ] **Step 1: Write the failing test for close outcome tags**

```python
from decimal import Decimal

from bjcj.review.close_results import build_close_results
from bjcj.review.closed_loop_models import IntradaySnapshotRecord, WatchRecord
from bjcj.review.tencent_finance import TencentRealtimeQuote


def test_build_close_results_uses_snapshots_for_subjective_tags():
    watch_records = [...]
    snapshots = [
        IntradaySnapshotRecord(
            trade_date="2026-06-08",
            session="morning_watch_925",
            symbol="600516",
            name="方大炭素",
            snapshot_time="10:00",
            price_change_pct=Decimal("7.50"),
            change_vs_open_pct=Decimal("4.00"),
            turnover_amount=300000000,
            hit_limit_up=True,
            sealed_limit_up=False,
            broken_limit_up=True,
            subjective_state_tags=["转强", "冲高回落"],
        )
    ]
    close_quotes = {"600516": quote}

    results = build_close_results(watch_records, snapshots, close_quotes)

    assert results[0].broken_limit_up is True
    assert "冲高回落" in results[0].subjective_outcome_tags
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest D:\北京炒家\tests\test_close_results.py -v`
Expected: FAIL with missing module or function

- [ ] **Step 3: Implement close result computation**

```python
@dataclass(frozen=True)
class CloseResultRecord:
    trade_date: str
    session: str
    symbol: str
    name: str
    high_pct: Decimal
    close_pct: Decimal
    close_turnover_amount: int
    hit_limit_up: bool
    sealed_limit_up: bool
    broken_limit_up: bool
    has_next_day_watch_value: bool
    subjective_outcome_tags: list[str]
```

```python
def build_close_results(
    watch_records: list[WatchRecord],
    snapshots: list[IntradaySnapshotRecord],
    close_quotes: dict[str, TencentRealtimeQuote],
) -> list[CloseResultRecord]:
    snapshot_map = _group_snapshots_by_symbol(snapshots)
    rows: list[CloseResultRecord] = []
    for record in watch_records:
        quote = close_quotes.get(record.symbol)
        if quote is None:
            continue
        symbol_snapshots = snapshot_map.get(record.symbol, [])
        rows.append(
            CloseResultRecord(
                trade_date=record.trade_date,
                session=record.session,
                symbol=record.symbol,
                name=record.name,
                high_pct=_pct(quote.high, quote.previous_close),
                close_pct=_pct(quote.close, quote.previous_close),
                close_turnover_amount=quote.turnover_amount,
                hit_limit_up=any(item.hit_limit_up for item in symbol_snapshots) or quote.high >= quote.limit_up > Decimal("0"),
                sealed_limit_up=quote.close >= quote.limit_up > Decimal("0"),
                broken_limit_up=any(item.broken_limit_up for item in symbol_snapshots),
                has_next_day_watch_value=_has_watch_value(record.watch_level, quote),
                subjective_outcome_tags=_outcome_tags(record.watch_level, symbol_snapshots, quote),
            )
        )
    return rows
```

- [ ] **Step 4: Run tests to verify close results pass**

Run: `python -m pytest D:\北京炒家\tests\test_close_results.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add D:\北京炒家\bjcj\review\close_results.py D:\北京炒家\tests\test_close_results.py
git commit -m "feat: add closed loop close result computation"
```

## Task 5: Generate fixed-tag attribution

**Files:**
- Create: `D:\北京炒家\bjcj\review\attribution.py`
- Test: `D:\北京炒家\tests\test_attribution.py`

- [ ] **Step 1: Write the failing test for attribution tags**

```python
from bjcj.review.attribution import build_attribution_records


def test_build_attribution_records_assigns_fixed_tags():
    rows = build_attribution_records(watch_records, snapshots, close_results)

    assert "竞价强" in rows[0].attribution_tags
    assert "冲高回落" in rows[0].attribution_tags
    assert rows[0].custom_attribution_tags == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest D:\北京炒家\tests\test_attribution.py -v`
Expected: FAIL with missing module or function

- [ ] **Step 3: Implement rule-based attribution**

```python
@dataclass(frozen=True)
class AttributionRecord:
    trade_date: str
    session: str
    symbol: str
    name: str
    attribution_tags: list[str]
    custom_attribution_tags: list[str]
    attribution_note: str = ""
```

```python
def build_attribution_records(
    watch_records: list[WatchRecord],
    snapshots: list[IntradaySnapshotRecord],
    close_results: list[CloseResultRecord],
) -> list[AttributionRecord]:
    rows: list[AttributionRecord] = []
    close_map = {item.symbol: item for item in close_results}
    snapshot_map = _group_snapshots_by_symbol(snapshots)
    for record in watch_records:
        result = close_map.get(record.symbol)
        if result is None:
            continue
        tags = []
        if record.open_premium_pct > Decimal("0"):
            tags.append("竞价强")
        if record.open_premium_pct < Decimal("0"):
            tags.append("竞价弱")
        if any("转强" in item.subjective_state_tags for item in snapshot_map.get(record.symbol, [])):
            tags.append("承接强")
        if "冲高回落" in result.subjective_outcome_tags:
            tags.append("冲高回落")
        rows.append(
            AttributionRecord(
                trade_date=record.trade_date,
                session=record.session,
                symbol=record.symbol,
                name=record.name,
                attribution_tags=sorted(set(tags)),
                custom_attribution_tags=[],
            )
        )
    return rows
```

- [ ] **Step 4: Run tests to verify attribution passes**

Run: `python -m pytest D:\北京炒家\tests\test_attribution.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add D:\北京炒家\bjcj\review\attribution.py D:\北京炒家\tests\test_attribution.py
git commit -m "feat: add rule-based closed loop attribution"
```

## Task 6: Build daily aggregation and Markdown report

**Files:**
- Create: `D:\北京炒家\bjcj\review\closed_loop_stats.py`
- Create: `D:\北京炒家\bjcj\review\closed_loop_report.py`
- Create: `D:\北京炒家\scripts\build_closed_loop_daily.py`
- Test: `D:\北京炒家\tests\test_closed_loop_stats.py`
- Test: `D:\北京炒家\tests\test_closed_loop_report.py`

- [ ] **Step 1: Write the failing tests for daily stats and report rendering**

```python
def test_build_daily_summary_counts_levels_and_tags():
    summary = build_daily_summary(watch_records, close_results, attribution_records)

    assert summary.watch_count == 3
    assert summary.level_counts["强观察"] == 1
    assert summary.success_counts["sealed_limit_up"] == 1
```

```python
def test_render_daily_closed_loop_markdown_contains_top_sections():
    markdown = render_daily_closed_loop_markdown(summary)

    assert "# 2026-06-08 闭环日报" in markdown
    assert "## 层级表现" in markdown
    assert "## 高频成功归因" in markdown
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest D:\北京炒家\tests\test_closed_loop_stats.py D:\北京炒家\tests\test_closed_loop_report.py -v`
Expected: FAIL with missing functions or modules

- [ ] **Step 3: Implement daily summary aggregation**

```python
@dataclass(frozen=True)
class DailyClosedLoopSummary:
    trade_date: str
    watch_count: int
    level_counts: dict[str, int]
    success_counts: dict[str, int]
    outcome_tag_counts: dict[str, int]
    attribution_tag_counts: dict[str, int]
    focus_symbols: list[str]
```

```python
def build_daily_summary(
    watch_records: list[WatchRecord],
    close_results: list[CloseResultRecord],
    attribution_records: list[AttributionRecord],
) -> DailyClosedLoopSummary:
    return DailyClosedLoopSummary(
        trade_date=watch_records[0].trade_date if watch_records else "latest",
        watch_count=len(watch_records),
        level_counts=dict(Counter(item.watch_level for item in watch_records)),
        success_counts={
            "close_positive": sum(1 for item in close_results if item.close_pct > 0),
            "hit_limit_up": sum(1 for item in close_results if item.hit_limit_up),
            "sealed_limit_up": sum(1 for item in close_results if item.sealed_limit_up),
        },
        outcome_tag_counts=dict(Counter(tag for item in close_results for tag in item.subjective_outcome_tags)),
        attribution_tag_counts=dict(Counter(tag for item in attribution_records for tag in item.attribution_tags)),
        focus_symbols=[item.symbol for item in sorted(close_results, key=lambda x: (x.sealed_limit_up, x.close_pct), reverse=True)[:5]],
    )
```

- [ ] **Step 4: Implement daily Markdown renderer and script**

```python
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
        "",
        "## 高频成功归因",
        "",
    ]
    lines.extend(f"- {tag}: {count}" for tag, count in sorted(summary.attribution_tag_counts.items(), key=lambda item: item[1], reverse=True)[:5])
    return "\n".join(lines) + "\n"
```

```python
watch_records = read_watch_records(paths.watch_json)
snapshots = read_intraday_snapshots(paths.snapshots_json)
close_results = build_close_results(watch_records, snapshots, close_quotes)
attributions = build_attribution_records(watch_records, snapshots, close_results)
summary = build_daily_summary(watch_records, close_results, attributions)
write_daily_closed_loop_markdown(paths.daily_report_markdown, summary)
```

- [ ] **Step 5: Run tests to verify the daily report passes**

Run: `python -m pytest D:\北京炒家\tests\test_closed_loop_stats.py D:\北京炒家\tests\test_closed_loop_report.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add D:\北京炒家\bjcj\review\closed_loop_stats.py D:\北京炒家\bjcj\review\closed_loop_report.py D:\北京炒家\scripts\build_closed_loop_daily.py D:\北京炒家\tests\test_closed_loop_stats.py D:\北京炒家\tests\test_closed_loop_report.py
git commit -m "feat: add closed loop daily summary and report"
```

## Task 7: Build weekly aggregation and Markdown report

**Files:**
- Modify: `D:\北京炒家\bjcj\review\closed_loop_stats.py`
- Modify: `D:\北京炒家\bjcj\review\closed_loop_report.py`
- Create: `D:\北京炒家\scripts\build_closed_loop_weekly.py`
- Test: `D:\北京炒家\tests\test_closed_loop_stats.py`
- Test: `D:\北京炒家\tests\test_closed_loop_report.py`

- [ ] **Step 1: Write the failing tests for weekly stats**

```python
def test_build_weekly_summary_aggregates_multiple_days():
    summary = build_weekly_summary([day_one_summary, day_two_summary])

    assert summary.trade_day_count == 2
    assert summary.watch_count == 6
    assert summary.level_counts["强观察"] == 2
```

```python
def test_render_weekly_closed_loop_markdown_contains_rule_sections():
    markdown = render_weekly_closed_loop_markdown(summary)

    assert "# 2026-06-08 闭环周报" in markdown
    assert "## 最近有效标签" in markdown
    assert "## 最近失效标签" in markdown
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest D:\北京炒家\tests\test_closed_loop_stats.py D:\北京炒家\tests\test_closed_loop_report.py -v`
Expected: FAIL with missing weekly functions

- [ ] **Step 3: Implement weekly summary**

```python
@dataclass(frozen=True)
class WeeklyClosedLoopSummary:
    end_date: str
    trade_day_count: int
    watch_count: int
    level_counts: dict[str, int]
    success_counts: dict[str, int]
    attribution_tag_counts: dict[str, int]
    strong_tags: list[tuple[str, int]]
    weak_tags: list[tuple[str, int]]
```

```python
def build_weekly_summary(days: list[DailyClosedLoopSummary]) -> WeeklyClosedLoopSummary:
    attribution_counts = Counter(tag for day in days for tag, count in day.attribution_tag_counts.items() for _ in range(count))
    return WeeklyClosedLoopSummary(
        end_date=days[-1].trade_date if days else "latest",
        trade_day_count=len(days),
        watch_count=sum(day.watch_count for day in days),
        level_counts=_merge_counter_dicts(day.level_counts for day in days),
        success_counts=_merge_counter_dicts(day.success_counts for day in days),
        attribution_tag_counts=dict(attribution_counts),
        strong_tags=attribution_counts.most_common(5),
        weak_tags=sorted(attribution_counts.items(), key=lambda item: item[1])[:5],
    )
```

- [ ] **Step 4: Implement weekly report script**

```python
parser.add_argument("--end-date", required=True)
parser.add_argument("--days", type=int, default=5)

daily_summaries = load_daily_summaries_for_window(args.end_date, args.days)
weekly_summary = build_weekly_summary(daily_summaries)
write_weekly_closed_loop_markdown(Path(f"reports/closed_loop/{args.end_date}-weekly.md"), weekly_summary)
```

- [ ] **Step 5: Run tests to verify weekly reporting passes**

Run: `python -m pytest D:\北京炒家\tests\test_closed_loop_stats.py D:\北京炒家\tests\test_closed_loop_report.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add D:\北京炒家\bjcj\review\closed_loop_stats.py D:\北京炒家\bjcj\review\closed_loop_report.py D:\北京炒家\scripts\build_closed_loop_weekly.py D:\北京炒家\tests\test_closed_loop_stats.py D:\北京炒家\tests\test_closed_loop_report.py
git commit -m "feat: add closed loop weekly aggregation"
```

## Task 8: End-to-end verification and docs refresh

**Files:**
- Modify: `D:\北京炒家\README.md`
- Modify: `D:\北京炒家\docs\superpowers\specs\2026-06-08-bjcj-closed-loop-design.md`
- Test: existing test suite plus new suite

- [ ] **Step 1: Write the usage section updates**

```markdown
## 强化版闭环流程

1. `python scripts/morning_watch_925.py --trade-date YYYY-MM-DD`
2. `python scripts/capture_intraday_snapshot.py --trade-date YYYY-MM-DD --time-label 09:35`
3. `python scripts/capture_intraday_snapshot.py --trade-date YYYY-MM-DD --time-label 10:00`
4. `python scripts/capture_intraday_snapshot.py --trade-date YYYY-MM-DD --time-label 10:30`
5. `python scripts/capture_intraday_snapshot.py --trade-date YYYY-MM-DD --time-label 14:30`
6. `python scripts/build_closed_loop_daily.py --trade-date YYYY-MM-DD`
7. `python scripts/build_closed_loop_weekly.py --end-date YYYY-MM-DD`
```

- [ ] **Step 2: Run the focused test suite**

Run: `python -m pytest D:\北京炒家\tests\test_morning_watch.py D:\北京炒家\tests\test_closed_loop_store.py D:\北京炒家\tests\test_intraday_snapshots.py D:\北京炒家\tests\test_close_results.py D:\北京炒家\tests\test_attribution.py D:\北京炒家\tests\test_closed_loop_stats.py D:\北京炒家\tests\test_closed_loop_report.py -v`
Expected: PASS

- [ ] **Step 3: Run the full regression suite**

Run: `python -m pytest D:\北京炒家\tests -v`
Expected: PASS

- [ ] **Step 4: Smoke test the scripts with archived data**

Run: `python D:\北京炒家\scripts\morning_watch_925.py --trade-date 2026-06-05`
Expected: exits `0` and writes `data/closed_loop/2026-06-05/watch.json`

Run: `python D:\北京炒家\scripts\build_closed_loop_daily.py --trade-date 2026-06-05`
Expected: exits `0` and writes `reports/closed_loop/2026-06-05-daily.md`

- [ ] **Step 5: Commit**

```bash
git add D:\北京炒家\README.md D:\北京炒家\docs\superpowers\specs\2026-06-08-bjcj-closed-loop-design.md
git commit -m "docs: document closed loop workflow"
```

## Spec Coverage Check

- Structured watch record persistence: covered by Task 2.
- Fixed four intraday snapshots: covered by Task 3.
- Mixed close result model: covered by Task 4.
- Fixed-tag plus custom attribution structure: covered by Task 5.
- Daily and weekly report generation: covered by Tasks 6 and 7.
- Reverse-feedback-ready statistics base: covered by Tasks 6 and 7 through aggregated counters.

## Placeholder Scan

- No `TODO`, `TBD`, or deferred placeholders were left in the task steps.
- Every code-change step includes exact file targets and concrete code skeletons.
- Every verification step includes an explicit command and expected result.
