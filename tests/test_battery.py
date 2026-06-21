# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

import pytest

from custom_components.flipr_local.battery import (
    BATTERY_CURVE,
    battery_percent_from_mv,
)


def test_clamps_above_and_below_the_curve():
    """Voltages outside the curve bounds clamp to 100% and 0%."""
    assert battery_percent_from_mv(3700) == 100  # above the plateau
    assert battery_percent_from_mv(3600) == 100  # first breakpoint
    assert battery_percent_from_mv(2800) == 0  # last breakpoint
    assert battery_percent_from_mv(2000) == 0  # below cut-off


def test_breakpoints_are_returned_exactly():
    """Each breakpoint maps to its declared percentage."""
    for mv, pct in BATTERY_CURVE:
        assert battery_percent_from_mv(mv) == round(pct)


def test_monotonic_non_decreasing_with_voltage():
    """A higher voltage never yields a lower percentage."""
    prev = -1
    for mv in range(2000, 3801, 10):
        pct = battery_percent_from_mv(mv)
        assert pct >= prev
        prev = pct


def test_plateau_reads_high():
    """The flat Li-SOCl2 plateau (~3.5-3.6 V) stays near full."""
    assert battery_percent_from_mv(3550) >= 95
    assert battery_percent_from_mv(3500) >= 90


def test_knee_collapses_fast():
    """The percentage drops steeply through the knee, unlike a linear map."""
    # A linear 2500->3600 map would read ~73% at 3.3 V; the curve must be lower.
    assert battery_percent_from_mv(3300) < 60
    assert battery_percent_from_mv(3100) < 20


def test_interpolates_between_breakpoints():
    """Midway between two breakpoints gives the midpoint percentage."""
    # Between (3400, 70) and (3300, 45): 3350 mV -> ~57.5 -> 58 after rounding.
    assert battery_percent_from_mv(3350) == pytest.approx(58, abs=1)
