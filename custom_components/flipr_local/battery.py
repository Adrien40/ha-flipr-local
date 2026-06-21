# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

# State-of-charge model for the Saft LS26500 (Li-SOCl2) primary cell used by the
# Flipr AnalysR.
#
# Li-SOCl2 chemistry has a very flat discharge plateau (~3.5-3.6 V for almost the
# whole life), followed by a sharp "knee" that drops to the 2.0 V cut-off in the
# last few percent of capacity. A plain linear voltage->percent mapping is
# therefore misleading: it would read near-full for almost the entire life, then
# collapse with no warning. This piecewise curve keeps ~100% across the plateau
# and concentrates the resolution in the knee, where the voltage is actually
# informative.
#
# Datasheet: Saft LS26500, 3.6 V nominal, OCV ~3.67 V, 7.7 Ah, 2.0 V cut-off;
# fresh cells stay above 3.0 V even under 300 mA pulses.
#
# Breakpoints are (millivolts, percent), ordered from full to empty. They are a
# first-pass calibration of the published Li-SOCl2 discharge curve and can be
# refined with real field readings.
BATTERY_CURVE: tuple[tuple[int, float], ...] = (
    (3600, 100.0),
    (3550, 99.0),
    (3500, 95.0),
    (3450, 85.0),
    (3400, 70.0),
    (3300, 45.0),
    (3200, 25.0),
    (3100, 12.0),
    (3000, 5.0),
    (2900, 2.0),
    (2800, 0.0),
)


def battery_percent_from_mv(mv: float) -> int:
    """Map a cell voltage (mV) to a state-of-charge percent via the Li-SOCl2 curve.

    At or above the first breakpoint the result is 100%, at or below the last it
    is 0%, and it is linearly interpolated between adjacent breakpoints.
    """
    points = BATTERY_CURVE
    if mv >= points[0][0]:
        return int(round(points[0][1]))
    if mv <= points[-1][0]:
        return int(round(points[-1][1]))

    for (hi_mv, hi_pct), (lo_mv, lo_pct) in zip(points, points[1:]):
        if lo_mv <= mv <= hi_mv:
            fraction = (mv - lo_mv) / (hi_mv - lo_mv)
            return int(round(lo_pct + fraction * (hi_pct - lo_pct)))

    # Defensive: the loop above covers the whole range between the bounds.
    return int(round(points[-1][1]))
