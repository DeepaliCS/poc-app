# Test Suite — Trading Journal

**5 test files** covering API connection, data pipeline, symbol mapping, core dashboard logic, and golden tests using real trade data.

> **Note:** Some tests appear in both class and standalone form due to how the files were structured across sessions. This does not affect correctness — pytest runs them all and they all test the same logic.

---

## How to Run

```bash
# Every day before starting work — runs in seconds
pytest -m smoke

# After any code change — includes golden tests
pytest -m core

# Before a release — includes live cTrader connection
pytest -m live

# Everything except slow live tests
pytest -m "not live"

# Everything
pytest

# One file only
pytest tests/test_golden.py -v
pytest tests/test_app_logic.py -v
pytest tests/test_api_connection.py -v
pytest tests/test_fetch_data.py -v
pytest tests/test_fetch_symbols.py -v
```

---

## Test Files

| File | What it covers | Unique tests |
|------|---------------|-------|
| `test_api_connection.py` | cTrader credentials and API connectivity | 5 |
| `test_fetch_data.py` | trades.csv structure, data quality, merge logic | 13 |
| `test_fetch_symbols.py` | symbols.json validity and symbol lookup | 6 |
| `test_app_logic.py` | Core dashboard functions with dummy data | 23 |
| `test_golden.py` | **Real data** — known date with exact expected output | 22 |

---

## Golden Tests — How They Work

Golden tests in `test_golden.py` use a real date from your actual `trades.csv`
and verify the exact expected output. This catches bugs that dummy data cannot.

**Preferred golden date:** `2026-01-13`
Pre-computed expected values for this date:
- Total P&L: **£110.78**
- Scenarios: **6**
- Trades: **19**
- Win rate: **89.5%**
- Symbol: **XAUEUR**

**Dynamic fallback:** If `2026-01-13` is not in your CSV, the tests automatically
pick the best available date with 8+ trades and 2+ scenarios and adjust assertions
to match that date's actual values.

---

## Full Test Inventory

### `test_api_connection.py` — 5 tests

| Test | Tier | Keep? | What it catches |
|------|------|-------|----------------|
| `test_env_variables_exist` | smoke | ✅ | App cannot start without credentials |
| `test_env_values_not_placeholder` | smoke | ✅ | Guards against template defaults |
| `test_ctrader_api_importable` | smoke | ✅ | Package not installed |
| `test_twisted_importable` | smoke | ✅ | Package not installed |
| `test_api_app_authentication` | live | ✅ | **Most important** — actual live connection |

---

### `test_fetch_data.py` — 13 tests

| Test | Tier | Keep? | What it catches |
|------|------|-------|----------------|
| `TestConfig::test_fetch_days_constant` | core | ❌ Remove | Config check, not functionality |
| `TestTradesCsvStructure::test_trades_csv_exists` | smoke | ✅ | App breaks entirely if missing |
| `TestTradesCsvStructure::test_trades_csv_has_required_columns` | core | ✅ | Schema drift breaks all pages |
| `TestTradesCsvStructure::test_trades_csv_not_empty` | core | ⚠️ Borderline | Only useful after fresh fetch |
| `TestTradesCsvStructure::test_trades_csv_time_parseable` | core | ✅ | Caused real bugs before |
| `TestTradesCsvStructure::test_trades_csv_pnl_numeric` | core | ✅ | Silent failure if column becomes string |
| `TestTradesCsvStructure::test_trades_csv_direction_values` | core | ❌ Remove | Unlikely to change, low value |
| `TestTradesCsvStructure::test_trades_csv_has_closing_positions` | core | ✅ | App shows nothing if missing |
| `TestTradesCsvStructure::test_trades_csv_positions_matchable` | core | ✅ | Scenario logic breaks if no match |
| `TestCacheLogic::test_sample_csv_loads_correctly` | core | ✅ | Pure unit test — no file needed |
| `TestCacheLogic::test_deduplication_on_deal_id` | core | ✅ | Incremental fetch depends on this |
| `TestCacheLogic::test_incremental_merge_adds_new_rows` | core | ✅ | Key fetch logic |
| `TestCacheLogic::test_no_duplicate_deals_after_overlap_merge` | core | ✅ | Prevents data corruption |

---

### `test_fetch_symbols.py` — 6 tests

| Test | Tier | Keep? | What it catches |
|------|------|-------|----------------|
| `TestSymbolsFile::test_symbols_json_exists` | smoke | ✅ | App shows "ID:93" without this |
| `TestSymbolsFile::test_symbols_json_valid_json` | smoke | ✅ | Silent crash risk |
| `TestSymbolsFile::test_symbols_json_not_empty` | core | ❌ Remove | Low value |
| `TestSymbolLookup::test_known_traded_symbols_present` | core | ✅ | Your 7 symbols must resolve |
| `TestSymbolLookup::test_known_symbol_names_correct` | core | ✅ | Correct name mapping |
| `TestSymbolLookup::test_traded_symbols_match_trades_csv` | core | ✅ | Every traded symbol has a name |

---

### `test_app_logic.py` — 23 tests (dummy data)

| Test | Tier | Keep? | What it catches |
|------|------|-------|----------------|
| `TestGetSymbolName::test_known_symbol_returns_name` | smoke | ✅ | Symbol lookup broken |
| `TestGetSymbolName::test_unknown_symbol_returns_fallback` | smoke | ✅ | Crash on unknown symbol |
| `TestGetSymbolName::test_symbol_id_as_int_works` | core | ✅ | Type mismatch int vs str |
| `TestGetSymbolName::test_empty_symbols_dict_returns_fallback` | core | ✅ | Crash when file missing |
| `TestBuildScenarios::test_empty_date_returns_empty_dataframe` | core | ✅ | Crash on no-trade days |
| `TestBuildScenarios::test_single_trade_creates_one_scenario` | core | ✅ | Scenario detection broken |
| `TestBuildScenarios::test_two_trades_close_together_same_scenario` | core | ✅ | 10-min gap threshold changed |
| `TestBuildScenarios::test_two_trades_far_apart_different_scenarios` | core | ✅ | 10-min gap threshold changed |
| `TestBuildScenarios::test_scenario_pnl_sums_correctly` | core | ✅ | P&L aggregation bug |
| `TestBuildScenarios::test_scenario_has_required_columns` | core | ✅ | Column rename breaks Scenarios page |
| `TestBuildScenarios::test_scenario_buys_sells_count_correct` | core | ✅ | Direction counting wrong |
| `TestCalcExposureDrawdown::test_empty_day_returns_none` | core | ✅ | Crash on empty days |
| `TestCalcExposureDrawdown::test_profitable_trade_returns_zero` | core | ✅ | False DD shown on winning days |
| `TestCalcExposureDrawdown::test_losing_trade_has_negative_exposure` | core | ✅ | DD calculation broken entirely |
| `TestCalcExposureDrawdown::test_exposure_dd_not_worse_than_sum_of_losses` | core | ✅ | Runaway negative calculation |
| `TestBuildDailySummary::test_returns_dataframe` | core | ✅ | Journal page crashes |
| `TestBuildDailySummary::test_one_trading_day_produces_one_row` | core | ✅ | Row duplication bug |
| `TestBuildDailySummary::test_daily_summary_has_required_columns` | core | ✅ | Column rename breaks Journal page |
| `TestBuildDailySummary::test_pnl_sum_is_correct` | core | ✅ | P&L total wrong in journal |
| `TestBuildDailySummary::test_win_rate_calculation` | core | ✅ | Win rate formula changed |
| `TestBuildFloatingPnl::test_empty_date_returns_empty_dataframe` | core | ✅ | Download crash on empty date |
| `TestBuildFloatingPnl::test_returns_dataframe_with_correct_columns` | core | ✅ | Column rename breaks CSV download |
| `TestBuildFloatingPnl::test_float_pnl_zero_at_entry` | core | ✅ | Float logic wrong at entry point |

---

### `test_golden.py` — 22 tests (real data)

| Test | Tier | Keep? | What it catches |
|------|------|-------|----------------|
| `TestGoldenPrerequisites::test_trades_csv_exists` | smoke | ✅ | Nothing works without this |
| `TestGoldenPrerequisites::test_symbols_json_exists` | smoke | ✅ | Names show as IDs without this |
| `TestGoldenPrerequisites::test_preferred_date_in_csv` | smoke | ✅ | Warns if golden date dropped out |
| `TestGoldenScenarios::test_scenarios_returns_dataframe` | core | ✅ | Function crashes on real data |
| `TestGoldenScenarios::test_scenarios_not_empty` | core | ✅ | No scenarios detected |
| `TestGoldenScenarios::test_scenario_count_matches_expected` | core | ✅ | Gap logic changed — **high value** |
| `TestGoldenScenarios::test_total_pnl_matches_expected` | core | ✅ | P&L wrong on real data — **high value** |
| `TestGoldenScenarios::test_pnl_per_scenario_sums_to_total` | core | ✅ | Double counting bug |
| `TestGoldenScenarios::test_trade_count_matches_expected` | core | ✅ | Trades missed or duplicated |
| `TestGoldenScenarios::test_win_rate_in_valid_range` | core | ✅ | Win rate out of 0–100 bounds |
| `TestGoldenScenarios::test_preferred_date_win_rate` | core | ✅ | Win rate calculation wrong |
| `TestGoldenScenarios::test_scenario_instruments_populated` | core | ✅ | Instrument names missing |
| `TestGoldenScenarios::test_exposure_dd_not_positive` | core | ✅ | Exposure DD sign flipped |
| `TestGoldenDailySummary::test_summary_contains_golden_date` | core | ✅ | Date missing from journal |
| `TestGoldenDailySummary::test_golden_date_pnl_correct` | core | ✅ | Journal P&L wrong — **high value** |
| `TestGoldenDailySummary::test_golden_date_trade_count_correct` | core | ✅ | Trade count wrong in journal |
| `TestGoldenDailySummary::test_golden_date_win_rate_correct` | core | ✅ | Win rate wrong in journal |
| `TestGoldenFloatingPnl::test_floating_pnl_returns_data` | core | ✅ | Function crashes or returns empty |
| `TestGoldenFloatingPnl::test_floating_pnl_all_positions_covered` | core | ✅ | Positions silently dropped |
| `TestGoldenFloatingPnl::test_floating_pnl_has_required_columns` | core | ✅ | Column rename breaks CSV download |
| `TestGoldenFloatingPnl::test_floating_pnl_row_count_reasonable` | core | ✅ | Output too sparse |
| `TestGoldenFloatingPnl::test_floating_pnl_closed_pnl_matches_csv` | core | ✅ | Closed P&L doesn't match source data |

---

## Known Issue — Duplicate Test Functions

Some test files contain functions both inside classes (e.g. `TestBuildScenarios::test_single_trade_creates_one_scenario`) and as standalone functions (e.g. `test_single_trade_creates_one_scenario`). This happened because the files were built iteratively across sessions. The tests are identical — pytest runs both, which inflates the count but does not affect correctness.

**To fix this cleanly:** Remove the standalone functions at the bottom of `test_fetch_data.py`, `test_fetch_symbols.py`, `test_app_logic.py`, and `test_golden.py`, keeping only the class-based versions. This is a tidy-up task with no functional impact.

---

## What Is Not Tested Yet

| Area | Priority | Why it matters |
|------|---------|---------------|
| Dashboard starts without import errors | 🔴 High | Catches broken refactors instantly |
| Scenarios page renders in browser | 🔴 High | Page could crash despite logic passing |
| Journal page renders correct row count | 🔴 High | Same reason |
| CSV download produces parseable file | 🟠 Medium | Silent empty file risk |
| Multi-symbol exposure DD | 🟠 Medium | Only single-symbol in dummy tests |
| Session detection at timezone boundaries | 🟡 Low | Edge case |
