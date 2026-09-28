# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.
"""Pure decoding (no Home Assistant, no Bluetooth) of Flipr BLE frames.

Frame layout (13 bytes, little-endian):

    bytes 0-1    raw temperature        (x 0.06 -> °C)
    bytes 2-3    raw pH                 (mV)
    bytes 4-5    raw ORP                (/ 2 -> mV)
    byte  8      sync mode              (0-3)
    bytes 11-12  battery voltage        (mV)

Bytes 6-7 and 9-10 are not decoded here (unused/reserved by the device
protocol) but carry a rolling counter/checksum that changes on every
transmitted frame, even when the measured values are unchanged. This
guarantees two consecutive frames are never byte-identical, which
coordinator.py relies on to detect a fresh reading (see reference_frame_bytes).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .const import (
    BATTERY_MAX_MV,
    BATTERY_MIN_MV,
    FRAME_LENGTH_BYTES,
    VALID_SYNC_MODES,
)

_LOGGER = logging.getLogger(__name__)

TEMP_MIN_PLAUSIBLE = 0.0
TEMP_MAX_PLAUSIBLE = 50.0
ORP_MIN_PLAUSIBLE = 0.0
ORP_MAX_PLAUSIBLE = 1500.0
PH_MV_MIN_PLAUSIBLE = 500
PH_MV_MAX_PLAUSIBLE = 3000
BAT_MIN_PLAUSIBLE = BATTERY_MIN_MV - 500
BAT_MAX_PLAUSIBLE = BATTERY_MAX_MV + 500

_TEMP_FACTOR = 0.06
_ORP_DIVISOR = 2.0
_BATTERY_DENOM = max(BATTERY_MAX_MV - BATTERY_MIN_MV, 1)


@dataclass(frozen=True, slots=True)
class FliprFrame:
    """Raw (uncalibrated) values contained in a Flipr frame."""

    temperature: float
    ph_mv: int
    orp: float
    sync_mode: str | None
    battery_mv: int


def is_standby_frame(data: bytes) -> bool:
    """Whether the frame is from a sensor in standby (zero temperature)."""
    return data[:2] == b"\x00\x00"


def parse_frame(data: bytes) -> FliprFrame | None:
    """Decode a frame; returns None if it is invalid or implausible."""
    if len(data) != FRAME_LENGTH_BYTES:
        _LOGGER.debug(
            "Invalid frame length: %d bytes (expected %d)",
            len(data),
            FRAME_LENGTH_BYTES,
        )
        return None

    temperature = int.from_bytes(data[0:2], "little") * _TEMP_FACTOR
    ph_mv = int.from_bytes(data[2:4], "little")
    orp = int.from_bytes(data[4:6], "little") / _ORP_DIVISOR
    sync_raw = str(data[8])
    battery_mv = int.from_bytes(data[11:13], "little")

    if not PH_MV_MIN_PLAUSIBLE <= ph_mv <= PH_MV_MAX_PLAUSIBLE:
        _LOGGER.warning("Implausible pH raw value %d mV", ph_mv)
        return None
    if not TEMP_MIN_PLAUSIBLE <= temperature <= TEMP_MAX_PLAUSIBLE:
        _LOGGER.warning("Implausible temperature value %.2f", temperature)
        return None
    if not ORP_MIN_PLAUSIBLE <= orp <= ORP_MAX_PLAUSIBLE:
        _LOGGER.warning("Implausible ORP value %.1f mV", orp)
        return None
    if not BAT_MIN_PLAUSIBLE <= battery_mv <= BAT_MAX_PLAUSIBLE:
        _LOGGER.warning("Implausible battery value %d mV", battery_mv)
        return None

    return FliprFrame(
        temperature=temperature,
        ph_mv=ph_mv,
        orp=orp,
        sync_mode=sync_raw if sync_raw in VALID_SYNC_MODES else None,
        battery_mv=battery_mv,
    )


def battery_percent(battery_mv: float) -> int:
    """Convert a voltage (mV) to a percentage bounded to [0, 100]."""
    pct = (battery_mv - BATTERY_MIN_MV) / _BATTERY_DENOM * 100.0
    return round(max(0.0, min(pct, 100.0)))
