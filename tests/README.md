# Test Suite — Trading Journal

This folder contains all tests for the Trading Journal app.
Tests are organised by what they test and marked by tier so you can run exactly what you need.

---

## How to Run

```bash
# Quick sanity check — run every time before starting work
pytest -m smoke

# After any code change
pytest -m core

# Before a release — includes live API connection
pytest -m live

# Everything except slow live tests
pytest -m "not live"

# Everything
pytest

# One file at a time
pytest tests/test_api_connection.py -v
pytest tests/test_fetch_data.py -v
pytest tests/test_fetch_symbols.py -v
```

---

## Test Tiers

| Marker | Purpose | Speed | When to run |
|--------|---------|-------|-------------|
| `smoke` | Does the bare minimum work? | Seconds | Every time |
| `core` | Does the logic produce correct output? | ~10 seconds | After any code change |
| `live` | Can we actually connect to cTrader? | ~15 seconds | Before a release |

---

## Test Inventory

### `test_api_connection.py` — cTrader API

| Test | Tier | What it does | Keep? |
|------|------|-------------|-------|
| `test_env_variables_exist` | smoke | Checks all 6 credentials are present in `.env` | ✅ Essential |
| `test_env_values_not_placeholder` | smoke | Checks credentials are not still the template defaults | ✅ Essential |
| `test_ctrader_api_importable` | smoke | Checks `ctrader-open-api` package is installed | ✅ Essential |
| `test_twisted_importable` | smoke | Checks `twisted` package is installed | ✅ Essential |
| `test_api_app_authentication` | live | Actually connects to cTrader and authenticates | ✅ Essential — this is a core functional test |

**Verdict:** Keep all 5. The live authentication test is the most important one — if this fails, nothing else in the app works.

---

### `test_fetch_data.py` — Trade Data Pipeline

| Test | Tier | What it does | Keep? |
|------|------|-------------|-------|
| `test_fetch_days_constant` | core | Checks `FETCH_DAYS` is a valid positive number | ⚠️ Low value — basic config check |
| `test_trades_csv_exists` | smoke | Checks `data/trades.csv` exists on disk | ✅ Keep — if this fails nothing loads |
| `test_trades_csv_has_required_columns` | core | Checks all 11 expected columns are present | ✅ Keep — schema drift would break the whole app |
| `test_trades_csv_not_empty` | core | Checks the file has at least 1 row | ⚠️ Borderline — only useful after a fresh fetch |
| `test_trades_csv_time_parseable` | core | Checks the time column parses as UTC datetime | ✅ Keep — this caused real bugs before |
| `test_trades_csv_pnl_numeric` | core | Checks P&L column is numeric not string | ✅ Keep — silent bug risk |
| `test_trades_csv_direction_values` | core | Checks direction is only BUY or SELL | ⚠️ Low value — unlikely to change |
| `test_trades_csv_has_closing_positions` | core | Checks there are closing positions in the data | ✅ Keep — app breaks if no closing positions |
| `test_trades_csv_positions_matchable` | core | Checks closing deals have matching opening deals | ✅ Keep — scenario logic depends on this |
| `test_sample_csv_loads_correctly` | core | Unit test: a minimal CSV loads and parses correctly | ✅ Keep — pure logic test, no file needed |
| `test_deduplication_on_deal_id` | core | Unit test: duplicate rows are removed correctly | ✅ Keep — incremental fetch depends on this |
| `test_incremental_merge_adds_new_rows` | core | Unit test: new rows are appended correctly | ✅ Keep — key incremental fetch logic |
| `test_no_duplicate_deals_after_overlap_merge` | core | Unit test: overlapping fetch doesn't create duplicates | ✅ Keep — real bug this prevents |

**Verdict:** Remove `test_fetch_days_constant` and `test_trades_csv_direction_values` — low value. Keep the rest.

---

### `test_fetch_symbols.py` — Symbol Name Mapping

| Test | Tier | What it does | Keep? |
|------|------|-------------|-------|
| `test_symbols_json_exists` | smoke | Checks `data/symbols.json` exists | ✅ Keep — app shows "ID:93" instead of "XAUEUR" if missing |
| `test_symbols_json_valid_json` | smoke | Checks it parses as valid JSON | ✅ Keep — silent failure risk |
| `test_symbols_json_not_empty` | core | Checks it has at least one entry | ⚠️ Low value |
| `test_symbols_json_keys_are_strings` | core | Checks all keys are strings | ❌ Remove — overly pedantic |
| `test_symbols_json_values_are_strings` | core | Checks all values are strings | ❌ Remove — overly pedantic |
| `test_symbols_json_keys_are_numeric_strings` | core | Checks all keys are numeric | ❌ Remove — overly pedantic |
| `test_known_traded_symbols_present` | core | Checks your 7 traded symbols are all in the file | ✅ Keep — directly functional |
| `test_known_symbol_names_correct` | core | Checks XAUEUR maps to "XAUEUR" not something else | ✅ Keep — directly functional |
| `test_traded_symbols_match_trades_csv` | core | Checks every symbol in trades.csv has a name | ✅ Keep — charts show wrong names if this fails |

**Verdict:** Remove the 3 structural/pedantic tests. Keep the 2 smoke tests and the 3 functional ones.

---

## What Is NOT Tested Yet

These are the higher-value functional tests that don't exist yet.
These are what you asked for — dashboard functionality, page loading, downloads.

| Test area | What it would check | Priority |
|-----------|-------------------|----------|
| Dashboard starts without errors | `python app.py` launches and responds at port 8050 | 🔴 High |
| Overview page loads | Hitting `/` returns HTTP 200 and contains expected content | 🔴 High |
| Scenarios page loads | Scenario table renders for a known date | 🔴 High |
| Journal page loads | Journal table renders with correct columns | 🔴 High |
| CSV download works | Clicking Download CSV returns a valid CSV file | 🟠 Medium |
| Floating P&L download | Returns a CSV with correct columns | 🟠 Medium |
| Scenario detection logic | `build_scenarios()` returns correct number of scenarios for a known date | 🔴 High |
| Exposure DD calculation | `calc_exposure_drawdown()` returns expected value for known data | 🔴 High |
| Candle fetch returns data | `fetch_candles_sync()` returns a non-empty DataFrame | 🟠 Medium |

These will go in new files: `test_dashboard.py` and `test_app_logic.py`

---

## Recommended Test Set (stripped down)

If you want to run only the tests that directly test functionality:

```bash
# Functional tests only — API, data pipeline, symbol mapping
pytest tests/ -m "smoke or core" \
  --deselect tests/test_fetch_data.py::TestConfig::test_fetch_days_constant \
  --deselect tests/test_fetch_data.py::TestTradesCsvStructure::test_trades_csv_direction_values \
  --deselect tests/test_fetch_symbols.py::TestSymbolsFile::test_symbols_json_not_empty \
  --deselect tests/test_fetch_symbols.py::TestSymbolsFile::test_symbols_json_keys_are_strings \
  --deselect tests/test_fetch_symbols.py::TestSymbolsFile::test_symbols_json_values_are_strings \
  --deselect tests/test_fetch_symbols.py::TestSymbolsFile::test_symbols_json_keys_are_numeric_strings
```

Or once you tell me which ones to remove, I can update the test files to just delete them outright.
