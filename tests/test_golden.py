# tests/test_golden.py
# Golden tests — use a real known date from trades.csv with exact expected outputs.
#
# These tests catch bugs that dummy data cannot:
#   - Calculation logic changes that produce wrong numbers on real data
#   - Edge cases only present in real market data
#   - Regressions after refactoring
#
# The test date is chosen dynamically — it picks a day from your actual
# trades.csv that has enough data (8+ trades, 2+ scenarios) to be meaningful.
# If that date disappears from the CSV, it falls back gracefully.
#
# Pre-computed expected values for 2026-01-13 (19 trades, 6 scenarios, XAUEUR):
#   Total P&L:  £110.78
#   Scenarios:  6
#   Win rate:   89.5%
#   Net P&L:    £107.32
#
# Run: pytest tests/test_golden.py -v
# Run smoke only: pytest tests/test_golden.py -m smoke -v

import sys
import json
import pytest
import pandas as pd
from pathlib import Path
from datetime import timezone, timedelta

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

DATA_FILE    = BASE_DIR / "data" / "trades.csv"
SYMBOLS_FILE = BASE_DIR / "data" / "symbols.json"

# ── Golden date selection ─────────────────────────────────────

PREFERRED_DATE = "2026-01-13"   # pre-computed expected values below
MIN_TRADES     = 8              # minimum trades for a date to be usable
MIN_SCENARIOS  = 2              # minimum scenarios for a date to be usable


def pick_golden_date():
    """
    Pick the best date to run golden tests against.
    Prefers PREFERRED_DATE if it exists in the CSV with enough data.
    Falls back to the best available date if not.
    Returns (date_str, df_day) or raises pytest.skip if no suitable date found.
    """
    if not DATA_FILE.exists():
        pytest.skip("data/trades.csv not found — run fetch_data.py first")

    df = pd.read_csv(DATA_FILE)
    df["time"] = pd.to_datetime(df["time"], format="ISO8601", utc=True)
    closings = df[df["is_closing"] == True].copy()
    closings["date_str"] = closings["time"].dt.strftime("%Y-%m-%d")

    # Try preferred date first
    preferred = closings[closings["date_str"] == PREFERRED_DATE]
    if len(preferred) >= MIN_TRADES:
        gaps = preferred.sort_values("time")["time"].diff().dt.total_seconds().fillna(9999) / 60
        n_scenarios = (gaps > 10).sum() + 1
        if n_scenarios >= MIN_SCENARIOS:
            return PREFERRED_DATE, df

    # Fall back to best available date
    day_counts = closings.groupby("date_str").size()
    candidates = day_counts[day_counts >= MIN_TRADES].index.tolist()

    for date_str in sorted(candidates, reverse=True):
        day = closings[closings["date_str"] == date_str].sort_values("time")
        gaps = day["time"].diff().dt.total_seconds().fillna(9999) / 60
        n_scenarios = (gaps > 10).sum() + 1
        if n_scenarios >= MIN_SCENARIOS:
            return date_str, df

    pytest.skip(
        f"No date found with {MIN_TRADES}+ trades and {MIN_SCENARIOS}+ scenarios. "
        "Run fetch_data.py to populate trades.csv."
    )


# ── Fixtures ──────────────────────────────────────────────────

@pytest.fixture(scope="module")
def golden_date_and_df():
    """Shared fixture — loads real data once for all golden tests."""
    return pick_golden_date()


@pytest.fixture(scope="module")
def golden_scenarios(golden_date_and_df):
    """Runs build_scenarios() on the golden date — shared across tests."""
    import app as app_module
    date_str, _ = golden_date_and_df
    return app_module.build_scenarios(date_str), date_str


@pytest.fixture(scope="module")
def golden_daily_summary():
    """Runs build_daily_summary() — shared across tests."""
    import app as app_module
    if not DATA_FILE.exists():
        pytest.skip("trades.csv not found")
    return app_module.build_daily_summary()


# ── Prerequisites ─────────────────────────────────────────────

class TestGoldenPrerequisites:
    """Check everything needed for golden tests is in place."""

    @pytest.mark.smoke
    def test_trades_csv_exists(self):
        assert DATA_FILE.exists(), \
            "data/trades.csv missing — run: python fetch_data.py"

    @pytest.mark.smoke
    def test_symbols_json_exists(self):
        assert SYMBOLS_FILE.exists(), \
            "data/symbols.json missing — run: python fetch_symbols.py"

    @pytest.mark.smoke
    def test_preferred_date_in_csv(self):
        """Warn (not fail) if preferred golden date has dropped out of CSV."""
        if not DATA_FILE.exists():
            pytest.skip("trades.csv not found")
        df = pd.read_csv(DATA_FILE)
        df["time"] = pd.to_datetime(df["time"], format="ISO8601", utc=True)
        dates = df["time"].dt.strftime("%Y-%m-%d").unique()
        if PREFERRED_DATE not in dates:
            pytest.xfail(
                f"Preferred golden date {PREFERRED_DATE} not in CSV — "
                "tests will use a fallback date instead"
            )


# ── Golden: build_scenarios ───────────────────────────────────

class TestGoldenScenarios:
    """
    Tests build_scenarios() against a real trading day.
    Uses pre-computed expected values for 2026-01-13.
    Falls back dynamically if that date is unavailable.
    """

    @pytest.mark.core
    def test_scenarios_returns_dataframe(self, golden_scenarios):
        result, date_str = golden_scenarios
        assert isinstance(result, pd.DataFrame), \
            f"build_scenarios({date_str}) should return a DataFrame"

    @pytest.mark.core
    def test_scenarios_not_empty(self, golden_scenarios):
        result, date_str = golden_scenarios
        assert not result.empty, \
            f"build_scenarios({date_str}) returned empty DataFrame"

    @pytest.mark.core
    def test_scenario_count_matches_expected(self, golden_scenarios):
        """
        The number of scenarios must match what we expect for the golden date.
        If this fails after a code change — scenario gap logic has changed.
        """
        result, date_str = golden_scenarios
        if date_str == PREFERRED_DATE:
            assert len(result) == 6, (
                f"Expected 6 scenarios on {date_str}, got {len(result)}. "
                "The 10-minute gap threshold may have changed."
            )
        else:
            assert len(result) >= MIN_SCENARIOS, \
                f"Expected at least {MIN_SCENARIOS} scenarios, got {len(result)}"

    @pytest.mark.core
    def test_total_pnl_matches_expected(self, golden_scenarios):
        """
        Total P&L across all scenarios must match the sum from raw trades.
        If this fails — P&L aggregation logic has changed.
        """
        result, date_str = golden_scenarios
        actual_pnl = result["P&L (£)"].sum()

        if date_str == PREFERRED_DATE:
            assert actual_pnl == pytest.approx(110.78, abs=0.05), (
                f"Expected total P&L of £110.78 on {date_str}, got £{actual_pnl:.2f}. "
                "P&L aggregation logic may have changed."
            )
        else:
            # For fallback dates — just verify it matches the raw CSV sum
            df = pd.read_csv(DATA_FILE)
            df["time"] = pd.to_datetime(df["time"], format="ISO8601", utc=True)
            sel_dt  = pd.Timestamp(date_str).tz_localize("UTC")
            sel_end = sel_dt + timedelta(days=1)
            raw_pnl = df[
                (df["is_closing"] == True) &
                (df["time"] >= sel_dt) &
                (df["time"] < sel_end)
            ]["pnl"].sum()
            assert actual_pnl == pytest.approx(raw_pnl, abs=0.05), (
                f"build_scenarios P&L (£{actual_pnl:.2f}) doesn't match "
                f"raw CSV sum (£{raw_pnl:.2f}) for {date_str}"
            )

    @pytest.mark.core
    def test_pnl_per_scenario_sums_to_total(self, golden_scenarios):
        """
        Sum of individual scenario P&Ls must equal the overall total.
        Catches off-by-one or double-counting bugs.
        """
        result, date_str = golden_scenarios
        df = pd.read_csv(DATA_FILE)
        df["time"] = pd.to_datetime(df["time"], format="ISO8601", utc=True)
        sel_dt  = pd.Timestamp(date_str).tz_localize("UTC")
        sel_end = sel_dt + timedelta(days=1)
        raw_total = df[
            (df["is_closing"] == True) &
            (df["time"] >= sel_dt) &
            (df["time"] < sel_end)
        ]["pnl"].sum()
        assert result["P&L (£)"].sum() == pytest.approx(raw_total, abs=0.05), \
            "Scenario P&L sum does not match raw trade P&L sum"

    @pytest.mark.core
    def test_trade_count_matches_expected(self, golden_scenarios):
        """
        Total trades across all scenarios must equal closing trades in CSV.
        Catches trades being double-counted or missed.
        """
        result, date_str = golden_scenarios
        df = pd.read_csv(DATA_FILE)
        df["time"] = pd.to_datetime(df["time"], format="ISO8601", utc=True)
        sel_dt  = pd.Timestamp(date_str).tz_localize("UTC")
        sel_end = sel_dt + timedelta(days=1)
        raw_count = len(df[
            (df["is_closing"] == True) &
            (df["time"] >= sel_dt) &
            (df["time"] < sel_end)
        ])
        scenario_total = result["Trades"].sum()
        assert scenario_total == raw_count, (
            f"Scenario trade count ({scenario_total}) != "
            f"raw closing trades ({raw_count}) on {date_str}"
        )

    @pytest.mark.core
    def test_win_rate_in_valid_range(self, golden_scenarios):
        """Win rate must be between 0 and 100 for all scenarios."""
        result, date_str = golden_scenarios
        for _, row in result.iterrows():
            assert 0 <= row["Win %"] <= 100, \
                f"Scenario {row['Scenario']} has invalid win rate: {row['Win %']}"

    @pytest.mark.core
    def test_preferred_date_win_rate(self, golden_scenarios):
        """On preferred golden date, overall win rate should be ~89.5%."""
        result, date_str = golden_scenarios
        if date_str != PREFERRED_DATE:
            pytest.skip("Using fallback date — skipping preferred-date-specific check")
        total_trades = result["Trades"].sum()
        winning = sum(
            row["Trades"] * (row["Win %"] / 100)
            for _, row in result.iterrows()
        )
        actual_wr = round(winning / total_trades * 100, 1)
        assert actual_wr == pytest.approx(89.5, abs=2.0), \
            f"Expected ~89.5% win rate on {PREFERRED_DATE}, got {actual_wr}%"

    @pytest.mark.core
    def test_scenario_instruments_populated(self, golden_scenarios):
        """Every scenario must have at least one instrument listed."""
        result, date_str = golden_scenarios
        for _, row in result.iterrows():
            assert row["Instruments"] and len(str(row["Instruments"])) > 0, \
                f"Scenario {row['Scenario']} has no instruments listed"

    @pytest.mark.core
    def test_exposure_dd_not_positive(self, golden_scenarios):
        """Exposure DD should be 0 or negative — never positive."""
        result, date_str = golden_scenarios
        for _, row in result.iterrows():
            assert row["Exposure DD (£)"] <= 0, (
                f"Scenario {row['Scenario']} has positive exposure DD: "
                f"£{row['Exposure DD (£)']:.2f}"
            )


# ── Golden: build_daily_summary ───────────────────────────────

class TestGoldenDailySummary:
    """
    Tests build_daily_summary() against real data.
    Checks the golden date row has the correct P&L, trade count, and win rate.
    """

    @pytest.mark.core
    def test_summary_contains_golden_date(self, golden_daily_summary, golden_date_and_df):
        """The daily summary must include a row for the golden date."""
        date_str, _ = golden_date_and_df
        result = golden_daily_summary
        dates = result["Date"].astype(str).tolist()
        assert any(date_str in d for d in dates), \
            f"Golden date {date_str} not found in daily summary. Dates available: {dates[:5]}"

    @pytest.mark.core
    def test_golden_date_pnl_correct(self, golden_daily_summary, golden_date_and_df):
        """Daily summary P&L for golden date must match raw CSV sum."""
        date_str, df = golden_date_and_df
        result = golden_daily_summary

        # Get the row for our golden date
        row = result[result["Date"].astype(str).str.contains(date_str)]
        if row.empty:
            pytest.skip(f"Golden date {date_str} not in daily summary")

        actual_pnl = row.iloc[0]["P&L (£)"]

        # Expected from raw CSV
        df_t = df.copy()
        df_t["time"] = pd.to_datetime(df_t["time"], format="ISO8601", utc=True)
        sel_dt  = pd.Timestamp(date_str).tz_localize("UTC")
        sel_end = sel_dt + timedelta(days=1)
        expected_pnl = df_t[
            (df_t["is_closing"] == True) &
            (df_t["time"] >= sel_dt) &
            (df_t["time"] < sel_end)
        ]["pnl"].sum()

        assert actual_pnl == pytest.approx(expected_pnl, abs=0.05), (
            f"Daily summary P&L for {date_str}: "
            f"got £{actual_pnl:.2f}, expected £{expected_pnl:.2f}"
        )

    @pytest.mark.core
    def test_golden_date_trade_count_correct(self, golden_daily_summary, golden_date_and_df):
        """Trade count in daily summary must match raw CSV closing count."""
        date_str, df = golden_date_and_df
        result = golden_daily_summary
        row = result[result["Date"].astype(str).str.contains(date_str)]
        if row.empty:
            pytest.skip(f"Golden date {date_str} not in daily summary")

        actual_count = row.iloc[0]["Trades"]
        df_t = df.copy()
        df_t["time"] = pd.to_datetime(df_t["time"], format="ISO8601", utc=True)
        sel_dt  = pd.Timestamp(date_str).tz_localize("UTC")
        sel_end = sel_dt + timedelta(days=1)
        expected_count = len(df_t[
            (df_t["is_closing"] == True) &
            (df_t["time"] >= sel_dt) &
            (df_t["time"] < sel_end)
        ])

        assert actual_count == expected_count, (
            f"Daily summary trade count for {date_str}: "
            f"got {actual_count}, expected {expected_count}"
        )

    @pytest.mark.core
    def test_golden_date_win_rate_correct(self, golden_daily_summary, golden_date_and_df):
        """Win rate in daily summary must match manual calculation from raw CSV."""
        date_str, df = golden_date_and_df
        result = golden_daily_summary
        row = result[result["Date"].astype(str).str.contains(date_str)]
        if row.empty:
            pytest.skip(f"Golden date {date_str} not in daily summary")

        actual_wr = row.iloc[0]["Win %"]
        df_t = df.copy()
        df_t["time"] = pd.to_datetime(df_t["time"], format="ISO8601", utc=True)
        sel_dt  = pd.Timestamp(date_str).tz_localize("UTC")
        sel_end = sel_dt + timedelta(days=1)
        day = df_t[
            (df_t["is_closing"] == True) &
            (df_t["time"] >= sel_dt) &
            (df_t["time"] < sel_end)
        ]
        expected_wr = round(len(day[day["pnl"] > 0]) / len(day) * 100, 1)

        assert actual_wr == pytest.approx(expected_wr, abs=1.0), (
            f"Daily summary win rate for {date_str}: "
            f"got {actual_wr}%, expected {expected_wr}%"
        )


# ── Golden: build_floating_pnl ────────────────────────────────

class TestGoldenFloatingPnl:
    """Tests build_floating_pnl() produces consistent output on real data."""

    @pytest.mark.core
    def test_floating_pnl_returns_data(self, golden_date_and_df):
        """build_floating_pnl() must return a non-empty DataFrame for a day with trades."""
        import app as app_module
        date_str, _ = golden_date_and_df
        result = app_module.build_floating_pnl(date_str)
        assert isinstance(result, pd.DataFrame),             "build_floating_pnl() should return a DataFrame"
        assert not result.empty,             f"build_floating_pnl({date_str}) returned empty — expected data"

    @pytest.mark.core
    def test_floating_pnl_all_positions_covered(self, golden_date_and_df):
        """Every closed position on the day should appear in the floating P&L output."""
        import app as app_module
        date_str, df = golden_date_and_df
        result = app_module.build_floating_pnl(date_str)
        if result.empty:
            pytest.skip("No floating P&L data generated")

        df_t = df.copy()
        df_t["time"] = pd.to_datetime(df_t["time"], format="ISO8601", utc=True)
        sel_dt  = pd.Timestamp(date_str).tz_localize("UTC")
        sel_end = sel_dt + timedelta(days=1)
        day_closings = df_t[
            (df_t["is_closing"] == True) &
            (df_t["time"] >= sel_dt) &
            (df_t["time"] < sel_end)
        ]

        expected_positions = set(day_closings["position_id"].unique())
        actual_positions   = set(result["position_id"].unique())
        missing = expected_positions - actual_positions

        assert not missing, (
            f"These position_ids are in trades.csv but missing from "
            f"floating P&L output: {missing}"
        )

    @pytest.mark.core
    def test_floating_pnl_has_required_columns(self, golden_date_and_df):
        """Output must have all expected columns for the CSV download to work."""
        import app as app_module
        date_str, _ = golden_date_and_df
        result = app_module.build_floating_pnl(date_str)
        if result.empty:
            pytest.skip("No floating P&L data generated")
        required = [
            "date", "scenario", "position_id", "symbol",
            "direction", "entry_price", "exit_price", "closed_pnl",
            "time", "price_at_time", "position_float_pnl",
            "scenario_total_float",
        ]
        for col in required:
            assert col in result.columns,                 f"Missing column in floating P&L output: {col}"

    @pytest.mark.core
    def test_floating_pnl_row_count_reasonable(self, golden_date_and_df):
        """
        Row count must be >= number of closing positions on the day.
        Each position needs at least one price checkpoint row.
        """
        import app as app_module
        date_str, df = golden_date_and_df
        result = app_module.build_floating_pnl(date_str)
        if result.empty:
            pytest.skip("No floating P&L data generated")

        df_t = df.copy()
        df_t["time"] = pd.to_datetime(df_t["time"], format="ISO8601", utc=True)
        sel_dt  = pd.Timestamp(date_str).tz_localize("UTC")
        sel_end = sel_dt + timedelta(days=1)
        n_closings = len(df_t[
            (df_t["is_closing"] == True) &
            (df_t["time"] >= sel_dt) &
            (df_t["time"] < sel_end)
        ])

        assert len(result) >= n_closings, (
            f"Floating P&L has {len(result)} rows but there are "
            f"{n_closings} closing positions — expected at least one row each"
        )

    @pytest.mark.core
    def test_floating_pnl_closed_pnl_matches_csv(self, golden_date_and_df):
        """
        The closed_pnl column in floating P&L output must match
        the actual pnl values in trades.csv for each position.
        This catches any mismatch between the two data sources.
        """
        import app as app_module
        date_str, df = golden_date_and_df
        result = app_module.build_floating_pnl(date_str)
        if result.empty:
            pytest.skip("No floating P&L data generated")

        df_t = df.copy()
        # Build a lookup of position_id -> actual pnl from CSV
        closing_pnl = df_t[df_t["is_closing"] == True].set_index("position_id")["pnl"]

        mismatches = []
        for pos_id, grp in result.groupby("position_id"):
            reported_pnl = grp["closed_pnl"].iloc[0]
            if pos_id in closing_pnl.index:
                actual_pnl = closing_pnl[pos_id]
                if abs(reported_pnl - actual_pnl) > 0.05:
                    mismatches.append(
                        f"Position {pos_id}: floating CSV shows £{reported_pnl:.2f} "
                        f"but trades.csv has £{actual_pnl:.2f}"
                    )

        assert not mismatches, (
            f"closed_pnl mismatch between floating P&L and trades.csv:\n"
            + "\n".join(mismatches[:5])
        )
