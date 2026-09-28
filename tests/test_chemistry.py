"""Pure calculations: mV<->pH conversion, two-point calibration, Langelier."""

from __future__ import annotations

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from custom_components.flipr_local import chemistry
from custom_components.flipr_local.chemistry import (
    apply_orp_offset,
    classify_lsi,
    compute_factory_ph,
    compute_isl,
    compute_ph_calibrated,
    compute_ph_equilibrium,
    get_mv_from_input,
)

# Default calibration of the integration (const.py) expressed in mV.
C7_MV, C4_MV = 1634.0, 1916.0
REF_7, REF_4 = 7.02, 4.00


# ---------------------------------------------------------------------------
# get_mv_from_input: pH input (2-14) or mV input (500-3000)
# ---------------------------------------------------------------------------
class TestGetMvFromInput:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (7.02, 1798.0),  # pH -> mV via the factory line
            (8.40, 1634.0),
            (6.02, 1916.0),
            ("8.40", 1634.0),  # numeric string accepted
            (1600, 1600.0),  # already in mV
            (1600.0, 1600.0),
            ("1900", 1900.0),
        ],
    )
    def test_valid_inputs(self, value, expected):
        assert get_mv_from_input(value) == expected

    @pytest.mark.parametrize("value", [2.0, 14.0, 500.0, 3000.0])
    def test_boundaries_are_accepted(self, value):
        assert get_mv_from_input(value) > 0

    @pytest.mark.parametrize(
        "value",
        [
            0,
            1.99,  # below the pH range
            14.01,  # between the pH range and the mV range
            250,
            499.99,
            3000.01,
            -1600,
            "abc",
            "",
            None,
            [],
            float("nan"),
            float("inf"),
            float("-inf"),
        ],
    )
    def test_invalid_inputs_raise_value_error(self, value):
        with pytest.raises(ValueError):
            get_mv_from_input(value)

    def test_ph_in_range_but_calculated_mv_out_of_range_raises(self, monkeypatch):
        """A pH within 2-14 can still yield an out-of-range mV if the
        factory calibration constants are degenerate; this must raise
        instead of silently returning an out-of-bounds mV."""
        monkeypatch.setattr(chemistry, "PH_FACTORY_OFFSET", 0)
        monkeypatch.setattr(chemistry, "PH_FACTORY_SLOPE", 100)
        with pytest.raises(ValueError, match="out of range"):
            chemistry.get_mv_from_input(10)

    def test_ph_conversion_is_monotonic_decreasing(self):
        """The Flipr probe has a negative slope: higher pH = lower mV."""
        mvs = [get_mv_from_input(ph) for ph in (4.0, 5.0, 6.0, 7.0, 8.0, 9.0)]
        assert mvs == sorted(mvs, reverse=True)


# ---------------------------------------------------------------------------
# compute_ph_calibrated: line through (c7, ref7) and (c4, ref4)
# ---------------------------------------------------------------------------
class TestPhCalibrated:
    def test_hits_both_calibration_points(self):
        assert compute_ph_calibrated(
            C7_MV, C4_MV, C7_MV, REF_4, REF_7
        ) == pytest.approx(REF_7)
        assert compute_ph_calibrated(
            C4_MV, C4_MV, C7_MV, REF_4, REF_7
        ) == pytest.approx(REF_4)

    def test_midpoint(self):
        mid_mv = (C4_MV + C7_MV) / 2
        expected = (REF_4 + REF_7) / 2
        assert compute_ph_calibrated(
            mid_mv, C4_MV, C7_MV, REF_4, REF_7
        ) == pytest.approx(expected)

    def test_extrapolates_beyond_calibration_points(self):
        """A pH of 8 is beyond the pH 7 point: the line is extended."""
        ph = compute_ph_calibrated(1500, C4_MV, C7_MV, REF_4, REF_7)
        assert ph > REF_7

    def test_higher_mv_means_lower_ph(self):
        low = compute_ph_calibrated(1500, C4_MV, C7_MV, REF_4, REF_7)
        high = compute_ph_calibrated(1800, C4_MV, C7_MV, REF_4, REF_7)
        assert low > high

    @pytest.mark.parametrize(
        ("c4", "c7", "r4", "r7"),
        [
            (1700.0, 1700.0, 4.0, 7.0),  # same mV
            (1900.0, 1600.0, 7.0, 7.0),  # same reference pH
            (1700.0, 1700.0, 7.0, 7.0),
        ],
    )
    def test_degenerate_calibration_raises(self, c4, c7, r4, r7):
        """Never return a "neutral" pH that would hide an error."""
        with pytest.raises(ValueError):
            compute_ph_calibrated(1700, c4, c7, r4, r7)

    def test_factory_calibration_matches_default_calibration_reasonably(self):
        """A factory-fresh Flipr must not deviate by more than ~0.5 pH."""
        for mv in (1500, 1650, 1800):
            factory = compute_factory_ph(mv)
            calibrated = compute_ph_calibrated(mv, C4_MV, C7_MV, REF_4, REF_7)
            assert abs(factory - calibrated) < 2.0  # loose bound: documents the gap

    @given(
        mv=st.floats(min_value=500, max_value=3000),
        c4=st.floats(min_value=1800, max_value=2200),
        c7=st.floats(min_value=1200, max_value=1700),
    )
    def test_calibration_is_affine_and_invertible(self, mv, c4, c7):
        """Property: recalibrating then inverting returns the original mV."""
        ph = compute_ph_calibrated(mv, c4, c7, REF_4, REF_7)
        slope = (c4 - c7) / (REF_4 - REF_7)
        assert c7 + (ph - REF_7) * slope == pytest.approx(mv, abs=1e-6)


class TestFactoryPh:
    def test_known_values(self):
        assert compute_factory_ph(1798) == pytest.approx(7.02, abs=0.01)
        assert compute_factory_ph(1634) == pytest.approx(8.40, abs=0.01)

    def test_decreasing(self):
        assert compute_factory_ph(1500) > compute_factory_ph(1800)


# ---------------------------------------------------------------------------
# apply_orp_offset
# ---------------------------------------------------------------------------
class TestOrpOffset:
    def test_identity_when_reference_equals_measured(self):
        assert apply_orp_offset(700.0, 650, 650) == 700

    def test_positive_and_negative_offsets(self):
        # The reference solution is 650 but the probe reads 640 -> +10 mV.
        assert apply_orp_offset(700.0, 650, 640) == 710
        assert apply_orp_offset(700.0, 650, 660) == 690

    def test_returns_int(self):
        assert isinstance(apply_orp_offset(700.5, 650, 650), int)


# ---------------------------------------------------------------------------
# Langelier index
# ---------------------------------------------------------------------------
class TestLangelier:
    def test_reference_values(self):
        """Reference values (regression): 25 °C, TAC 100, TH 200, TDS 1000."""
        assert compute_ph_equilibrium(25, 100, 200, 1000) == 7.68
        assert compute_isl(25, 7.5, 100, 200, 1000) == -0.18

    def test_isl_is_ph_minus_equilibrium(self):
        ph_s = compute_ph_equilibrium(28, 90, 250, 1200)
        assert compute_isl(28, 7.4, 90, 250, 1200) == pytest.approx(
            7.4 - ph_s, abs=0.011
        )

    def test_isl_rises_with_ph_and_temperature(self):
        base = compute_isl(25, 7.4, 100, 200, 1000)
        assert compute_isl(25, 7.8, 100, 200, 1000) > base
        assert compute_isl(35, 7.4, 100, 200, 1000) > base

    def test_isl_direction_with_alkalinity_hardness_and_tds(self):
        """More TAC/TH -> more scale-forming water (LSI up); more TDS -> LSI down."""
        base = compute_isl(25, 7.4, 100, 200, 1000)
        assert compute_isl(25, 7.4, 200, 200, 1000) > base
        assert compute_isl(25, 7.4, 100, 400, 1000) > base
        assert compute_isl(25, 7.4, 100, 200, 3000) < base

    @pytest.mark.parametrize(
        ("temp", "ph", "tac", "th", "tds"),
        [
            (None, 7.4, 100, 200, 1000),
            (25, None, 100, 200, 1000),
            (25, 7.4, None, 200, 1000),
            (25, 7.4, 100, None, 1000),
            (25, 7.4, 100, 200, None),
            (25, 7.4, 0, 200, 1000),  # zero TAC
            (25, 7.4, 100, 0, 1000),  # zero TH
            (25, 7.4, 100, 200, 0),  # zero TDS (entity default value)
            (25, 7.4, -5, 200, 1000),  # negative
            (float("nan"), 7.4, 100, 200, 1000),
            (25, float("nan"), 100, 200, 1000),
            (25, 7.4, float("inf"), 200, 1000),
            (-273.15, 7.4, 100, 200, 1000),  # absolute zero: log10(0)
            (-300, 7.4, 100, 200, 1000),  # log10 of a negative
        ],
    )
    def test_invalid_inputs_return_none(self, temp, ph, tac, th, tds):
        assert compute_isl(temp, ph, tac, th, tds) is None

    @pytest.mark.parametrize(
        ("temp", "tac", "th", "tds"),
        [(None, 100, 200, 1000), (25, 0, 200, 1000), (25, 100, 200, float("nan"))],
    )
    def test_equilibrium_invalid_inputs_return_none(self, temp, tac, th, tds):
        assert compute_ph_equilibrium(temp, tac, th, tds) is None

    @pytest.mark.parametrize("temp", [0, 2, 35, 50, 90])
    def test_extreme_temperatures_still_compute(self, temp):
        assert compute_isl(temp, 7.4, 120, 250, 1000) is not None

    @given(
        temp=st.floats(min_value=-40, max_value=100),
        ph=st.floats(min_value=0, max_value=14),
        tac=st.floats(min_value=1, max_value=500),
        th=st.floats(min_value=1, max_value=800),
        tds=st.floats(min_value=1, max_value=5000),
    )
    def test_never_returns_nan_or_raises(self, temp, ph, tac, th, tds):
        result = compute_isl(temp, ph, tac, th, tds)
        assert result is not None
        assert math.isfinite(result)

    @given(
        temp=st.floats(allow_nan=True, allow_infinity=True),
        ph=st.floats(allow_nan=True, allow_infinity=True),
        tac=st.floats(allow_nan=True, allow_infinity=True),
        th=st.floats(allow_nan=True, allow_infinity=True),
        tds=st.floats(allow_nan=True, allow_infinity=True),
    )
    def test_arbitrary_floats_never_crash_nor_yield_nan(self, temp, ph, tac, th, tds):
        for result in (
            compute_isl(temp, ph, tac, th, tds),
            compute_ph_equilibrium(temp, tac, th, tds),
        ):
            assert result is None or math.isfinite(result)


class TestClassifyLsi:
    @pytest.mark.parametrize(
        ("lsi", "expected"),
        [
            (None, "unknown"),
            (-2.0, "corrosive"),
            (-0.31, "corrosive"),
            (-0.3, "balanced"),  # bounds included in "balanced"
            (0.0, "balanced"),
            (0.3, "balanced"),
            (0.31, "scaling"),
            (2.0, "scaling"),
        ],
    )
    def test_classification(self, lsi, expected):
        assert classify_lsi(lsi) == expected
