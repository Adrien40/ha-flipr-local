# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.
"""Pure calculations: probe calibration and water chemistry (Langelier)."""

from __future__ import annotations

import logging
import math

from .const import PH_FACTORY_OFFSET, PH_FACTORY_SLOPE

_LOGGER = logging.getLogger(__name__)

PH_MIN_VALID = 0.0
PH_MAX_VALID = 14.0


def get_mv_from_input(val: float | int | str) -> float:
    """Convert a user input (pH 2-14 or mV 500-3000) to mV."""
    try:
        val_f = float(val)
    # PEP 758 (Python 3.14): parentheses are optional when there is no `as` clause. Intentional.
    except ValueError, TypeError:
        _LOGGER.error("Invalid calibration value: %s", val)
        raise ValueError("Invalid format") from None

    if not math.isfinite(val_f):
        raise ValueError(f"Value {val_f} is not finite")

    if 2.0 <= val_f <= 14.0:
        mv = round((val_f - PH_FACTORY_OFFSET) / PH_FACTORY_SLOPE)
        if not (500 <= mv <= 3000):
            raise ValueError(f"Calculated mV {mv} out of range")
        return float(mv)

    if 500 <= val_f <= 3000:
        return val_f

    raise ValueError(f"Value {val_f} out of bounds")


def compute_ph_calibrated(
    ph_raw_mv: float,
    c4_mv: float,
    c7_mv: float,
    ph_ref_4: float,
    ph_ref_7: float,
) -> float:
    """pH calibrated via the line through the two calibration points.

    Raises ValueError if the calibration is degenerate (points coincide):
    returning a "neutral" value like 7.0 would mask a miscalibration.
    """
    ref_delta = ph_ref_4 - ph_ref_7
    mv_delta = float(c4_mv) - float(c7_mv)
    if abs(ref_delta) < 1e-9 or abs(mv_delta) < 1e-9:
        raise ValueError("Degenerate pH calibration")
    slope = mv_delta / ref_delta
    return ph_ref_7 + (ph_raw_mv - float(c7_mv)) / slope


def compute_factory_ph(ph_raw_mv: float) -> float:
    """pH from the factory calibration line."""
    return PH_FACTORY_SLOPE * ph_raw_mv + PH_FACTORY_OFFSET


def apply_orp_offset(raw_orp: float, orp_ref: float, orp_measured: float) -> int:
    """Correct ORP by the measured/expected gap on a reference solution."""
    return round(raw_orp + (orp_ref - orp_measured))


def _all_finite(*values: float | None) -> bool:
    return all(v is not None and math.isfinite(v) for v in values)


def _compute_ph_s(temp_c: float, tac_c: float, th_c: float, tds_c: float) -> float:
    """Saturation pH (Langelier formula, temperature in Kelvin)."""
    a = (math.log10(max(1.0, tds_c)) - 1) / 10
    b = -13.12 * math.log10(temp_c + 273.15) + 34.55
    c = math.log10(max(1.0, th_c)) - 0.4
    d = math.log10(max(1.0, tac_c))
    return (9.3 + a + b) - (c + d)


def compute_isl(
    temp: float | None,
    ph: float | None,
    tac: float | None,
    th: float | None,
    tds: float | None,
) -> float | None:
    """Langelier Saturation Index; None if an input is missing/invalid."""
    if not _all_finite(temp, ph, tac, th, tds):
        return None
    assert temp is not None and ph is not None and tac is not None
    assert th is not None and tds is not None
    if tac <= 0 or th <= 0 or tds <= 0:
        return None
    try:
        ph_s = _compute_ph_s(float(temp), float(tac), float(th), float(tds))
        result = round(ph - ph_s, 2)
    except (ValueError, OverflowError, TypeError) as err:
        _LOGGER.debug("Error computing ISL: %s", err)
        return None
    return result if math.isfinite(result) else None


def compute_ph_equilibrium(
    temp: float | None,
    tac: float | None,
    th: float | None,
    tds: float | None,
) -> float | None:
    """Equilibrium (saturation) pH; None if an input is missing/invalid."""
    if not _all_finite(temp, tac, th, tds):
        return None
    assert temp is not None and tac is not None
    assert th is not None and tds is not None
    if tac <= 0 or th <= 0 or tds <= 0:
        return None
    try:
        result = round(_compute_ph_s(float(temp), float(tac), float(th), float(tds)), 2)
    except (ValueError, OverflowError, TypeError) as err:
        _LOGGER.debug("Error computing equilibrium pH: %s", err)
        return None
    return result if math.isfinite(result) else None


LSI_CORROSIVE_BELOW = -0.3
LSI_SCALING_ABOVE = 0.3


def classify_lsi(lsi: float | None) -> str:
    """Interpret the Langelier index: corrosive / balanced / scaling / unknown."""
    if lsi is None:
        return "unknown"
    if lsi < LSI_CORROSIVE_BELOW:
        return "corrosive"
    if lsi > LSI_SCALING_ABOVE:
        return "scaling"
    return "balanced"
