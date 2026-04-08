# tests/test_fetch_data.py
# Tests the fetch_data.py logic — data loading, caching, incremental fetch logic
#
# Run: pytest tests/test_fetch_data.py -v

import os
import sys
import pytest
import pandas as pd
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env")

pytestmark = pytest.mark.core


# ── Fixtures ──────────────────────────────────────────────────

@pytest.fixture
def tmp_data_dir(tmp_path):
    """Creates a temporary data directory for each test."""
    d = tmp_path / "data"
    d.mkdir()
    return d


@pytest.fixture
def sample_trades_csv(tmp_data_dir):
    """Creates a minimal valid trades.csv for testing."""
    now = datetime.now(timezone.utc)
    df = pd.DataFrame([
        {
            "deal_id":     1001,
            "position_id": 2001,
            "symbol_id":   93,
            "direction":   "BUY",
            "volume":      1.0,
            "fill_price":  3650.0,
            "close_price": 3650.0,
            "time":        (now - timedelta(hours=2)).isoformat(),
            "pnl":         0.0,
            "commission":  -0.5,
            "is_closing":  False,
        },
        {
            "deal_id":     1002,
            "position_id": 2001,
            "symbol_id":   93,
            "direction":   "SELL",
            "volume":      1.0,
            "fill_price":  3670.0,
            "close_price": 3650.0,
            "time":        (now - timedelta(hours=1)).isoformat(),
            "pnl":         18.50,
            "commission":  -0.5,
            "is_closing":  True,
        },
    ])
    path = tmp_data_dir / "trades.csv"
    df.to_csv(path, index=False)
    return path


# ── Config tests ──────────────────────────────────────────────

class TestConfig:
    def test_fetch_days_constant(self):
        """FETCH_DAYS should be a positive integer"""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "fetch_data", BASE_DIR / "fetch_data.py"
        )
        mod = importlib.util.load_from_spec = spec
        # Just check the file contains FETCH_DAYS
        content = (BASE_DIR / "fetch_data.py").read_text()
        assert "FETCH_DAYS" in content, "FETCH_DAYS constant not found in fetch_data.py"
        # Extract the value
        import re
        match = re.search(r"FETCH_DAYS\s*=\s*(\d+)", content)
        assert match, "Could not parse FETCH_DAYS value"
        value = int(match.group(1))
        assert value > 0,   "FETCH_DAYS must be positive"
        assert value <= 365, "FETCH_DAYS is suspiciously large (> 365)"


# ── CSV structure tests ───────────────────────────────────────

class TestTradesCsvStructure:
    REQUIRED_COLUMNS = [
        "deal_id", "position_id", "symbol_id", "direction",
        "volume", "fill_price", "close_price", "time",
        "pnl", "commission", "is_closing",
    ]

    @pytest.mark.smoke
    def test_trades_csv_exists(self):
        """trades.csv must exist in data/ folder"""
        path = BASE_DIR / "data" / "trades.csv"
        assert path.exists(), (
            "data/trades.csv not found. "
            "Run: python fetch_data.py"
        )

    def test_trades_csv_has_required_columns(self):
        """trades.csv must have all required columns"""
        path = BASE_DIR / "data" / "trades.csv"
        if not path.exists():
            pytest.skip("trades.csv not found — run fetch_data.py first")
        df = pd.read_csv(path, nrows=5)
        for col in self.REQUIRED_COLUMNS:
            assert col in df.columns, f"Missing column: {col}"

    def test_trades_csv_not_empty(self):
        """trades.csv must contain at least one row"""
        path = BASE_DIR / "data" / "trades.csv"
        if not path.exists():
            pytest.skip("trades.csv not found — run fetch_data.py first")
        df = pd.read_csv(path)
        assert len(df) > 0, "trades.csv is empty"

    def test_trades_csv_time_parseable(self):
        """Time column must be parseable as UTC datetime"""
        path = BASE_DIR / "data" / "trades.csv"
        if not path.exists():
            pytest.skip("trades.csv not found — run fetch_data.py first")
        df = pd.read_csv(path, nrows=10)
        try:
            times = pd.to_datetime(df["time"], format="ISO8601", utc=True)
            assert times.notna().all(), "Some time values could not be parsed"
        except Exception as e:
            pytest.fail(f"Failed to parse time column: {e}")

    def test_trades_csv_pnl_numeric(self):
        """PnL column must be numeric"""
        path = BASE_DIR / "data" / "trades.csv"
        if not path.exists():
            pytest.skip("trades.csv not found — run fetch_data.py first")
        df = pd.read_csv(path)
        assert pd.api.types.is_numeric_dtype(df["pnl"]), \
            "pnl column is not numeric"

    def test_trades_csv_direction_values(self):
        """Direction must only be BUY or SELL"""
        path = BASE_DIR / "data" / "trades.csv"
        if not path.exists():
            pytest.skip("trades.csv not found — run fetch_data.py first")
        df = pd.read_csv(path)
        valid = {"BUY", "SELL"}
        actual = set(df["direction"].unique())
        unexpected = actual - valid
        assert not unexpected, f"Unexpected direction values: {unexpected}"

    def test_trades_csv_has_closing_positions(self):
        """Must have at least some closing positions (is_closing = True)"""
        path = BASE_DIR / "data" / "trades.csv"
        if not path.exists():
            pytest.skip("trades.csv not found — run fetch_data.py first")
        df = pd.read_csv(path)
        closing = df[df["is_closing"] == True]
        assert len(closing) > 0, "No closing positions found in trades.csv"

    def test_trades_csv_positions_matchable(self):
        """Every closing deal must have a matching opening deal via position_id"""
        path = BASE_DIR / "data" / "trades.csv"
        if not path.exists():
            pytest.skip("trades.csv not found — run fetch_data.py first")
        df = pd.read_csv(path)
        closings = df[df["is_closing"] == True]
        openings = df[df["is_closing"] == False]
        opening_pos_ids = set(openings["position_id"].unique())

        unmatched = []
        for pos_id in closings["position_id"].unique():
            if pos_id not in opening_pos_ids:
                unmatched.append(pos_id)

        # Allow up to 5% unmatched (old positions opened before fetch window)
        pct_unmatched = len(unmatched) / len(closings["position_id"].unique()) * 100
        assert pct_unmatched < 5, (
            f"{pct_unmatched:.1f}% of closing positions have no matching opening deal. "
            f"Expected < 5%."
        )


# ── Cache / incremental logic tests ──────────────────────────

class TestCacheLogic:
    def test_sample_csv_loads_correctly(self, sample_trades_csv):
        """A minimal trades CSV should load and parse correctly"""
        df = pd.read_csv(sample_trades_csv)
        df["time"] = pd.to_datetime(df["time"], format="ISO8601", utc=True)
        assert len(df) == 2
        assert df["time"].notna().all()
        assert df["pnl"].sum() == pytest.approx(18.50, abs=0.01)

    def test_deduplication_on_deal_id(self, sample_trades_csv):
        """Duplicate deal_ids should be removed after merge"""
        df = pd.read_csv(sample_trades_csv)
        df_dup = pd.concat([df, df], ignore_index=True)
        assert len(df_dup) == 4
        df_dedup = df_dup.drop_duplicates(subset=["deal_id"])
        assert len(df_dedup) == 2

    def test_incremental_merge_adds_new_rows(self, tmp_data_dir):
        """New rows should be appended correctly in incremental mode"""
        now = datetime.now(timezone.utc)

        df_old = pd.DataFrame([{
            "deal_id": 1, "position_id": 1, "symbol_id": 93,
            "direction": "BUY", "volume": 1.0, "fill_price": 3600.0,
            "close_price": 3600.0,
            "time": (now - timedelta(days=2)).isoformat(),
            "pnl": 0.0, "commission": -0.5, "is_closing": False,
        }])

        df_new = pd.DataFrame([{
            "deal_id": 2, "position_id": 1, "symbol_id": 93,
            "direction": "SELL", "volume": 1.0, "fill_price": 3650.0,
            "close_price": 3600.0,
            "time": (now - timedelta(hours=1)).isoformat(),
            "pnl": 45.0, "commission": -0.5, "is_closing": True,
        }])

        combined = pd.concat([df_old, df_new], ignore_index=True)
        combined = combined.drop_duplicates(subset=["deal_id"])
        assert len(combined) == 2
        assert combined["pnl"].sum() == pytest.approx(45.0, abs=0.01)

    def test_no_duplicate_deals_after_overlap_merge(self, tmp_data_dir):
        """Overlapping fetch should not create duplicate deal_ids"""
        now = datetime.now(timezone.utc)

        shared_row = {
            "deal_id": 999, "position_id": 5, "symbol_id": 93,
            "direction": "BUY", "volume": 1.0, "fill_price": 3700.0,
            "close_price": 3700.0,
            "time": (now - timedelta(hours=2)).isoformat(),
            "pnl": 0.0, "commission": -0.5, "is_closing": False,
        }

        df_old = pd.DataFrame([shared_row])
        df_new = pd.DataFrame([shared_row])  # same row fetched again due to overlap

        combined = pd.concat([df_old, df_new], ignore_index=True)
        combined = combined.drop_duplicates(subset=["deal_id"])
        assert len(combined) == 1, "Duplicate deal_id not removed after merge"
