"""ML test configuration.

These tests exercise optional ``backend.ml`` backends. Mark the whole
directory so CI can run ``pytest -m 'not ml'`` on the slim image and
``pytest -m ml --extra ml`` when the heavy stack is installed.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.ml
