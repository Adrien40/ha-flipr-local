"""BLE frame decoding: layout, plausibility bounds, robustness."""

from __future__ import annotations

import dataclasses

import pytest
from hypothesis import given
from hypothesis import strategies as st

from custom_components.flipr_local.const import BATTERY_MAX_MV, BATTERY_MIN_MV
from custom_components.flipr_local.frame import (
    BAT_MAX_PLAUSIBLE,
    BAT_MIN_PLAUSIBLE,
    ORP_MAX_PLAUSIBLE,
    PH_MV_MAX_PLAUSIBLE,
    PH_MV_MIN_PLAUSIBLE,
    TEMP_MAX_PLAUSIBLE,
    FliprFrame,
    battery_percent,
    is_standby_frame,
    parse_frame,
)

from .helpers import STANDBY_FRAME, build_frame


def _raw(temp_raw=None, ph=None, orp_raw=None, sync=None, battery=None) -> bytes:
    """Frame built from *raw* values (before conversion)."""
    frame = bytearray(build_frame())
    if temp_raw is not None:
        frame[0:2] = temp_raw.to_bytes(2, "little")
    if ph is not None:
        frame[2:4] = ph.to_bytes(2, "little")
    if orp_raw is not None:
        frame[4:6] = orp_raw.to_bytes(2, "little")
    if sync is not None:
        frame[8] = sync
    if battery is not None:
        frame[11:13] = battery.to_bytes(2, "little")
    return bytes(frame)


class TestParseFrame:
    def test_decodes_all_fields(self):
        frame = parse_frame(
            build_frame(
                temp_c=25.02, ph_mv=1600, orp_mv=700, sync_mode=2, battery_mv=3300
            )
        )
        assert frame == FliprFrame(
            temperature=pytest.approx(25.02),
            ph_mv=1600,
            orp=700.0,
            sync_mode="2",
            battery_mv=3300,
        )

    def test_byte_layout_is_little_endian(self):
        # 0x0410 = 1040 → ph 1040 mV ; 0x0BB8 = 3000 → ORP 1500 mV
        frame = parse_frame(_raw(ph=0x0410, orp_raw=0x0BB8))
        assert frame.ph_mv == 1040
        assert frame.orp == 1500.0

    @pytest.mark.parametrize("length", [0, 1, 12, 14, 26])
    def test_wrong_length_is_rejected(self, length):
        assert parse_frame(bytes(build_frame())[:1] * length) is None

    def test_frame_is_immutable(self):
        frame = parse_frame(build_frame())
        with pytest.raises(dataclasses.FrozenInstanceError):
            frame.ph_mv = 0  # type: ignore[misc]

    # -- plausibility bounds: boundary value accepted, +1 rejected ----------
    @pytest.mark.parametrize(
        ("ph", "valid"),
        [
            (PH_MV_MIN_PLAUSIBLE - 1, False),
            (PH_MV_MIN_PLAUSIBLE, True),
            (PH_MV_MAX_PLAUSIBLE, True),
            (PH_MV_MAX_PLAUSIBLE + 1, False),
            (0, False),
            (65535, False),
        ],
    )
    def test_ph_mv_bounds(self, ph, valid):
        assert (parse_frame(_raw(ph=ph)) is not None) is valid

    @pytest.mark.parametrize(
        ("temp_raw", "valid"),
        [
            (1, True),
            (int(TEMP_MAX_PLAUSIBLE / 0.06), True),  # 833 → 49.98 °C
            (int(TEMP_MAX_PLAUSIBLE / 0.06) + 1, False),  # 834 → 50.04 °C
            (65535, False),
        ],
    )
    def test_temperature_bounds(self, temp_raw, valid):
        assert (parse_frame(_raw(temp_raw=temp_raw)) is not None) is valid

    @pytest.mark.parametrize(
        ("orp_raw", "valid"),
        [
            (0, True),
            (int(ORP_MAX_PLAUSIBLE * 2), True),  # 1500.0 mV
            (int(ORP_MAX_PLAUSIBLE * 2) + 1, False),  # 1500.5 mV
            (65535, False),
        ],
    )
    def test_orp_bounds(self, orp_raw, valid):
        assert (parse_frame(_raw(orp_raw=orp_raw)) is not None) is valid

    @pytest.mark.parametrize(
        ("battery", "valid"),
        [
            (BAT_MIN_PLAUSIBLE - 1, False),
            (BAT_MIN_PLAUSIBLE, True),
            (BAT_MAX_PLAUSIBLE, True),
            (BAT_MAX_PLAUSIBLE + 1, False),
            (0, False),
        ],
    )
    def test_battery_bounds(self, battery, valid):
        assert (parse_frame(_raw(battery=battery)) is not None) is valid

    @pytest.mark.parametrize("mode", [0, 1, 2, 3])
    def test_valid_sync_modes(self, mode):
        assert parse_frame(_raw(sync=mode)).sync_mode == str(mode)

    @pytest.mark.parametrize("mode", [4, 9, 128, 255])
    def test_unknown_sync_mode_becomes_none(self, mode):
        """Unknown mode: the measurement stays usable, only the mode is ignored."""
        frame = parse_frame(_raw(sync=mode))
        assert frame is not None
        assert frame.sync_mode is None

    @given(st.binary(min_size=0, max_size=40))
    def test_arbitrary_bytes_never_crash(self, data):
        frame = parse_frame(data)
        if frame is not None:
            assert len(data) == 13
            assert PH_MV_MIN_PLAUSIBLE <= frame.ph_mv <= PH_MV_MAX_PLAUSIBLE
            assert 0 <= frame.temperature <= TEMP_MAX_PLAUSIBLE
            assert 0 <= frame.orp <= ORP_MAX_PLAUSIBLE
            assert BAT_MIN_PLAUSIBLE <= frame.battery_mv <= BAT_MAX_PLAUSIBLE


class TestStandby:
    def test_zero_frame_is_standby(self):
        assert is_standby_frame(STANDBY_FRAME)

    def test_zero_temperature_prefix_is_standby(self):
        assert is_standby_frame(b"\x00\x00" + b"\x01" * 11)

    def test_real_frame_is_not_standby(self):
        assert not is_standby_frame(build_frame())

    def test_empty_is_not_standby(self):
        assert not is_standby_frame(b"")

    def test_standby_frame_is_also_invalid_for_parsing(self):
        """Raw pH at 0 mV is implausible: the standby frame does not pass."""
        assert parse_frame(STANDBY_FRAME) is None


class TestBatteryPercent:
    @pytest.mark.parametrize(
        ("mv", "expected"),
        [
            (BATTERY_MIN_MV, 0),
            (BATTERY_MAX_MV, 100),
            ((BATTERY_MIN_MV + BATTERY_MAX_MV) / 2, 50),
            (BATTERY_MIN_MV - 400, 0),  # below the minimum: clamped
            (BATTERY_MAX_MV + 400, 100),  # above the maximum: clamped
        ],
    )
    def test_values(self, mv, expected):
        assert battery_percent(mv) == expected

    @given(st.integers(min_value=0, max_value=65535))
    def test_always_within_0_100_and_int(self, mv):
        pct = battery_percent(mv)
        assert isinstance(pct, int)
        assert 0 <= pct <= 100

    @given(st.integers(0, 65534))
    def test_monotonic(self, mv):
        assert battery_percent(mv) <= battery_percent(mv + 1)


class TestBoundsWithLiteralValues:
    """The bounds are hardcoded here: a test that reads the code's constants
    would not catch a constant accidentally changed."""

    @pytest.mark.parametrize(
        ("kwargs", "valid"),
        [
            ({"ph": 500}, True),
            ({"ph": 499}, False),
            ({"ph": 3000}, True),
            ({"ph": 3001}, False),
            ({"temp_raw": 833}, True),  # 49.98 °C
            ({"temp_raw": 834}, False),  # 50.04 °C
            ({"orp_raw": 3000}, True),  # 1500.0 mV
            ({"orp_raw": 3001}, False),
            ({"battery": 2000}, True),
            ({"battery": 1999}, False),
            ({"battery": 4100}, True),
            ({"battery": 4101}, False),
        ],
    )
    def test_boundary(self, kwargs, valid):
        assert (parse_frame(_raw(**kwargs)) is not None) is valid
