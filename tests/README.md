# Quick smoke check — runs in seconds, use this every day
pytest -m smoke

# Full core tests — run after any code change
pytest -m core

# Everything including live API (slow)
pytest -m live

# Everything except the slow live tests
pytest -m "not live"

# All tests
pytest