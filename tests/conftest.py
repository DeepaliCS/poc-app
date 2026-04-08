# tests/conftest.py
# Shared pytest configuration and fixtures
#
# This file is automatically loaded by pytest before any test runs.

import sys
from pathlib import Path

# Make sure the project root is on the Python path
# so test files can import project modules
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
