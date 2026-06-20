"""Shared pytest configuration for the scoring_service test suite.

The ``Role-5-Implementation.md`` test command relies on
``PYTHONPATH='platform;.'``. This conftest ensures the project root is
importable when tests are invoked without that env var.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _ensure_on_path(path: Path) -> None:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


# Ensure both the project root and the platform package are importable.
_ensure_on_path(_PROJECT_ROOT)
_ensure_on_path(_PROJECT_ROOT / "platform")
