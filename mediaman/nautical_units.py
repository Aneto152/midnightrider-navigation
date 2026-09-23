"""Canonical nautical-unit and circular-angle helpers for MediaMan analysis."""

from __future__ import annotations

import math
from collections.abc import Iterable

METERS_PER_SECOND_TO_KNOTS = 1.9438444924406


def meters_per_second_to_knots(value: float) -> float:
    """Convert a speed from m/s to knots."""
    return value * METERS_PER_SECOND_TO_KNOTS


def knots_to_meters_per_second(value: float) -> float:
    """Convert a speed from knots to m/s."""
    return value / METERS_PER_SECOND_TO_KNOTS


def wrap_degrees(value: float) -> float:
    """Wrap an angle to the interval [-180, 180)."""
    return (value + 180.0) % 360.0 - 180.0


def circular_delta_degrees(start: float, end: float) -> float:
    """Return the signed shortest angular change from start to end."""
    return wrap_degrees(end - start)


def circular_mean_degrees(values: Iterable[float]) -> float:
    """Return the circular mean in degrees, or raise for an empty iterable."""
    values = tuple(values)
    if not values:
        raise ValueError("circular mean requires at least one value")
    sine = sum(math.sin(math.radians(value)) for value in values)
    cosine = sum(math.cos(math.radians(value)) for value in values)
    return (math.degrees(math.atan2(sine, cosine)) + 360.0) % 360.0
