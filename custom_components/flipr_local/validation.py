# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.
"""Conversion and validation of form inputs (pure functions).

Separated from config_flow.py, which depends on the Home Assistant UI.
"""

from __future__ import annotations

import math
from typing import Any

from .chemistry import get_mv_from_input
from .const import (
    CONF_CYA,
    CONF_ORP_CALIB,
    CONF_ORP_MAX,
    CONF_ORP_MIN,
    CONF_ORP_REF,
    CONF_PH_CALIB_4,
    CONF_PH_CALIB_7,
    CONF_PH_MAX,
    CONF_PH_MIN,
    CONF_PH_REF_4,
    CONF_PH_REF_7,
    CONF_TEMP_MAX,
    CONF_TEMP_MIN,
    CONF_TEMP_OFFSET,
    DEFAULT_PH_CALIB_4,
    DEFAULT_PH_CALIB_7,
    DEFAULT_PH_REF_4,
    DEFAULT_PH_REF_7,
)


def _to_float(val: object) -> float:
    if isinstance(val, str):
        val = val.replace(",", ".")
    if not isinstance(val, (str, int, float)):
        raise ValueError(f"{val!r} is not a valid calibration value")
    result = float(val)
    if math.isnan(result) or math.isinf(result):
        raise ValueError("NaN/Inf is not a valid calibration value")
    return result


def _flatten_sections(user_input: dict[str, Any]) -> dict[str, Any]:
    """Merge section (dict) values into a flat dict.

    FIX: Unified helper used by both async_step_user and async_step_init.
    Section (dict) values take priority over any same-named top-level keys,
    since section values are more specific. This was previously inconsistent:
    - async_step_user: top-level keys written first, dicts could overwrite them.
    - async_step_init: dicts written first, top-level keys used setdefault (no override).
    Both forms now follow the same rule: dict/section values win.
    """
    flat: dict[str, Any] = {}
    # Pass 1: collect all section (dict) values.
    for value in user_input.values():
        if isinstance(value, dict):
            flat.update(value)
    # Pass 2: add top-level scalars only if the key wasn't already set by a section.
    for k, v in user_input.items():
        if not isinstance(v, dict):
            flat.setdefault(k, v)
    return flat


def validate_calibration(data: dict[str, Any]) -> dict[str, Any] | tuple[str, str]:
    try:
        raw_c4 = _to_float(data.get(CONF_PH_CALIB_4, DEFAULT_PH_CALIB_4))
        raw_c7 = _to_float(data.get(CONF_PH_CALIB_7, DEFAULT_PH_CALIB_7))
        ref4 = _to_float(data.get(CONF_PH_REF_4, DEFAULT_PH_REF_4))
        ref7 = _to_float(data.get(CONF_PH_REF_7, DEFAULT_PH_REF_7))
    # PEP 758 (Python 3.14): parentheses are optional when there is no `as` clause. Intentional.
    except ValueError, TypeError:
        return (CONF_PH_CALIB_4, "unknown")

    try:
        if CONF_PH_MIN in data and CONF_PH_MAX in data:
            ph_min = _to_float(data[CONF_PH_MIN])
            ph_max = _to_float(data[CONF_PH_MAX])
            if ph_min >= ph_max:
                return (CONF_PH_MIN, "ph_threshold_error")
    # PEP 758 (Python 3.14): parentheses are optional when there is no `as` clause. Intentional.
    except ValueError, TypeError:
        return (CONF_PH_MIN, "unknown")

    try:
        if CONF_TEMP_MIN in data and CONF_TEMP_MAX in data:
            temp_min = _to_float(data[CONF_TEMP_MIN])
            temp_max = _to_float(data[CONF_TEMP_MAX])
            if temp_min >= temp_max:
                return (CONF_TEMP_MIN, "temp_threshold_error")
    # PEP 758 (Python 3.14): parentheses are optional when there is no `as` clause. Intentional.
    except ValueError, TypeError:
        return (CONF_TEMP_MIN, "unknown")

    try:
        if CONF_ORP_MIN in data and CONF_ORP_MAX in data:
            orp_min = int(_to_float(data[CONF_ORP_MIN]))
            orp_max = int(_to_float(data[CONF_ORP_MAX]))
            if orp_min >= orp_max:
                return (CONF_ORP_MIN, "orp_threshold_error")
    # PEP 758 (Python 3.14): parentheses are optional when there is no `as` clause. Intentional.
    except ValueError, TypeError:
        return (CONF_ORP_MIN, "unknown")

    try:
        c4_mv = get_mv_from_input(raw_c4)
    except ValueError:
        return (CONF_PH_CALIB_4, "ph_mv_out_of_range")

    try:
        c7_mv = get_mv_from_input(raw_c7)
    except ValueError:
        return (CONF_PH_CALIB_7, "ph_mv_out_of_range")

    if ref4 < 2.5 or ref4 > 5.5 or ref7 < 6.5 or ref7 > 7.5:
        return (CONF_PH_REF_4, "ph_ref_out_of_range")
    if abs(c7_mv - c4_mv) < 1.0:
        return (CONF_PH_CALIB_7, "ph_calibration_equal")
    if abs(ref7 - ref4) < 0.01:
        return (CONF_PH_REF_7, "ph_reference_equal")
    if c7_mv > c4_mv:
        return (CONF_PH_CALIB_7, "ph_slope_mismatch")

    normalized = dict(data)
    normalized[CONF_PH_CALIB_4] = raw_c4
    normalized[CONF_PH_CALIB_7] = raw_c7
    normalized[CONF_PH_REF_4] = ref4
    normalized[CONF_PH_REF_7] = ref7

    for key, cast in (
        (CONF_ORP_REF, int),
        (CONF_ORP_CALIB, int),
        (CONF_TEMP_OFFSET, float),
        (CONF_CYA, int),
    ):
        if key in data:
            try:
                normalized[key] = cast(_to_float(data[key]))
            # PEP 758 (Python 3.14): parentheses are optional when there is no `as` clause. Intentional.
            except ValueError, TypeError:
                return (key, "unknown")

    return normalized
