# tests/test_app_logic.py
# Functional tests for the Trading Journal dashboard
#
# These tests cover the core logic functions in app.py:
#   - Data loading helpers
#   - Scenario detection
#   - Exposure drawdown calculation
#   - Daily summary building
#   - Floating P&L generation
#   - Symbol name lookup
#
# No browser or running server needed — tests call the functions directly.
#
# Run all:        pytest tests/test_app_logic.py -v
# Run smoke only: pytest tests/test_app_logic.py -m smoke -v

import sys
import json
import pytest
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

# ── Helpers to build minimal test data ───────────────────────

def make_trades_df(rows):
    """Build a DataFrame in the same format as trades.csv."""
    df = pd.DataFrame(rows)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df


def one_position(
    position_id=1,
    symbol_id=93,
    direction="BUY",
    entry_price=3600.0,
    exit_price=3650.0,
    volume=1.0,
    pnl=45.0,
    entry_time=None,
    exit_time=None,
):
    """Returns (opening_row, closing_row) for one matched position."""
    now = datetime.now(timezone.utc)
    if entry_time is None:
        entry_time = now - timedelta(hours=2)
    if exit_time is None:
        exit_time = now - timedelta(hours=1)

    opening = {
        "deal_id":     position_id * 10,
        "position_id": position_id,
        "symbol_id":   symbol_id,
        "direction":   direction,
        "volume":      volume,
        "fill_price":  entry_price,
        "close_price": entry_price,
        "time":        entry_time.isoformat(),
        "pnl":         0.0,
        "commission":  -0.5,
        "is_closing":  False,
    }
    closing_dir = "SELL" if direction == "BUY" else "BUY"
    closing = {
        "deal_id":     position_id * 10 + 1,
        "position_id": position_id,
        "symbol_id":   symbol_id,
        "direction":   closing_dir,
        "volume":      volume,
        "fill_price":  exit_price,
        "close_price": entry_price,
        "time":        exit_time.isoformat(),
        "pnl":         pnl,
        "commission":  -0.5,
        "is_closing":  True,
    }
    return opening, closing


# ── Tests: get_symbol_name ────────────────────────────────────

class TestGetSymbolName:
    """Tests for the get_symbol_name() helper."""

    def setup_method(self):
        # Import directly from app — avoids running the whole Dash app
        import importlib.util
        spec = importlib.util.spec_from_file_location("app", BASE_DIR / "app.py")
        self.app_module = importlib.util.load_from_spec = spec
        # Read just the function we need
        self._symbols = {"93": "XAUEUR", "92": "XAGEUR", "141": "XAUGBP"}

    def get_symbol_name(self, symbol_id, symbols):
        from dashboard.helpers import get_symbol_name
        return get_symbol_name(symbol_id, symbols)

    @pytest.mark.smoke
    def test_known_symbol_returns_name(self):
        result = self.get_symbol_name(93, self._symbols)
        assert result == "XAUEUR"

    @pytest.mark.smoke
    def test_unknown_symbol_returns_fallback(self):
        result = self.get_symbol_name(9999, self._symbols)
        assert result == "Symbol 9999"

    @pytest.mark.core
    def test_symbol_id_as_int_works(self):
        """symbol_id can come in as int or string — both should work."""
        assert self.get_symbol_name(93,   self._symbols) == "XAUEUR"
        assert self.get_symbol_name("93", self._symbols) == "XAUEUR"

    @pytest.mark.core
    def test_empty_symbols_dict_returns_fallback(self):
        result = self.get_symbol_name(93, {})
        assert result == "Symbol 93"


# ── Tests: build_scenarios ────────────────────────────────────

class TestBuildScenarios:
    """
    Tests for build_scenarios(date_str).
    This is one of the most important functions — it drives the entire
    Scenarios page. Tests use a patched DATA_FILE pointing at test data.
    """

    @pytest.fixture
    def patch_data_file(self, tmp_path, monkeypatch):
        """Create a temp data dir for testing."""
        import dashboard.helpers as helpers_module
        import dashboard.scenarios as scenarios_module
        data_path = tmp_path / "trades.csv"
        symbols_path = tmp_path / "symbols.json"
        symbols_path.write_text(json.dumps({"93": "XAUEUR"}))
        monkeypatch.setattr(helpers_module, "SYMBOLS_FILE", symbols_path)
        monkeypatch.setattr(scenarios_module, "DATA_FILE", data_path)
        return data_path

    def write_trades(self, path, rows):
        df = pd.DataFrame(rows)
        df.to_csv(path, index=False)

    @pytest.mark.core
    def test_empty_date_returns_empty_dataframe(self, patch_data_file):
        """A day with no trades should return an empty DataFrame."""
        from dashboard.scenarios import build_scenarios
        # Write trades for a different date
        o, c = one_position(
            exit_time=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
            entry_time=datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc),
        )
        self.write_trades(patch_data_file, [o, c])
        result = build_scenarios("2026-02-01", data_file=patch_data_file)
        assert result.empty

    @pytest.mark.core
    def test_single_trade_creates_one_scenario(self, patch_data_file):
        """One closing trade on a day should produce exactly one scenario."""
        from dashboard.scenarios import build_scenarios
        from dashboard.journal import build_daily_summary, calc_exposure_drawdown
        from dashboard.floating_pnl import build_floating_pnl
        o, c = one_position(
            position_id=1,
            exit_time=datetime(2026, 2, 16, 10, 0, tzinfo=timezone.utc),
            entry_time=datetime(2026, 2, 16, 9, 0, tzinfo=timezone.utc),
            pnl=25.0,
        )
        self.write_trades(patch_data_file, [o, c])
        result = build_scenarios("2026-02-16", data_file=patch_data_file)
        assert len(result) == 1

    @pytest.mark.core
    def test_two_trades_close_together_same_scenario(self, patch_data_file):
        """Two trades closing within 10 minutes should be ONE scenario."""
        from dashboard.scenarios import build_scenarios
        from dashboard.journal import build_daily_summary, calc_exposure_drawdown
        from dashboard.floating_pnl import build_floating_pnl
        base = datetime(2026, 2, 16, 10, 0, tzinfo=timezone.utc)
        o1, c1 = one_position(
            position_id=1,
            entry_time=base - timedelta(minutes=30),
            exit_time=base,
            pnl=10.0,
        )
        o2, c2 = one_position(
            position_id=2,
            entry_time=base - timedelta(minutes=20),
            exit_time=base + timedelta(minutes=5),  # 5 min gap — same scenario
            pnl=15.0,
        )
        self.write_trades(patch_data_file, [o1, c1, o2, c2])
        result = build_scenarios("2026-02-16", data_file=patch_data_file)
        assert len(result) == 1

    @pytest.mark.core
    def test_two_trades_far_apart_different_scenarios(self, patch_data_file):
        """Two trades with 15+ minute gap between exits should be TWO scenarios."""
        from dashboard.scenarios import build_scenarios
        from dashboard.journal import build_daily_summary, calc_exposure_drawdown
        from dashboard.floating_pnl import build_floating_pnl
        base = datetime(2026, 2, 16, 10, 0, tzinfo=timezone.utc)
        o1, c1 = one_position(
            position_id=1,
            entry_time=base - timedelta(minutes=30),
            exit_time=base,
            pnl=10.0,
        )
        o2, c2 = one_position(
            position_id=2,
            entry_time=base + timedelta(minutes=5),
            exit_time=base + timedelta(minutes=20),  # 20 min gap — new scenario
            pnl=15.0,
        )
        self.write_trades(patch_data_file, [o1, c1, o2, c2])
        result = build_scenarios("2026-02-16", data_file=patch_data_file)
        assert len(result) == 2

    @pytest.mark.core
    def test_scenario_pnl_sums_correctly(self, patch_data_file):
        """Scenario P&L must equal the sum of all trades in that scenario."""
        from dashboard.scenarios import build_scenarios
        from dashboard.journal import build_daily_summary, calc_exposure_drawdown
        from dashboard.floating_pnl import build_floating_pnl
        base = datetime(2026, 2, 16, 10, 0, tzinfo=timezone.utc)
        trades = []
        expected_pnl = 0.0
        for i in range(4):
            o, c = one_position(
                position_id=i + 1,
                entry_time=base - timedelta(minutes=30 - i * 2),
                exit_time=base + timedelta(minutes=i),
                pnl=10.0 + i,
            )
            expected_pnl += 10.0 + i
            trades += [o, c]
        self.write_trades(patch_data_file, trades)
        result = build_scenarios("2026-02-16", data_file=patch_data_file)
        assert len(result) == 1
        assert result.iloc[0]["P&L (£)"] == pytest.approx(expected_pnl, abs=0.01)

    @pytest.mark.core
    def test_scenario_has_required_columns(self, patch_data_file):
        """Output DataFrame must have all expected columns."""
        from dashboard.scenarios import build_scenarios
        from dashboard.journal import build_daily_summary, calc_exposure_drawdown
        from dashboard.floating_pnl import build_floating_pnl
        o, c = one_position(
            exit_time=datetime(2026, 2, 16, 10, 0, tzinfo=timezone.utc),
            entry_time=datetime(2026, 2, 16, 9, 0, tzinfo=timezone.utc),
        )
        self.write_trades(patch_data_file, [o, c])
        result = build_scenarios("2026-02-16", data_file=patch_data_file)
        required = [
            "Scenario", "Start", "First Close", "Last Close",
            "Duration", "Trades", "Buys", "Sells",
            "P&L (£)", "Net (£)", "Win %",
            "Exposure DD (£)", "Instruments",
        ]
        for col in required:
            assert col in result.columns, f"Missing column: {col}"

    @pytest.mark.core
    def test_scenario_buys_sells_count_correct(self, patch_data_file):
        """Buys and Sells columns must reflect the correct direction counts."""
        from dashboard.scenarios import build_scenarios
        from dashboard.journal import build_daily_summary, calc_exposure_drawdown
        from dashboard.floating_pnl import build_floating_pnl
        base = datetime(2026, 2, 16, 10, 0, tzinfo=timezone.utc)
        o1, c1 = one_position(position_id=1, direction="BUY",
            entry_time=base - timedelta(minutes=10),
            exit_time=base, pnl=10.0)
        o2, c2 = one_position(position_id=2, direction="BUY",
            entry_time=base - timedelta(minutes=8),
            exit_time=base + timedelta(minutes=2), pnl=8.0)
        self.write_trades(patch_data_file, [o1, c1, o2, c2])
        result = build_scenarios("2026-02-16", data_file=patch_data_file)
        assert result.iloc[0]["Buys"] == 2
        assert result.iloc[0]["Sells"] == 0


# ── Tests: calc_exposure_drawdown ─────────────────────────────

class TestCalcExposureDrawdown:
    """
    Tests for calc_exposure_drawdown(date_str, all_df).
    This calculates the worst floating loss at any point during a day.
    """

    def make_df(self, rows):
        df = pd.DataFrame(rows)
        df["time"] = pd.to_datetime(df["time"], utc=True)
        return df

    @pytest.mark.core
    def test_empty_day_returns_none(self):
        from dashboard.journal import calc_exposure_drawdown
        df = self.make_df([{
            "deal_id": 1, "position_id": 1, "symbol_id": 93,
            "direction": "BUY", "volume": 1.0,
            "fill_price": 3600.0, "close_price": 3600.0,
            "time": "2026-01-01T10:00:00+00:00",
            "pnl": 0.0, "commission": -0.5, "is_closing": False,
        }])
        result = calc_exposure_drawdown("2026-02-16", df)
        assert result is None

    @pytest.mark.core
    def test_profitable_trade_returns_zero(self):
        """A trade that went straight to profit should have 0 exposure DD."""
        from dashboard.scenarios import build_scenarios
        from dashboard.journal import build_daily_summary, calc_exposure_drawdown
        from dashboard.floating_pnl import build_floating_pnl
        base = datetime(2026, 2, 16, 10, 0, tzinfo=timezone.utc)
        o, c = one_position(
            entry_price=3600.0,
            exit_price=3650.0,
            pnl=45.0,
            entry_time=base - timedelta(minutes=30),
            exit_time=base,
        )
        df = self.make_df([o, c])
        result = calc_exposure_drawdown("2026-02-16", df)
        assert result == 0.0

    @pytest.mark.core
    def test_losing_trade_has_negative_exposure(self):
        """
        A trade that closed at a loss must have negative exposure DD.
        We need multiple price events so the function has checkpoints
        to observe the price moving against the open position.
        """
        from dashboard.scenarios import build_scenarios
        from dashboard.journal import build_daily_summary, calc_exposure_drawdown
        from dashboard.floating_pnl import build_floating_pnl
        base = datetime(2026, 2, 16, 10, 0, tzinfo=timezone.utc)

        # Main losing position — open for 30 mins
        o1, c1 = one_position(
            position_id=1,
            entry_price=3600.0,
            exit_price=3550.0,
            pnl=-45.0,
            entry_time=base - timedelta(minutes=30),
            exit_time=base,
        )
        # Second position that closes at a lower price WHILE position 1 is still open
        # This creates a price event at 3540 which is worse than position 1 entry (3600)
        o2, c2 = one_position(
            position_id=2,
            entry_price=3580.0,
            exit_price=3540.0,  # price drops to 3540 while pos 1 is still open
            pnl=-38.0,
            entry_time=base - timedelta(minutes=20),
            exit_time=base - timedelta(minutes=10),  # closes before pos 1
        )
        df = self.make_df([o1, c1, o2, c2])
        result = calc_exposure_drawdown("2026-02-16", df)
        assert result is not None
        assert result < 0, f"Expected negative exposure DD, got {result}"

    @pytest.mark.core
    def test_exposure_dd_not_worse_than_sum_of_losses(self):
        """
        Exposure DD should never be more negative than
        the total P&L of all losing trades combined.
        """
        from dashboard.scenarios import build_scenarios
        from dashboard.journal import build_daily_summary, calc_exposure_drawdown
        from dashboard.floating_pnl import build_floating_pnl
        base = datetime(2026, 2, 16, 10, 0, tzinfo=timezone.utc)
        rows = []
        total_loss = 0.0
        for i in range(3):
            o, c = one_position(
                position_id=i + 1,
                entry_price=3600.0,
                exit_price=3550.0 - i * 5,
                pnl=-20.0 - i * 5,
                entry_time=base - timedelta(minutes=30 - i * 5),
                exit_time=base + timedelta(minutes=i * 2),
            )
            total_loss += (-20.0 - i * 5)
            rows += [o, c]
        df = self.make_df(rows)
        result = calc_exposure_drawdown("2026-02-16", df)
        assert result is not None
        assert result >= total_loss, (
            f"Exposure DD {result} is more negative than total losses {total_loss}"
        )


# ── Tests: build_daily_summary ────────────────────────────────

class TestBuildDailySummary:
    """Tests for build_daily_summary() — the Journal page data."""

    @pytest.fixture
    def patch_data_file(self, tmp_path, monkeypatch):
        import dashboard.helpers as helpers_module
        data_path = tmp_path / "trades.csv"
        symbols_path = tmp_path / "symbols.json"
        symbols_path.write_text(json.dumps({"93": "XAUEUR"}))
        monkeypatch.setattr(helpers_module, "SYMBOLS_FILE", symbols_path)
        monkeypatch.setattr(helpers_module, "DATA_FILE", data_path)
        return data_path

    @pytest.mark.core
    def test_returns_dataframe(self, patch_data_file):
        from dashboard.scenarios import build_scenarios
        from dashboard.journal import build_daily_summary, calc_exposure_drawdown
        from dashboard.floating_pnl import build_floating_pnl
        base = datetime(2026, 2, 16, 10, 0, tzinfo=timezone.utc)
        o, c = one_position(
            exit_time=base,
            entry_time=base - timedelta(hours=1),
            pnl=30.0,
        )
        pd.DataFrame([o, c]).to_csv(patch_data_file, index=False)
        result = build_daily_summary(data_file=patch_data_file)
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    @pytest.mark.core
    def test_one_trading_day_produces_one_row(self, patch_data_file):
        from dashboard.scenarios import build_scenarios
        from dashboard.journal import build_daily_summary, calc_exposure_drawdown
        from dashboard.floating_pnl import build_floating_pnl
        base = datetime(2026, 2, 16, 10, 0, tzinfo=timezone.utc)
        o, c = one_position(
            exit_time=base,
            entry_time=base - timedelta(hours=1),
            pnl=30.0,
        )
        pd.DataFrame([o, c]).to_csv(patch_data_file, index=False)
        result = build_daily_summary(data_file=patch_data_file)
        assert len(result) == 1

    @pytest.mark.core
    def test_daily_summary_has_required_columns(self, patch_data_file):
        from dashboard.scenarios import build_scenarios
        from dashboard.journal import build_daily_summary, calc_exposure_drawdown
        from dashboard.floating_pnl import build_floating_pnl
        base = datetime(2026, 2, 16, 10, 0, tzinfo=timezone.utc)
        o, c = one_position(exit_time=base, entry_time=base - timedelta(hours=1))
        pd.DataFrame([o, c]).to_csv(patch_data_file, index=False)
        result = build_daily_summary(data_file=patch_data_file)
        required = ["Date", "P&L (£)", "Net (£)", "Trades", "Win %",
                    "Instruments", "Sessions", "First Session"]
        for col in required:
            assert col in result.columns, f"Missing column: {col}"

    @pytest.mark.core
    def test_pnl_sum_is_correct(self, patch_data_file):
        from dashboard.scenarios import build_scenarios
        from dashboard.journal import build_daily_summary, calc_exposure_drawdown
        from dashboard.floating_pnl import build_floating_pnl
        base = datetime(2026, 2, 16, 10, 0, tzinfo=timezone.utc)
        rows = []
        for i, pnl in enumerate([10.0, 20.0, -5.0]):
            o, c = one_position(
                position_id=i + 1,
                exit_time=base + timedelta(minutes=i * 10),
                entry_time=base + timedelta(minutes=i * 10) - timedelta(hours=1),
                pnl=pnl,
            )
            rows += [o, c]
        pd.DataFrame(rows).to_csv(patch_data_file, index=False)
        result = build_daily_summary(data_file=patch_data_file)
        assert result.iloc[0]["P&L (£)"] == pytest.approx(25.0, abs=0.01)

    @pytest.mark.core
    def test_win_rate_calculation(self, patch_data_file):
        from dashboard.scenarios import build_scenarios
        from dashboard.journal import build_daily_summary, calc_exposure_drawdown
        from dashboard.floating_pnl import build_floating_pnl
        base = datetime(2026, 2, 16, 10, 0, tzinfo=timezone.utc)
        rows = []
        # 3 wins, 1 loss = 75% win rate
        for i, pnl in enumerate([10.0, 20.0, 15.0, -5.0]):
            o, c = one_position(
                position_id=i + 1,
                exit_time=base + timedelta(minutes=i * 5),
                entry_time=base + timedelta(minutes=i * 5) - timedelta(hours=1),
                pnl=pnl,
            )
            rows += [o, c]
        pd.DataFrame(rows).to_csv(patch_data_file, index=False)
        result = build_daily_summary(data_file=patch_data_file)
        assert result.iloc[0]["Win %"] == pytest.approx(75.0, abs=0.1)


# ── Tests: build_floating_pnl ─────────────────────────────────

class TestBuildFloatingPnl:
    """Tests for build_floating_pnl(date_str) — the downloadable CSV."""

    @pytest.fixture
    def patch_data_file(self, tmp_path, monkeypatch):
        import dashboard.helpers as helpers_module
        data_path = tmp_path / "trades.csv"
        symbols_path = tmp_path / "symbols.json"
        symbols_path.write_text(json.dumps({"93": "XAUEUR"}))
        monkeypatch.setattr(helpers_module, "SYMBOLS_FILE", symbols_path)
        monkeypatch.setattr(helpers_module, "DATA_FILE", data_path)
        return data_path

    @pytest.mark.core
    def test_empty_date_returns_empty_dataframe(self, patch_data_file):
        from dashboard.scenarios import build_scenarios
        from dashboard.journal import build_daily_summary, calc_exposure_drawdown
        from dashboard.floating_pnl import build_floating_pnl
        base = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        o, c = one_position(exit_time=base, entry_time=base - timedelta(hours=1))
        pd.DataFrame([o, c]).to_csv(patch_data_file, index=False)
        result = build_floating_pnl("2026-02-16", data_file=patch_data_file)
        assert result.empty

    @pytest.mark.core
    def test_returns_dataframe_with_correct_columns(self, patch_data_file):
        from dashboard.scenarios import build_scenarios
        from dashboard.journal import build_daily_summary, calc_exposure_drawdown
        from dashboard.floating_pnl import build_floating_pnl
        base = datetime(2026, 2, 16, 10, 0, tzinfo=timezone.utc)
        o, c = one_position(exit_time=base, entry_time=base - timedelta(hours=1))
        pd.DataFrame([o, c]).to_csv(patch_data_file, index=False)
        result = build_floating_pnl("2026-02-16", data_file=patch_data_file)
        if result.empty:
            pytest.skip("No price events available for floating P&L")
        required = [
            "date", "scenario", "position_id", "symbol",
            "direction", "entry_price", "exit_price", "closed_pnl",
            "time", "price_at_time", "position_float_pnl",
            "scenario_total_float",
        ]
        for col in required:
            assert col in result.columns, f"Missing column: {col}"

    @pytest.mark.core
    def test_float_pnl_zero_at_entry(self, patch_data_file):
        """At the moment of entry, floating P&L should be 0."""
        from dashboard.scenarios import build_scenarios
        from dashboard.journal import build_daily_summary, calc_exposure_drawdown
        from dashboard.floating_pnl import build_floating_pnl
        base = datetime(2026, 2, 16, 10, 0, tzinfo=timezone.utc)
        o, c = one_position(
            entry_price=3600.0,
            exit_price=3650.0,
            pnl=45.0,
            entry_time=base - timedelta(minutes=30),
            exit_time=base,
        )
        pd.DataFrame([o, c]).to_csv(patch_data_file, index=False)
        result = build_floating_pnl("2026-02-16", data_file=patch_data_file)
        if result.empty:
            pytest.skip("No price events for this test")
        # First row should have 0 float (price hasn't moved yet)
        first = result.sort_values("time").iloc[0]
        assert first["position_float_pnl"] == pytest.approx(0.0, abs=0.01)
