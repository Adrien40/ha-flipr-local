"""Entities: sensors, alert thresholds, numbers, select, switch, button."""

from __future__ import annotations

from datetime import time, timedelta
from unittest.mock import AsyncMock

import homeassistant.util.dt as dt_util
import pytest
from homeassistant.const import (
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    EntityCategory,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.flipr_local.binary_sensor import FliprAlertSensor
from custom_components.flipr_local.const import (
    BT_STATUS_OUT_OF_RANGE,
    BT_STATUS_PAUSED,
    BT_STATUS_WAITING,
    CONF_CHLORINE_MODEL,
    CONF_CYA,
    CONF_MAC_ADDRESS,
    CONF_ORP_MAX,
    CONF_PH_MAX,
    CONF_PH_MIN,
    CONF_REFERENCE_TIME,
    CONF_SCAN_INTERVAL,
    CONF_TEMP_MAX,
    DEFAULT_PH_MAX,
)
from custom_components.flipr_local.select import FliprModelSelect

from .conftest import enable_disabled_by_default, entity_id, make_entry
from .helpers import MAC


async def _call(hass, domain, service, entity, **data):
    await hass.services.async_call(
        domain, service, {"entity_id": entity, **data}, blocking=True
    )
    await hass.async_block_till_done()


# ---------------------------------------------------------------------------
# Sensors
# ---------------------------------------------------------------------------
async def test_measurement_sensors(hass, setup_integration):
    for key in ("ph_raw", "orp_raw", "battery", "raw_frame"):
        enable_disabled_by_default(hass, "sensor", key)
    await setup_integration(make_entry())

    def state(key):
        return hass.states.get(entity_id(hass, "sensor", key)).state

    assert float(state("temperature")) == pytest.approx(25.02)
    assert float(state("ph")) == pytest.approx(7.38, abs=0.02)
    assert float(state("orp")) == 700
    assert float(state("ph_raw")) == 1600
    assert float(state("orp_raw")) == 700.0
    assert float(state("battery")) == 3300
    assert float(state("battery_level")) == 73
    assert state("lsi_status") == "unknown"
    assert state("sync_mode") == "2"
    assert state("bluetooth_status") == "success"
    assert len(state("raw_frame")) == 26


async def test_sensor_shows_unknown_when_value_is_none(hass, coordinator):
    coordinator.update_volatile_state({"ph": None})
    await hass.async_block_till_done()
    assert hass.states.get(entity_id(hass, "sensor", "ph")).state == STATE_UNKNOWN


async def test_next_analysis_matches_scheduled_slot(hass, coordinator):
    """Next analysis entity must display the aligned scheduled slot."""
    state = hass.states.get(entity_id(hass, "sensor", "next_analysis"))
    assert coordinator.next_slot is not None
    assert dt_util.parse_datetime(state.state) == coordinator.next_slot.replace(
        microsecond=0
    )


async def test_next_analysis_hidden_when_paused(hass, coordinator):
    coordinator.update_volatile_state({"active_measures": False})
    await hass.async_block_till_done()
    assert (
        hass.states.get(entity_id(hass, "sensor", "next_analysis")).state
        == STATE_UNKNOWN
    )


async def test_next_analysis_unknown_when_no_slot_scheduled(hass, coordinator):
    coordinator.next_slot = None
    coordinator.async_set_updated_data(dict(coordinator.data))
    await hass.async_block_till_done()
    assert (
        hass.states.get(entity_id(hass, "sensor", "next_analysis")).state
        == STATE_UNKNOWN
    )


async def test_next_analysis_converts_naive_slot_to_utc(hass, coordinator):
    """next_slot is normally tz-aware; a naive value must still be handled."""
    naive = dt_util.utcnow().replace(tzinfo=None)
    coordinator.next_slot = naive
    coordinator.async_set_updated_data(dict(coordinator.data))
    await hass.async_block_till_done()
    state = hass.states.get(entity_id(hass, "sensor", "next_analysis"))
    assert dt_util.parse_datetime(state.state) == dt_util.as_utc(naive).replace(
        microsecond=0
    )


async def test_rssi_sensor_follows_advertisements(hass, coordinator, ble):
    state = hass.states.get(entity_id(hass, "sensor", "rssi"))
    assert state.state == str(ble.rssi)


async def test_sensors_fall_back_to_unknown_with_no_coordinator_data(hass, coordinator):
    """Covers the `if not self.coordinator.data` guard in every sensor class.

    Unlike update_volatile_state/update_local_state (which merge into existing
    data), this replaces coordinator.data with a genuinely empty dict, as could
    happen very early during setup before the first successful cycle.
    """
    coordinator.async_set_updated_data({})
    await hass.async_block_till_done()
    assert hass.states.get(entity_id(hass, "sensor", "temperature")).state == (
        STATE_UNKNOWN
    )
    assert hass.states.get(entity_id(hass, "sensor", "sync_mode")).state == (
        STATE_UNKNOWN
    )
    assert (
        hass.states.get(entity_id(hass, "sensor", "bluetooth_status")).state
        == BT_STATUS_WAITING
    )
    assert hass.states.get(entity_id(hass, "sensor", "next_analysis")).state == (
        STATE_UNKNOWN
    )
    assert (
        hass.states.get(entity_id(hass, "binary_sensor", "ph_status")).state
        == STATE_UNKNOWN
    )


# ---------------------------------------------------------------------------
# Alerts (thresholds)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("key", ["ph_status", "orp_status", "temperature_status"])
async def test_alerts_off_when_values_in_range(hass, coordinator, key):
    assert hass.states.get(entity_id(hass, "binary_sensor", key)).state == STATE_OFF


async def test_alert_is_on_returns_none_for_unknown_data_key(hass, coordinator):
    """Defensive fallback: only ph/orp/temperature are meaningful data_keys."""
    sensor = FliprAlertSensor(
        coordinator,
        "fake_entry_id",
        coordinator.mac,
        "Flipr",
        "battery_status",
        "battery",
    )
    assert sensor.is_on is None


async def test_alert_keeps_default_thresholds_when_entry_is_gone(hass, coordinator):
    """_refresh_cached_thresholds must not crash if the config entry vanished."""
    sensor = FliprAlertSensor(
        coordinator, "fake_entry_id", coordinator.mac, "Flipr", "ph_status", "ph"
    )
    sensor.hass = hass
    original_async_get_entry = hass.config_entries.async_get_entry
    # Only fake it away for our made-up entry_id: replacing the bound method
    # outright would also break Home Assistant's own entry-unload machinery
    # during fixture teardown (it uses the same method internally), leaving a
    # lingering background task and failing every test that runs afterwards.
    hass.config_entries.async_get_entry = lambda entry_id: (
        None if entry_id == "fake_entry_id" else original_async_get_entry(entry_id)
    )
    try:
        sensor._refresh_cached_thresholds()
        assert sensor._cached_thresholds[CONF_PH_MAX] == DEFAULT_PH_MAX
    finally:
        hass.config_entries.async_get_entry = original_async_get_entry


async def test_ph_alert_follows_threshold_options(hass, coordinator, entry):
    ph_alert = entity_id(hass, "binary_sensor", "ph_status")
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, CONF_PH_MAX: 7.0, CONF_PH_MIN: 6.0}
    )
    await hass.async_block_till_done()
    assert hass.states.get(ph_alert).state == STATE_ON  # pH ≈ 7.38 > 7.0

    hass.config_entries.async_update_entry(
        entry, options={**entry.options, CONF_PH_MAX: 8.0}
    )
    await hass.async_block_till_done()
    assert hass.states.get(ph_alert).state == STATE_OFF


async def test_orp_and_temperature_alerts(hass, coordinator, entry):
    hass.config_entries.async_update_entry(
        entry,
        options={**entry.options, CONF_ORP_MAX: 690, CONF_TEMP_MAX: 20.0},
    )
    await hass.async_block_till_done()
    assert (
        hass.states.get(entity_id(hass, "binary_sensor", "orp_status")).state
        == STATE_ON
    )
    assert (
        hass.states.get(entity_id(hass, "binary_sensor", "temperature_status")).state
        == STATE_ON
    )


async def test_alert_boundary_values_are_in_range(hass, coordinator, entry):
    """The threshold itself is not an alert (strict comparisons)."""
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, CONF_ORP_MAX: 700}
    )
    await hass.async_block_till_done()
    assert (
        hass.states.get(entity_id(hass, "binary_sensor", "orp_status")).state
        == STATE_OFF
    )


async def test_alert_unknown_when_measurement_missing(hass, coordinator):
    coordinator.update_volatile_state({"ph": None})
    await hass.async_block_till_done()
    assert (
        hass.states.get(entity_id(hass, "binary_sensor", "ph_status")).state
        == STATE_UNKNOWN
    )


# ---------------------------------------------------------------------------
# Numbers: TAC / TH / TDS
# ---------------------------------------------------------------------------
async def test_water_parameters_drive_langelier(hass, coordinator):
    for key, value in (("tac", 100), ("th", 200), ("tds", 1000)):
        await _call(
            hass, "number", "set_value", entity_id(hass, "number", key), value=value
        )
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=2))
    await hass.async_block_till_done()

    lsi = hass.states.get(entity_id(hass, "sensor", "lsi"))
    assert lsi.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE)
    assert hass.states.get(entity_id(hass, "sensor", "lsi_status")).state in {
        "corrosive",
        "balanced",
        "scaling",
    }
    assert (
        float(hass.states.get(entity_id(hass, "sensor", "target_equilibrium_ph")).state)
        > 6
    )


@pytest.mark.parametrize(("key", "maximum"), [("tac", 500), ("th", 800), ("tds", 5000)])
async def test_water_parameter_bounds(hass, coordinator, key, maximum):
    entity = entity_id(hass, "number", key)
    await _call(hass, "number", "set_value", entity, value=maximum)
    assert float(hass.states.get(entity).state) == maximum
    with pytest.raises(ServiceValidationError):
        await _call(hass, "number", "set_value", entity, value=maximum + 1)
    with pytest.raises(ServiceValidationError):
        await _call(hass, "number", "set_value", entity, value=-1)


async def test_water_parameters_are_persisted(hass, coordinator, hass_storage):
    await _call(
        hass, "number", "set_value", entity_id(hass, "number", "tac"), value=120
    )
    assert coordinator.data["tac"] == 120
    await coordinator.async_save_to_disk()
    assert hass_storage["flipr_local_aabbccddeeff"]["data"]["tac"] == 120


async def test_scan_interval_updates_coordinator(hass, coordinator):
    entity = entity_id(hass, "number", "scan_interval")
    await _call(hass, "number", "set_value", entity, value=30)
    assert coordinator.data[CONF_SCAN_INTERVAL] == 30
    assert coordinator.update_interval <= timedelta(minutes=30)
    with pytest.raises(ServiceValidationError):
        await _call(hass, "number", "set_value", entity, value=4)  # minimum: 5 min


async def test_reference_time_entity(hass, coordinator):
    entity = entity_id(hass, "time", "reference_time")
    assert hass.states.get(entity).state == "08:00:00"
    await _call(hass, "time", "set_value", entity, time=time(6, 30).isoformat())
    assert coordinator.data[CONF_REFERENCE_TIME] == "06:30"
    assert hass.states.get(entity).state == "06:30:00"


# ---------------------------------------------------------------------------
# CyA and treatment type (kept)
# ---------------------------------------------------------------------------
async def test_cya_can_be_set(hass, coordinator):
    entity = entity_id(hass, "number", "cya")
    await _call(hass, "number", "set_value", entity, value=60)
    assert float(hass.states.get(entity).state) == 60
    assert coordinator.data["cya"] == 60


async def test_cya_is_unavailable_with_bromine(hass, coordinator):
    cya = entity_id(hass, "number", "cya")
    select = entity_id(hass, "select", "chlorine_model")
    assert hass.states.get(select).state == "chlorine"
    await _call(hass, "select", "select_option", select, option="bromine")
    assert hass.states.get(cya).state == STATE_UNAVAILABLE
    await _call(hass, "select", "select_option", select, option="chlorine")
    assert hass.states.get(cya).state != STATE_UNAVAILABLE


async def test_changing_treatment_does_not_revert_cya(hass, setup_integration):
    """Regression: the CyA entered on the entity was overwritten by the old
    options value whenever another setting (here, the treatment type) changed.

    The config flow writes `cya` into the options on creation: this reproduces
    that situation (CyA = 40 in the options).
    """
    entry = make_entry(**{CONF_CYA: 40})
    await setup_integration(entry)
    cya = entity_id(hass, "number", "cya")
    select = entity_id(hass, "select", "chlorine_model")
    await _call(hass, "number", "set_value", cya, value=80)

    await _call(hass, "select", "select_option", select, option="bromine")
    await _call(hass, "select", "select_option", select, option="chlorine")

    assert entry.options[CONF_CHLORINE_MODEL] == "chlorine"
    assert float(hass.states.get(cya).state) == 80


async def test_select_option_does_nothing_when_entry_is_gone(hass, coordinator):
    """If the config entry disappeared, selecting an option must not raise."""
    select = entity_id(hass, "select", "chlorine_model")
    original_async_get_entry = hass.config_entries.async_get_entry
    hass.config_entries.async_get_entry = lambda entry_id: None
    try:
        await _call(hass, "select", "select_option", select, option="bromine")
        # Unchanged: the entity never got a chance to update options.
        assert hass.states.get(select).state == "chlorine"
    finally:
        hass.config_entries.async_get_entry = original_async_get_entry


async def test_select_refresh_keeps_default_when_entry_is_gone(hass, coordinator):
    """_refresh_current_option must not crash if the config entry vanished."""
    select = FliprModelSelect(coordinator, "fake_entry_id", coordinator.mac, "Flipr")
    select.hass = hass
    original_async_get_entry = hass.config_entries.async_get_entry
    hass.config_entries.async_get_entry = lambda entry_id: (
        None if entry_id == "fake_entry_id" else original_async_get_entry(entry_id)
    )
    try:
        select._refresh_current_option()
        assert select.current_option == "chlorine"
    finally:
        hass.config_entries.async_get_entry = original_async_get_entry


async def test_cya_option_change_is_applied(hass, coordinator, entry):
    """Changing CyA in the options form is still taken into account."""
    cya = entity_id(hass, "number", "cya")
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, CONF_CYA: 55}
    )
    await hass.async_block_till_done()
    assert float(hass.states.get(cya).state) == 55


# ---------------------------------------------------------------------------
# "Automatic analysis" switch
# ---------------------------------------------------------------------------
async def test_switch_pauses_measurements(hass, coordinator):
    switch = entity_id(hass, "switch", "active_measures")
    assert hass.states.get(switch).state == STATE_ON
    await _call(hass, "switch", "turn_off", switch)
    assert hass.states.get(switch).state == STATE_OFF
    assert coordinator.data["bluetooth_status"] == BT_STATUS_PAUSED


async def test_switch_resume_does_not_request_refresh(hass, coordinator):
    """Turning switch back on must not trigger immediate analysis."""
    switch = entity_id(hass, "switch", "active_measures")
    await _call(hass, "switch", "turn_off", switch)
    coordinator.async_request_refresh = AsyncMock()
    await _call(hass, "switch", "turn_on", switch)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert coordinator.data["active_measures"] is True
    assert coordinator.data["bluetooth_status"] == BT_STATUS_WAITING
    coordinator.async_request_refresh.assert_not_awaited()


async def test_switch_resume_without_bluetooth_does_not_refresh(hass, coordinator, ble):
    switch = entity_id(hass, "switch", "active_measures")
    await _call(hass, "switch", "turn_off", switch)
    coordinator.async_request_refresh = AsyncMock()
    ble.scanner_count = 0
    await _call(hass, "switch", "turn_on", switch)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert coordinator.data["bluetooth_status"] == BT_STATUS_OUT_OF_RANGE
    coordinator.async_request_refresh.assert_not_awaited()


# ---------------------------------------------------------------------------
# "New analysis" button
# ---------------------------------------------------------------------------
async def test_button_requests_one_shot_analysis(hass, coordinator):
    button = entity_id(hass, "button", "force_analysis")
    coordinator.async_request_refresh = AsyncMock()
    await _call(hass, "button", "press", button)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert coordinator._force_one_shot is True
    coordinator.async_request_refresh.assert_awaited_once()
    assert coordinator.data["action_running"] is False  # reset to False at the end


async def test_button_ignored_while_analysis_running(hass, coordinator):
    coordinator.update_volatile_state({"action_running": True})
    coordinator.async_request_refresh = AsyncMock()
    await _call(hass, "button", "press", entity_id(hass, "button", "force_analysis"))
    await hass.async_block_till_done(wait_background_tasks=True)
    coordinator.async_request_refresh.assert_not_awaited()


async def test_button_is_not_blocked_when_out_of_range(hass, coordinator, ble):
    """Button tries analysis even without recent advertisement."""
    ble.scanner_count = 0
    coordinator.async_request_refresh = AsyncMock()
    await _call(hass, "button", "press", entity_id(hass, "button", "force_analysis"))
    await hass.async_block_till_done(wait_background_tasks=True)
    assert coordinator._force_one_shot is True
    coordinator.async_request_refresh.assert_awaited_once()


async def test_button_swallows_refresh_errors(hass, coordinator):
    """An error during the analysis must not leave "action_running" stuck."""
    coordinator.async_request_refresh = AsyncMock(side_effect=RuntimeError("boom"))
    await _call(hass, "button", "press", entity_id(hass, "button", "force_analysis"))
    await hass.async_block_till_done(wait_background_tasks=True)
    assert coordinator.data["action_running"] is False


async def test_button_ignored_while_shutting_down(hass, coordinator):
    """A press during shutdown must be a no-op, not raise or schedule anything."""
    coordinator.async_request_refresh = AsyncMock()
    coordinator._is_shutdown = True
    try:
        await _call(
            hass, "button", "press", entity_id(hass, "button", "force_analysis")
        )
        await hass.async_block_till_done(wait_background_tasks=True)
        coordinator.async_request_refresh.assert_not_awaited()
    finally:
        coordinator._is_shutdown = False


async def test_button_logs_timeout_without_leaving_action_running(hass, coordinator):
    """A refresh that exceeds TIMEOUT_FORCE_REFRESH is logged, not raised."""
    coordinator.async_request_refresh = AsyncMock(side_effect=TimeoutError())
    await _call(hass, "button", "press", entity_id(hass, "button", "force_analysis"))
    await hass.async_block_till_done(wait_background_tasks=True)
    assert coordinator.data["action_running"] is False


async def test_button_does_not_schedule_task_when_entry_is_gone(hass, coordinator):
    """If the config entry disappeared mid-press, no background task is scheduled."""
    coordinator.async_request_refresh = AsyncMock()
    original_async_get_entry = hass.config_entries.async_get_entry
    hass.config_entries.async_get_entry = lambda entry_id: None
    try:
        await _call(
            hass, "button", "press", entity_id(hass, "button", "force_analysis")
        )
        await hass.async_block_till_done(wait_background_tasks=True)
        coordinator.async_request_refresh.assert_not_awaited()
    finally:
        hass.config_entries.async_get_entry = original_async_get_entry


async def test_raw_orp_is_not_affected_by_calibration_offset(hass, setup_integration):
    """Raw Redox is used to establish the offset: it must stay the probe's value."""
    enable_disabled_by_default(hass, "sensor", "orp_raw")
    entry = make_entry(**{"orp_calib": 640, "orp_ref": 650})
    await setup_integration(entry)
    raw = hass.states.get(entity_id(hass, "sensor", "orp_raw"))
    calibrated = hass.states.get(entity_id(hass, "sensor", "orp"))
    assert float(raw.state) == 700.0
    assert float(calibrated.state) == 710.0
    assert raw.attributes["unit_of_measurement"] == "mV"


async def test_raw_orp_is_a_diagnostic_entity(hass, coordinator):
    reg = er.async_get(hass).async_get(entity_id(hass, "sensor", "orp_raw"))
    assert reg.entity_category is EntityCategory.DIAGNOSTIC


@pytest.mark.parametrize(
    ("alert", "low_key", "high_key", "value"),
    [
        ("ph_status", "ph_min", "ph_max", 7.38),
        ("orp_status", "orp_min", "orp_max", 700),
        ("temperature_status", "temp_min", "temp_max", 25.02),
    ],
)
async def test_every_threshold_boundary(
    hass, coordinator, entry, alert, low_key, high_key, value
):
    """A measurement equal to a threshold is not an alert; just beyond it, it is."""
    measured = hass.states.get(
        entity_id(
            hass,
            "sensor",
            {
                "ph_status": "ph",
                "orp_status": "orp",
                "temperature_status": "temperature",
            }[alert],
        )
    ).state
    measured = float(measured)
    assert measured == pytest.approx(value, abs=0.02)
    entity = entity_id(hass, "binary_sensor", alert)
    step = 0.01 if alert != "orp_status" else 1
    wide = {
        "ph_min": 0,
        "ph_max": 14,
        "orp_min": 0,
        "orp_max": 1200,
        "temp_min": 0,
        "temp_max": 50,
    }

    for key, threshold, expected in (
        (low_key, measured, STATE_OFF),  # measurement == low threshold
        (low_key, measured + step, STATE_ON),  # measurement < low threshold
        (high_key, measured, STATE_OFF),  # measurement == high threshold
        (high_key, measured - step, STATE_ON),  # measurement > high threshold
    ):
        hass.config_entries.async_update_entry(
            entry, options={**entry.options, **wide, key: threshold}
        )
        await hass.async_block_till_done()
        assert hass.states.get(entity).state == expected, (key, threshold)


# ---------------------------------------------------------------------------
# RSSI sensor out of range
# ---------------------------------------------------------------------------
async def test_rssi_becomes_unavailable_as_soon_as_signal_is_lost(
    hass, coordinator, ble
):
    rssi = entity_id(hass, "sensor", "rssi")
    assert hass.states.get(rssi).state == str(ble.rssi)
    ble.last_seen_age = 500
    coordinator._on_ble_unavailable(None)
    await hass.async_block_till_done()
    assert hass.states.get(rssi).state == STATE_UNAVAILABLE


async def test_rssi_is_available_again_when_signal_returns(hass, coordinator, ble):
    rssi = entity_id(hass, "sensor", "rssi")
    ble.last_seen_age = 500
    coordinator._on_ble_unavailable(None)
    await hass.async_block_till_done()
    ble.last_seen_age = 0
    coordinator._on_ble_seen(None, None)
    await hass.async_block_till_done()
    assert hass.states.get(rssi).state == str(ble.rssi)


async def test_rssi_unavailable_when_signal_disappears_between_polls(
    hass, coordinator, ble
):
    """Even without a loss callback, scheduled cycle notices absence and updates."""
    rssi = entity_id(hass, "sensor", "rssi")
    ble.last_seen_age = 500
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(rssi).state == STATE_UNAVAILABLE


async def test_rssi_falls_back_to_restored_value_without_last_service_info(
    hass, coordinator
):
    """When Bluetooth has no cached advertisement yet, the RSSI sensor must
    fall back to its last restored state instead of staying unknown."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock as _AsyncMock
    from unittest.mock import patch as _patch

    from custom_components.flipr_local.sensor import FliprRealTimeRSSISensor

    sensor = FliprRealTimeRSSISensor(coordinator, coordinator.mac, "Flipr")
    sensor.hass = hass
    sensor.async_write_ha_state = lambda: None
    restored = SimpleNamespace(native_value=-55)
    with (
        _patch(
            "custom_components.flipr_local.sensor.async_last_service_info",
            lambda *a, **k: None,
        ),
        _patch(
            "custom_components.flipr_local.sensor.async_register_callback",
            lambda *a, **k: lambda: None,
        ),
        _patch.object(
            FliprRealTimeRSSISensor,
            "async_get_last_sensor_data",
            _AsyncMock(return_value=restored),
        ),
    ):
        await sensor.async_added_to_hass()
    assert sensor._attr_native_value == -55


async def test_rssi_updates_from_realtime_bluetooth_callback(hass, coordinator):
    """The live Bluetooth-advertisement callback must update the RSSI value."""
    from types import SimpleNamespace
    from unittest.mock import patch as _patch

    from custom_components.flipr_local.sensor import FliprRealTimeRSSISensor

    sensor = FliprRealTimeRSSISensor(coordinator, coordinator.mac, "Flipr")
    sensor.hass = hass
    sensor.async_write_ha_state = lambda: None
    captured = {}

    def _fake_register(hass_, callback_, matcher, mode):
        captured["callback"] = callback_
        return lambda: None

    with (
        _patch(
            "custom_components.flipr_local.sensor.async_last_service_info",
            lambda *a, **k: SimpleNamespace(rssi=-60),
        ),
        _patch(
            "custom_components.flipr_local.sensor.async_register_callback",
            _fake_register,
        ),
    ):
        await sensor.async_added_to_hass()

    captured["callback"](SimpleNamespace(rssi=-42), None)
    assert sensor._attr_native_value == -42


async def test_rssi_stays_none_when_restored_value_is_none(hass, coordinator):
    """No live advertisement and a restored entry with no usable value:
    the RSSI must remain unset rather than crash."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock as _AsyncMock
    from unittest.mock import patch as _patch

    from custom_components.flipr_local.sensor import FliprRealTimeRSSISensor

    sensor = FliprRealTimeRSSISensor(coordinator, coordinator.mac, "Flipr")
    sensor.hass = hass
    sensor.async_write_ha_state = lambda: None
    restored = SimpleNamespace(native_value=None)
    with (
        _patch(
            "custom_components.flipr_local.sensor.async_last_service_info",
            lambda *a, **k: None,
        ),
        _patch(
            "custom_components.flipr_local.sensor.async_register_callback",
            lambda *a, **k: lambda: None,
        ),
        _patch.object(
            FliprRealTimeRSSISensor,
            "async_get_last_sensor_data",
            _AsyncMock(return_value=restored),
        ),
    ):
        await sensor.async_added_to_hass()
    assert sensor._attr_native_value is None


async def test_scan_interval_falls_back_to_entry_data(hass, setup_integration):
    """If scan_interval was only ever stored in entry.data (legacy/imported
    entries) and not in options, the number entity must still pick it up."""
    entry = MockConfigEntry(
        domain="flipr_local",
        unique_id=MAC,
        title="Flipr AnalysR 3",
        version=1,
        minor_version=2,
        data={
            CONF_MAC_ADDRESS: MAC,
            "model": "Flipr AnalysR 3",
            CONF_SCAN_INTERVAL: 45,
        },
        options={},
    )
    await setup_integration(entry)
    entity = entity_id(hass, "number", "scan_interval")
    assert hass.states.get(entity).state == "45"


async def test_scan_interval_option_change_updates_entity(hass, coordinator, entry):
    """An external options change (e.g. from the options flow) must be
    reflected on the number entity, not just changes made through it."""
    scan_interval = entity_id(hass, "number", "scan_interval")
    assert hass.states.get(scan_interval).state == "60"
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, CONF_SCAN_INTERVAL: 20}
    )
    await hass.async_block_till_done()
    assert hass.states.get(scan_interval).state == "20"
    assert coordinator.data[CONF_SCAN_INTERVAL] == 20


async def test_water_parameter_refresh_chlorine_model_when_entry_is_gone(
    hass, coordinator
):
    """_refresh_chlorine_model must not crash if the config entry vanished."""
    from custom_components.flipr_local.number import FliprWaterConfigNumber

    number = FliprWaterConfigNumber(
        coordinator,
        coordinator.mac,
        CONF_CYA,
        0,
        300,
        1,
        30,
        "fake_entry_id",
        "Flipr",
        "ppm",
    )
    number.hass = hass
    original_async_get_entry = hass.config_entries.async_get_entry
    hass.config_entries.async_get_entry = lambda entry_id: (
        None if entry_id == "fake_entry_id" else original_async_get_entry(entry_id)
    )
    try:
        number._refresh_chlorine_model()
        assert number._chlorine_model == "chlorine"
    finally:
        hass.config_entries.async_get_entry = original_async_get_entry


async def test_scan_interval_option_matching_current_value_skips_update(
    hass, coordinator, entry
):
    """If an options change brings scan_interval to the SAME value the
    entity already has, no redundant local-state update must be triggered."""
    scan_interval = entity_id(hass, "number", "scan_interval")
    await _call(hass, "number", "set_value", scan_interval, value=45)
    assert float(hass.states.get(scan_interval).state) == 45

    hass.config_entries.async_update_entry(
        entry, options={**entry.options, CONF_SCAN_INTERVAL: 45}
    )
    await hass.async_block_till_done()
    assert float(hass.states.get(scan_interval).state) == 45


async def test_water_parameter_option_matching_current_value_skips_update(
    hass, coordinator, entry
):
    """If an options change brings the option to the SAME value the entity
    already has, no redundant local-state update must be triggered."""
    tac = entity_id(hass, "number", "tac")
    await _call(hass, "number", "set_value", tac, value=120)
    assert float(hass.states.get(tac).state) == 120

    hass.config_entries.async_update_entry(entry, options={**entry.options, "tac": 120})
    await hass.async_block_till_done()
    assert float(hass.states.get(tac).state) == 120


async def test_reference_time_falls_back_to_entry_data(hass, setup_integration):
    """If reference_time was only ever stored in entry.data (legacy/imported
    entries) and not in options, the time entity must still pick it up."""
    entry = MockConfigEntry(
        domain="flipr_local",
        unique_id=MAC,
        title="Flipr AnalysR 3",
        version=1,
        minor_version=2,
        data={
            CONF_MAC_ADDRESS: MAC,
            "model": "Flipr AnalysR 3",
            CONF_REFERENCE_TIME: "05:15",
        },
        options={},
    )
    await setup_integration(entry)
    entity = entity_id(hass, "time", "reference_time")
    assert hass.states.get(entity).state == "05:15:00"


async def test_reference_time_option_change_updates_entity(hass, coordinator, entry):
    """An external options change (e.g. from the options flow) must be
    reflected on the time entity, not just changes made through it."""
    reference_time = entity_id(hass, "time", "reference_time")
    assert hass.states.get(reference_time).state == "08:00:00"
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, CONF_REFERENCE_TIME: "21:45"}
    )
    await hass.async_block_till_done()
    assert hass.states.get(reference_time).state == "21:45:00"
    assert coordinator.data[CONF_REFERENCE_TIME] == "21:45"


async def test_reference_time_native_value_reads_entry_when_coordinator_data_empty(
    hass, coordinator, entry
):
    """native_value must fall back to the config entry when the coordinator
    has no reference_time cached yet (e.g. before the first refresh)."""
    from custom_components.flipr_local.time import FliprReferenceTime

    hass.config_entries.async_update_entry(
        entry, options={**entry.options, CONF_REFERENCE_TIME: "11:11"}
    )
    await hass.async_block_till_done()
    coordinator.data.pop(CONF_REFERENCE_TIME, None)
    entity = FliprReferenceTime(coordinator, coordinator.mac, "Flipr", entry.entry_id)
    entity.hass = hass
    assert entity.native_value == time(11, 11)


async def test_reference_time_option_matching_current_value_skips_update(
    hass, coordinator, entry
):
    """If an options change brings reference_time to the SAME value already
    cached by the coordinator, no redundant local-state update must fire."""
    reference_time = entity_id(hass, "time", "reference_time")
    await _call(hass, "time", "set_value", reference_time, time=time(9, 30).isoformat())
    assert coordinator.data[CONF_REFERENCE_TIME] == "09:30"

    hass.config_entries.async_update_entry(
        entry, options={**entry.options, CONF_REFERENCE_TIME: "09:30"}
    )
    await hass.async_block_till_done()
    assert hass.states.get(reference_time).state == "09:30:00"


async def test_reference_time_native_value_defaults_when_nothing_available(
    hass, coordinator
):
    """native_value must default to 08:00 when there is neither cached
    coordinator data nor a resolvable config entry."""
    from custom_components.flipr_local.time import FliprReferenceTime

    coordinator.data.pop(CONF_REFERENCE_TIME, None)
    entity = FliprReferenceTime(coordinator, coordinator.mac, "Flipr", "fake_entry_id")
    entity.hass = hass
    assert entity.native_value == time(8, 0)


async def test_diagnostic_only_sensors_are_disabled_by_default(hass, coordinator):
    """Raw/redundant diagnostic sensors shouldn't clutter the dashboard for
    users who don't need them (Gold quality-scale: entity-disabled-by-default)."""
    reg = er.async_get(hass)
    for key in ("ph_raw", "orp_raw", "battery", "factory_ph", "raw_frame"):
        entry = reg.async_get(entity_id(hass, "sensor", key))
        assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION, key


async def test_scan_interval_is_stored_as_integer(hass, coordinator, entry):
    """Regression: the interval must stay an int ("45", not "45.0") in both
    the entity state and the coordinator data."""
    scan_interval = entity_id(hass, "number", "scan_interval")
    await _call(hass, "number", "set_value", scan_interval, value=45)
    assert hass.states.get(scan_interval).state == "45"
    assert isinstance(coordinator.data[CONF_SCAN_INTERVAL], int)
    assert coordinator.data[CONF_SCAN_INTERVAL] == 45
