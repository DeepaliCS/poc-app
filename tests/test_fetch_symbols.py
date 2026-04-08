# tests/test_fetch_symbols.py
# Tests the symbols cache and symbol fetching logic
#
# Run: pytest tests/test_fetch_symbols.py -v

import os
import sys
import json
import pytest
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env")

pytestmark = pytest.mark.core


# ── symbols.json file tests ───────────────────────────────────

class TestSymbolsFile:
    @pytest.mark.smoke
    def test_symbols_json_exists(self):
        """symbols.json must exist in data/ folder"""
        path = BASE_DIR / "data" / "symbols.json"
        assert path.exists(), (
            "data/symbols.json not found. "
            "Run: python fetch_symbols.py"
        )

    @pytest.mark.smoke
    def test_symbols_json_valid_json(self):
        """symbols.json must be valid JSON"""
        path = BASE_DIR / "data" / "symbols.json"
        if not path.exists():
            pytest.skip("symbols.json not found — run fetch_symbols.py first")
        try:
            with open(path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"symbols.json is not valid JSON: {e}")

    def test_symbols_json_not_empty(self):
        """symbols.json must contain at least one symbol"""
        path = BASE_DIR / "data" / "symbols.json"
        if not path.exists():
            pytest.skip("symbols.json not found — run fetch_symbols.py first")
        with open(path) as f:
            data = json.load(f)
        assert len(data) > 0, "symbols.json is empty"

    def test_symbols_json_keys_are_strings(self):
        """All keys in symbols.json must be strings (symbol IDs)"""
        path = BASE_DIR / "data" / "symbols.json"
        if not path.exists():
            pytest.skip("symbols.json not found — run fetch_symbols.py first")
        with open(path) as f:
            data = json.load(f)
        for key in data.keys():
            assert isinstance(key, str), f"Key {key} is not a string"

    def test_symbols_json_values_are_strings(self):
        """All values in symbols.json must be strings (symbol names)"""
        path = BASE_DIR / "data" / "symbols.json"
        if not path.exists():
            pytest.skip("symbols.json not found — run fetch_symbols.py first")
        with open(path) as f:
            data = json.load(f)
        for key, val in data.items():
            assert isinstance(val, str), \
                f"Symbol name for ID {key} is not a string: {val}"
            assert len(val) > 0, f"Symbol name for ID {key} is empty"

    def test_symbols_json_keys_are_numeric_strings(self):
        """All keys must be numeric strings representing symbol IDs"""
        path = BASE_DIR / "data" / "symbols.json"
        if not path.exists():
            pytest.skip("symbols.json not found — run fetch_symbols.py first")
        with open(path) as f:
            data = json.load(f)
        for key in data.keys():
            assert key.isdigit(), \
                f"Symbol ID '{key}' is not a numeric string"


# ── Symbol lookup tests ───────────────────────────────────────

class TestSymbolLookup:
    KNOWN_SYMBOLS = {
        "41":  "XAUUSD",
        "42":  "XAGUSD",
        "92":  "XAGEUR",
        "93":  "XAUEUR",
        "107": "XAUAUD",
        "141": "XAUGBP",
        "142": "XAUJPY",
    }

    def test_known_traded_symbols_present(self):
        """All symbols you have actually traded must be in symbols.json"""
        path = BASE_DIR / "data" / "symbols.json"
        if not path.exists():
            pytest.skip("symbols.json not found — run fetch_symbols.py first")
        with open(path) as f:
            data = json.load(f)
        for sym_id, sym_name in self.KNOWN_SYMBOLS.items():
            assert sym_id in data, \
                f"Symbol ID {sym_id} ({sym_name}) not found in symbols.json"

    def test_known_symbol_names_correct(self):
        """Known symbol IDs must map to the correct names"""
        path = BASE_DIR / "data" / "symbols.json"
        if not path.exists():
            pytest.skip("symbols.json not found — run fetch_symbols.py first")
        with open(path) as f:
            data = json.load(f)
        for sym_id, expected_name in self.KNOWN_SYMBOLS.items():
            if sym_id in data:
                actual = data[sym_id]
                assert actual == expected_name, \
                    f"Symbol {sym_id}: expected {expected_name}, got {actual}"

    def test_traded_symbols_match_trades_csv(self):
        """Every symbol_id in trades.csv must have an entry in symbols.json"""
        import pandas as pd
        trades_path  = BASE_DIR / "data" / "trades.csv"
        symbols_path = BASE_DIR / "data" / "symbols.json"

        if not trades_path.exists():
            pytest.skip("trades.csv not found — run fetch_data.py first")
        if not symbols_path.exists():
            pytest.skip("symbols.json not found — run fetch_symbols.py first")

        df = pd.read_csv(trades_path)
        with open(symbols_path) as f:
            symbols = json.load(f)

        traded_ids = {str(int(s)) for s in df["symbol_id"].unique()}
        missing = [sid for sid in traded_ids if sid not in symbols]

        assert not missing, (
            f"These symbol IDs appear in trades.csv but not in symbols.json: {missing}. "
            f"Re-run: python fetch_symbols.py"
        )
