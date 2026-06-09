from __future__ import annotations

from typing import Any


def clamp(value: Any, low: float = 0.0, high: float = 100.0, default: float = 0.0) -> float:
    try: number = float(value)
    except (TypeError, ValueError): number = default
    return round(max(low, min(high, number)), 4)


def ratio(value: Any) -> float:
    return clamp(value, 0.0, 1.0)


def score(value: Any) -> float:
    return clamp(value, 0.0, 100.0)


def average_available(values: list[Any]) -> float | None:
    available = [float(value) for value in values if value is not None]
    return round(sum(available) / len(available), 2) if available else None
