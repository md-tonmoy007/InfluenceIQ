"""Shared pytest configuration for the backend.tests.integration suite."""
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _ensure_on_path(path: Path) -> None:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


_ensure_on_path(_PROJECT_ROOT)
_ensure_on_path(_PROJECT_ROOT / "platform")
