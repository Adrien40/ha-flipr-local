"""Config flow, options flow and calibration validation."""

from __future__ import annotations

from time import monotonic
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import voluptuous as vol
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import (
    SOURCE_BLUETOOTH,
    SOURCE_RECONFIGURE,
    SOURCE_USER,
)
from homeassistant.data_entry_flow import FlowResultType

from custom_components.flipr_local.const import (
    CONF_CHLORINE_MODEL,
    CONF_CYA,
    CONF_MAC_ADDRESS,
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
    CONF_REFERENCE_TIME,
    CONF_SCAN_INTERVAL,
    CONF_SYNC_MODE,
    CONF_TEMP_MAX,
    CONF_TEMP_MIN,
    CONF_TEMP_OFFSET,
    CONF_USE_GATEWAY,
    DOMAIN,
)
from custom_components.flipr_local.validation import (
    _flatten_sections,
    _to_float,
    validate_calibration,
)

from .conftest import make_entry
from .helpers import MAC

DISCOVERED = "custom_components.flipr_local.config_flow.async_discovered_service_info"
SETUP = "custom_components.flipr_local.async_setup_entry"


def _valid_calibration(**over) -> dict:
    data = {
        CONF_PH_CALIB_7: 8.40,
        CONF_PH_REF_7: 7.02,
        CONF_PH_CALIB_4: 6.02,
        CONF_PH_REF_4: 4.00,
        CONF_ORP_CALIB: 650,
        CONF_ORP_REF: 650,
        CONF_TEMP_OFFSET: 0.0,
    }
    data.update(over)
    return data


def _service_info(
    name: str = "Flipr 12345", address: str = MAC
) -> BluetoothServiceInfoBleak:
    device = BLEDevice(address, name, {})
    adv = AdvertisementData(
        local_name=name,
        manufacturer_data={},
        service_data={},
        service_uuids=[],
        rssi=-60,
        tx_power=None,
        platform_data=(),
    )
    return BluetoothServiceInfoBleak(
        name=name,
        address=address,
        rssi=-60,
        manufacturer_data={},
        service_data={},
        service_uuids=[],
        source="local",
        device=device,
        advertisement=adv,
        connectable=True,
        time=monotonic(),
        tx_power=None,
    )


def _user_input(mac: str, **cal) -> dict:
    return {
        CONF_MAC_ADDRESS: mac,
        "general": {
            CONF_USE_GATEWAY: True,
            CONF_CHLORINE_MODEL: "chlorine",
            CONF_CYA: 40,
        },
        "synchronization": {
            CONF_SCAN_INTERVAL: 60,
            CONF_REFERENCE_TIME: "08:00:00",
        },
        "probes_calibration": _valid_calibration(**cal),
    }


def _default_of(result, field: str):
    for key in result["data_schema"].schema:
        if key == field:
            return key.default()
    raise AssertionError(f"{field} not in schema")


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------
class TestToFloat:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [("7,02", 7.02), ("7.02", 7.02), (7, 7.0), (" 5 ", 5.0)],
    )
    def test_accepts_decimal_comma(self, value, expected):
        assert _to_float(value) == expected

    @pytest.mark.parametrize("value", ["abc", "", None, "nan", "inf", float("nan")])
    def test_rejects_invalid(self, value):
        with pytest.raises((ValueError, TypeError)):
            _to_float(value)


class TestFlattenSections:
    def test_merges_sections(self):
        assert _flatten_sections({"a": {"x": 1}, "b": {"y": 2}}) == {"x": 1, "y": 2}

    def test_keeps_top_level_scalars(self):
        assert _flatten_sections({"mac": "AA", "s": {"x": 1}}) == {"mac": "AA", "x": 1}

    def test_section_value_wins_over_top_level(self):
        assert _flatten_sections({"x": 1, "s": {"x": 2}}) == {"x": 2}

    def test_empty(self):
        assert _flatten_sections({}) == {}


class TestValidateCalibration:
    def test_defaults_are_valid(self):
        result = validate_calibration(_valid_calibration())
        assert isinstance(result, dict)

    def test_accepts_mv_values(self):
        result = validate_calibration(
            _valid_calibration(**{CONF_PH_CALIB_7: 1600, CONF_PH_CALIB_4: 1900})
        )
        assert isinstance(result, dict)

    def test_accepts_decimal_comma_strings(self):
        result = validate_calibration(
            _valid_calibration(**{CONF_PH_CALIB_7: "8,40", CONF_PH_REF_7: "7,02"})
        )
        assert result[CONF_PH_CALIB_7] == 8.40

    def test_normalizes_types(self):
        result = validate_calibration(
            _valid_calibration(
                **{
                    CONF_ORP_REF: "650.9",
                    CONF_ORP_CALIB: 640.2,
                    CONF_TEMP_OFFSET: "1,5",
                    CONF_CYA: "40.7",
                }
            )
        )
        assert result[CONF_ORP_REF] == 650
        assert result[CONF_ORP_CALIB] == 640
        assert result[CONF_TEMP_OFFSET] == 1.5
        assert result[CONF_CYA] == 40

    def test_uses_defaults_when_keys_missing(self):
        assert isinstance(validate_calibration({}), dict)

    @pytest.mark.parametrize(
        ("override", "expected"),
        [
            ({CONF_PH_CALIB_4: "abc"}, (CONF_PH_CALIB_4, "unknown")),
            ({CONF_PH_REF_7: None}, (CONF_PH_CALIB_4, "unknown")),
            ({CONF_PH_CALIB_7: 100}, (CONF_PH_CALIB_7, "ph_mv_out_of_range")),
            ({CONF_PH_CALIB_4: 5000}, (CONF_PH_CALIB_4, "ph_mv_out_of_range")),
            ({CONF_PH_REF_4: 2.0}, (CONF_PH_REF_4, "ph_ref_out_of_range")),
            ({CONF_PH_REF_4: 6.0}, (CONF_PH_REF_4, "ph_ref_out_of_range")),
            ({CONF_PH_REF_7: 6.0}, (CONF_PH_REF_4, "ph_ref_out_of_range")),
            ({CONF_PH_REF_7: 8.0}, (CONF_PH_REF_4, "ph_ref_out_of_range")),
            (
                {CONF_PH_CALIB_7: 1700, CONF_PH_CALIB_4: 1700},
                (CONF_PH_CALIB_7, "ph_calibration_equal"),
            ),
            # pH 4 must give MORE mV than pH 7 (probe's negative slope).
            (
                {CONF_PH_CALIB_7: 1900, CONF_PH_CALIB_4: 1600},
                (CONF_PH_CALIB_7, "ph_slope_mismatch"),
            ),
            # Regressions: these values used to raise an unhandled exception.
            ({CONF_ORP_REF: "abc"}, (CONF_ORP_REF, "unknown")),
            ({CONF_ORP_CALIB: "nan"}, (CONF_ORP_CALIB, "unknown")),
            ({CONF_TEMP_OFFSET: "x"}, (CONF_TEMP_OFFSET, "unknown")),
            ({CONF_CYA: "x"}, (CONF_CYA, "unknown")),
        ],
    )
    def test_error_codes(self, override, expected):
        assert validate_calibration(_valid_calibration(**override)) == expected

    @pytest.mark.parametrize(
        ("over", "expected"),
        [
            ({CONF_PH_MIN: 7.5, CONF_PH_MAX: 7.0}, (CONF_PH_MIN, "ph_threshold_error")),
            ({CONF_PH_MIN: 7.0, CONF_PH_MAX: 7.0}, (CONF_PH_MIN, "ph_threshold_error")),
            (
                {CONF_TEMP_MIN: 30, CONF_TEMP_MAX: 10},
                (CONF_TEMP_MIN, "temp_threshold_error"),
            ),
            (
                {CONF_ORP_MIN: 800, CONF_ORP_MAX: 650},
                (CONF_ORP_MIN, "orp_threshold_error"),
            ),
            ({CONF_PH_MIN: "x", CONF_PH_MAX: 7}, (CONF_PH_MIN, "unknown")),
            ({CONF_TEMP_MIN: "x", CONF_TEMP_MAX: 7}, (CONF_TEMP_MIN, "unknown")),
            ({CONF_ORP_MIN: "x", CONF_ORP_MAX: 7}, (CONF_ORP_MIN, "unknown")),
        ],
    )
    def test_threshold_errors(self, over, expected):
        assert validate_calibration(_valid_calibration(**over)) == expected

    def test_valid_thresholds_pass(self):
        result = validate_calibration(
            _valid_calibration(
                **{
                    CONF_PH_MIN: 6.9,
                    CONF_PH_MAX: 7.5,
                    CONF_ORP_MIN: 650,
                    CONF_ORP_MAX: 800,
                }
            )
        )
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Flux de configuration
# ---------------------------------------------------------------------------
async def test_bluetooth_discovery_creates_entry(hass):
    with (
        patch(DISCOVERED, return_value=[_service_info()]),
        patch(SETUP, return_value=True),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=_service_info()
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        selection = _default_of(result, CONF_MAC_ADDRESS)
        assert MAC in selection

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], _user_input(selection)
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_MAC_ADDRESS] == MAC
    assert result["result"].unique_id == MAC
    options = result["options"]
    assert options[CONF_USE_GATEWAY] is True
    assert options[CONF_SYNC_MODE] == "2"  # Eco by default with the gateway
    assert options[CONF_CYA] == 40
    assert options[CONF_CHLORINE_MODEL] == "chlorine"
    assert "general" not in options  # sections flattened


async def test_without_gateway_default_sync_mode_is_normal(hass):
    with (
        patch(DISCOVERED, return_value=[_service_info()]),
        patch(SETUP, return_value=True),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=_service_info()
        )
        user_input = _user_input(_default_of(result, CONF_MAC_ADDRESS))
        user_input["general"][CONF_USE_GATEWAY] = False
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input
        )
    assert result["options"][CONF_SYNC_MODE] == "1"


async def test_already_configured_device_aborts(hass):
    make_entry().add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=_service_info()
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_invalid_calibration_shows_error_and_keeps_form(hass):
    with (
        patch(DISCOVERED, return_value=[_service_info()]),
        patch(SETUP, return_value=True),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=_service_info()
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            _user_input(
                _default_of(result, CONF_MAC_ADDRESS),
                **{CONF_PH_CALIB_7: 1900, CONF_PH_CALIB_4: 1600},
            ),
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_PH_CALIB_7: "ph_slope_mismatch"}


async def test_user_flow_without_discovered_devices_asks_for_mac(hass):
    with patch(DISCOVERED, return_value=[]), patch(SETUP, return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        # Malformed address -> error, form kept
        bad = await hass.config_entries.flow.async_configure(
            result["flow_id"], _user_input("not-a-mac")
        )
        assert bad["type"] is FlowResultType.FORM
        assert bad["errors"] == {CONF_MAC_ADDRESS: "invalid_mac"}

        good = await hass.config_entries.flow.async_configure(
            result["flow_id"], _user_input(MAC.lower())
        )
    assert good["type"] is FlowResultType.CREATE_ENTRY
    assert good["data"][CONF_MAC_ADDRESS] == MAC  # normalized to uppercase


async def test_manual_entry_step(hass):
    with (
        patch(DISCOVERED, return_value=[_service_info()]),
        patch(SETUP, return_value=True),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], _user_input("manual")
        )
        assert result["step_id"] == "manual"

        bad = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_MAC_ADDRESS: "zz"}
        )
        assert bad["errors"] == {CONF_MAC_ADDRESS: "invalid_mac"}

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_MAC_ADDRESS: "11:22:33:44:55:66"}
        )
        assert result["step_id"] == "user"


async def test_manual_mac_already_configured_aborts(hass):
    make_entry().add_to_hass(hass)
    with patch(DISCOVERED, return_value=[]), patch(SETUP, return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], _user_input(MAC)
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


# ---------------------------------------------------------------------------
# Options flow
# ---------------------------------------------------------------------------
def _options_input(**over) -> dict:
    general = {
        CONF_USE_GATEWAY: False,
        CONF_SYNC_MODE: "1",
        CONF_CHLORINE_MODEL: "chlorine",
        CONF_CYA: 40,
    }
    general.update(over.pop("general", {}))
    synchronization = {
        CONF_SCAN_INTERVAL: 60,
        CONF_REFERENCE_TIME: "08:00:00",
    }
    synchronization.update(over.pop("synchronization", {}))
    thresholds = {
        CONF_PH_MIN: 6.9,
        CONF_PH_MAX: 7.5,
        CONF_ORP_MIN: 650,
        CONF_ORP_MAX: 800,
        CONF_TEMP_MIN: 6.0,
        CONF_TEMP_MAX: 32.0,
    }
    thresholds.update(over.pop("alert_thresholds", {}))
    return {
        "general": general,
        "synchronization": synchronization,
        "probes_calibration": _valid_calibration(**over),
        "alert_thresholds": thresholds,
    }


async def test_options_form_prefills_current_values(hass):
    entry = make_entry(**{CONF_CYA: 55, CONF_CHLORINE_MODEL: "bromine"})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    general = result["data_schema"].schema["general"].schema.schema
    defaults = {str(k): k.default() for k in general}
    assert defaults[CONF_CYA] == 55
    assert defaults[CONF_CHLORINE_MODEL] == "bromine"


async def test_options_form_prefills_from_live_coordinator_data(
    hass, coordinator, entry
):
    """When the integration is loaded, the options form must show the
    scan_interval/reference_time currently held by the coordinator, not
    just the values stored in the config entry."""
    coordinator.data[CONF_SCAN_INTERVAL] = 77
    coordinator.data[CONF_REFERENCE_TIME] = "13:37"
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    synchronization = result["data_schema"].schema["synchronization"].schema.schema
    defaults = {str(k): k.default() for k in synchronization}
    assert defaults[CONF_SCAN_INTERVAL] == 77
    assert defaults[CONF_REFERENCE_TIME] == "13:37"


async def test_warning_step_without_pending_data_redirects_to_init(hass):
    """Defensive path: if the warning step is somehow reached without a
    pending submission (e.g. flow state lost), it must redirect back to
    the init step instead of crashing."""
    from custom_components.flipr_local.config_flow import FliprOptionsFlowHandler

    entry = make_entry()
    entry.add_to_hass(hass)
    handler = FliprOptionsFlowHandler()
    handler.hass = hass
    handler.handler = entry.entry_id

    result = await handler.async_step_warning()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_options_saved(hass):
    entry = make_entry()
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        _options_input(
            **{
                CONF_TEMP_OFFSET: 1.5,
                "alert_thresholds": {CONF_PH_MAX: 7.8},
                "synchronization": {
                    CONF_SCAN_INTERVAL: 30,
                    CONF_REFERENCE_TIME: "06:00:00",
                },
            }
        ),
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_TEMP_OFFSET] == 1.5
    assert entry.options[CONF_PH_MAX] == 7.8
    assert entry.options[CONF_CYA] == 40
    assert entry.options[CONF_SCAN_INTERVAL] == 30
    assert entry.options[CONF_REFERENCE_TIME] == "06:00:00"


@pytest.mark.parametrize(
    ("over", "field", "code"),
    [
        (
            {"alert_thresholds": {CONF_PH_MIN: 7.6, CONF_PH_MAX: 7.0}},
            CONF_PH_MIN,
            "ph_threshold_error",
        ),
        (
            {"alert_thresholds": {CONF_TEMP_MIN: 40, CONF_TEMP_MAX: 10}},
            CONF_TEMP_MIN,
            "temp_threshold_error",
        ),
        (
            {"alert_thresholds": {CONF_ORP_MIN: 900, CONF_ORP_MAX: 700}},
            CONF_ORP_MIN,
            "orp_threshold_error",
        ),
        (
            {CONF_PH_CALIB_7: 1900, CONF_PH_CALIB_4: 1600},
            CONF_PH_CALIB_7,
            "ph_slope_mismatch",
        ),
    ],
)
async def test_options_validation_errors(hass, over, field, code):
    entry = make_entry()
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], _options_input(**over)
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {field: code}


@pytest.mark.parametrize("mode", ["1", "3"])
async def test_intensive_sync_with_gateway_shows_battery_warning(hass, mode):
    entry = make_entry()
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        _options_input(general={CONF_USE_GATEWAY: True, CONF_SYNC_MODE: mode}),
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "warning"
    assert entry.options[CONF_SYNC_MODE] == "1"  # not saved yet

    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_SYNC_MODE] == mode
    assert entry.options[CONF_USE_GATEWAY] is True


@pytest.mark.parametrize("mode", ["0", "2"])
async def test_gentle_sync_modes_skip_warning(hass, mode):
    entry = make_entry()
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        _options_input(general={CONF_USE_GATEWAY: True, CONF_SYNC_MODE: mode}),
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_high_sync_mode_without_gateway_skips_warning(hass):
    entry = make_entry()
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        _options_input(general={CONF_USE_GATEWAY: False, CONF_SYNC_MODE: "3"}),
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


# ---------------------------------------------------------------------------
# Reconfigure flow (point this entry at a different physical Flipr)
# ---------------------------------------------------------------------------
NEW_MAC = "11:22:33:44:55:66"


async def _start_reconfigure(hass, entry):
    return await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
    )


async def test_reconfigure_form_prefills_current_mac(hass, coordinator, entry):
    with patch(DISCOVERED, return_value=[]):
        result = await _start_reconfigure(hass, entry)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    schema_defaults = {
        field.schema: field.default()
        for field in result["data_schema"].schema
        if field.default is not vol.UNDEFINED
    }
    assert schema_defaults[CONF_MAC_ADDRESS] == MAC


async def test_reconfigure_updates_mac(hass, coordinator, entry):
    with patch(DISCOVERED, return_value=[]):
        result = await _start_reconfigure(hass, entry)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_MAC_ADDRESS: NEW_MAC}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_MAC_ADDRESS] == NEW_MAC
    assert entry.unique_id == NEW_MAC


async def test_reconfigure_rejects_invalid_mac(hass, coordinator, entry):
    with patch(DISCOVERED, return_value=[]):
        result = await _start_reconfigure(hass, entry)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_MAC_ADDRESS: "not-a-mac"}
        )
    assert result["errors"] == {CONF_MAC_ADDRESS: "invalid_mac"}
    assert entry.data[CONF_MAC_ADDRESS] == MAC


async def test_reconfigure_can_keep_the_same_mac(hass, coordinator, entry):
    """Re-running the flow without actually changing the device."""
    with patch(DISCOVERED, return_value=[]):
        result = await _start_reconfigure(hass, entry)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_MAC_ADDRESS: MAC}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_MAC_ADDRESS] == MAC


async def test_reconfigure_aborts_if_mac_used_by_another_entry(
    hass, coordinator, entry
):
    other_mac = "AA:AA:AA:AA:AA:AA"
    other_entry = make_entry()
    other_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(other_entry, unique_id=other_mac)

    with patch(DISCOVERED, return_value=[]):
        result = await _start_reconfigure(hass, entry)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_MAC_ADDRESS: other_mac}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_MAC_ADDRESS] == MAC


async def test_reconfigure_picks_up_model_from_discovered_device(
    hass, coordinator, entry
):
    """If the newly targeted MAC matches a device HA has discovered over
    Bluetooth, the model recorded on the entry must reflect that device's
    advertised name instead of the previous device's model."""
    discovered = _service_info(name="Flipr 12345", address=NEW_MAC)
    with patch(DISCOVERED, return_value=[discovered]):
        result = await _start_reconfigure(hass, entry)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_MAC_ADDRESS: NEW_MAC}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_MAC_ADDRESS] == NEW_MAC
    assert entry.data["model"] != "unknown"


async def test_manual_mac_matching_discovered_device_fills_bt_name(hass):
    """When the manually typed MAC matches a device HA already discovered
    over Bluetooth, the flow should adopt that device's advertised name
    (and thus its detected model) instead of falling back to a generic one.
    A non-matching, differently-named device is included first to exercise
    the "keep scanning" loop path as well as the match path.
    """
    other_device = _service_info(name="Some Other Gadget", address="11:11:11:11:11:11")
    nameless_device = _service_info(name="", address="22:22:22:22:22:22")
    with (
        patch(
            DISCOVERED,
            return_value=[nameless_device, other_device, _service_info()],
        ),
        patch(SETUP, return_value=True),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], _user_input("manual")
        )
        assert result["step_id"] == "manual"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_MAC_ADDRESS: MAC}
        )
        assert result["step_id"] == "user"

        final = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            _user_input(_default_of(result, CONF_MAC_ADDRESS)),
        )
    assert final["type"] is FlowResultType.CREATE_ENTRY
    assert final["data"][CONF_MAC_ADDRESS] == MAC
    assert "Flipr" in final["title"]


async def test_user_flow_keeps_explicit_sync_mode(hass):
    """If normalized_input already carries a sync mode (defensive branch,
    not reachable through the current UI schema which has no such field),
    the flow must not silently overwrite it from use_gateway."""
    from custom_components.flipr_local.config_flow import FliprConfigFlow

    with (
        patch(DISCOVERED, return_value=[_service_info()]),
        patch(SETUP, return_value=True),
    ):
        flow = FliprConfigFlow()
        flow.hass = hass
        flow.context = {"source": SOURCE_USER}

        payload = _user_input(MAC)
        payload[CONF_SYNC_MODE] = "2"  # bypasses the (field-less) UI schema
        payload["general"][CONF_USE_GATEWAY] = False  # would normally imply "1"

        final = await flow.async_step_user(user_input=payload)
    assert final["type"] is FlowResultType.CREATE_ENTRY
    assert final["options"][CONF_SYNC_MODE] == "2"


async def test_reconfigure_skips_other_devices_in_the_scan(hass, coordinator, entry):
    """Another Bluetooth device in the scan must not be mistaken for the new Flipr."""
    stranger = SimpleNamespace(address="AA:AA:AA:AA:AA:AA", name="Not a Flipr")
    seen = [stranger, _service_info(address=NEW_MAC)]
    with patch(DISCOVERED, return_value=seen):
        result = await _start_reconfigure(hass, entry)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_MAC_ADDRESS: NEW_MAC}
        )
        await hass.async_block_till_done()
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_MAC_ADDRESS] == NEW_MAC
