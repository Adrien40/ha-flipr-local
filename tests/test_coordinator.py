"""Coordinator: full BLE cycle with fake Bluetooth."""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, patch

import homeassistant.util.dt as dt_util
import pytest

from custom_components.flipr_local.chemistry import classify_lsi, compute_isl
from custom_components.flipr_local.const import (
    BT_STATUS_ERROR,
    BT_STATUS_ERROR_RETRY,
    BT_STATUS_OUT_OF_RANGE,
    BT_STATUS_PAUSED,
    BT_STATUS_SUCCESS,
    BT_STATUS_SYNC_APPLIED,
    BT_STATUS_WAITING,
    BT_STATUS_WRITE_FAILED,
    CONF_ORP_CALIB,
    CONF_ORP_REF,
    CONF_PH_CALIB_4,
    CONF_PH_CALIB_7,
    CONF_PH_REF_4,
    CONF_PH_REF_7,
    CONF_REFERENCE_TIME,
    CONF_SCAN_INTERVAL,
    CONF_SYNC_MODE,
    CONF_TAC,
    CONF_TDS,
    CONF_TEMP_OFFSET,
    CONF_TH,
    CONF_USE_GATEWAY,
    FLIPR_ANALYZE_UUID,
    FLIPR_CHARACTERISTIC_UUID,
    SYNC_CHAR_UUID,
)
from custom_components.flipr_local.coordinator import (
    format_mac_safe,
    get_opt,
    store_key,
)

from .conftest import make_entry
from .helpers import MAC, STANDBY_FRAME, FakeBleakClient, build_frame


def _frame(n: int = 0, **kw) -> bytes:
    """Valid frame distinct for each n (an identical frame would be ignored)."""
    return build_frame(battery_mv=3300 - n, **kw)


# ---------------------------------------------------------------------------
# Pure utilities
# ---------------------------------------------------------------------------
def test_store_key_is_normalized():
    assert store_key("AA:BB:CC:DD:EE:FF") == "flipr_local_aabbccddeeff"


@pytest.mark.parametrize("mac", [None, "", "AA:BB", "short"])
def test_format_mac_safe_hides_invalid(mac):
    assert format_mac_safe(mac) == "XX:XX:XX:XX:XX:XX"


def test_format_mac_safe_masks_middle():
    masked = format_mac_safe("AA:BB:CC:DD:EE:FF")
    assert masked == "AA:BB:CC...EE:FF"
    assert "DD" not in masked


def test_get_opt_precedence(entry):
    entry = make_entry(only_option=1, shared="option")
    entry = type(entry)(
        domain=entry.domain,
        data={**entry.data, "shared": "data", "only_data": 2},
        options=entry.options,
    )
    assert get_opt(entry, "shared") == "option"  # options > data
    assert get_opt(entry, "only_data") == 2  # data if absent from options
    assert get_opt(entry, "missing", "dflt") == "dflt"


# ---------------------------------------------------------------------------
# Nominal cycle
# ---------------------------------------------------------------------------
async def test_first_cycle_populates_data(coordinator, ble):
    d = coordinator.data
    assert d["bluetooth_status"] == BT_STATUS_SUCCESS
    assert d["temperature"] == pytest.approx(25.02)
    assert d["ph_raw"] == 1600
    assert d["ph"] == pytest.approx(7.38, abs=0.02)
    assert d["orp"] == 700
    assert d["battery"] == 3300
    assert d["battery_level"] == 73
    assert d["sync_mode"] == "2"
    assert d["raw_frame"] == build_frame().hex().upper()
    assert d["last_received"] is not None
    # Estimated chlorine no longer exists.
    assert "estimated_free_chlorine" not in d
    assert "active_chlorine_hocl" not in d


async def test_first_cycle_uses_analyze_command_and_cleans_up(coordinator, ble):
    assert ble.client.writes == [(FLIPR_ANALYZE_UUID, b"\x01")]
    assert ble.client.notify_started
    assert ble.client.notify_stopped
    assert ble.client.disconnected


async def test_lsi_unknown_until_water_parameters_are_set(coordinator):
    assert coordinator.data["lsi"] is None
    assert coordinator.data["lsi_status"] == "unknown"
    assert coordinator.data["target_equilibrium_ph"] is None


async def test_recompute_after_water_parameters_change(coordinator):
    coordinator.update_local_state({CONF_TAC: 100, CONF_TH: 200, CONF_TDS: 1000})
    coordinator.recompute_derived_values()
    d = coordinator.data
    expected = compute_isl(d["temperature"], d["ph"], 100, 200, 1000)
    assert d["lsi"] == expected
    assert d["lsi_status"] == classify_lsi(expected)
    assert d["target_equilibrium_ph"] == 7.68 or d["target_equilibrium_ph"] is not None


# ---------------------------------------------------------------------------
# Calibration and offsets
# ---------------------------------------------------------------------------
async def test_offsets_and_calibration_are_applied(setup_integration, ble):
    ble.client = FakeBleakClient([build_frame(temp_c=25.02, ph_mv=1750, orp_mv=700)])
    coord = await setup_integration(
        make_entry(
            **{
                CONF_TEMP_OFFSET: 1.5,
                CONF_ORP_REF: 650,
                CONF_ORP_CALIB: 640,  # the probe reads 10 mV less than the reference
                CONF_PH_CALIB_7: 1600,
                CONF_PH_REF_7: 7.0,
                CONF_PH_CALIB_4: 1900,
                CONF_PH_REF_4: 4.0,
            }
        )
    )
    assert coord.data["temperature"] == pytest.approx(26.52)
    assert coord.data["orp"] == 710
    assert coord.data["ph"] == pytest.approx(5.5)  # midway between 7 and 4
    # Raw values stay available for recomputation.
    assert coord.data["temp_raw"] == pytest.approx(25.02)
    assert coord.data["orp_raw"] == 700.0


async def test_options_change_recomputes_without_new_measurement(
    hass, entry, coordinator, ble
):
    writes_before = len(ble.client.writes)
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, CONF_TEMP_OFFSET: 2.0}
    )
    await hass.async_block_till_done()
    assert coordinator.data["temperature"] == pytest.approx(27.02)
    assert len(ble.client.writes) == writes_before  # no BLE connection


async def test_degenerate_ph_calibration_falls_back_to_factory(
    setup_integration, caplog
):
    """Two coincident calibration points: pH must not freeze at 7.0."""
    with caplog.at_level(logging.WARNING):
        coord = await setup_integration(
            make_entry(**{CONF_PH_CALIB_4: 1700, CONF_PH_CALIB_7: 1700})
        )
    assert coord.data["ph"] == pytest.approx(coord.data["factory_ph"], abs=0.01)
    assert "Degenerate pH calibration" in caplog.text


async def test_physically_impossible_ph_becomes_unknown(setup_integration, ble, caplog):
    ble.client = FakeBleakClient([build_frame(ph_mv=2500)])
    with caplog.at_level(logging.WARNING):
        coord = await setup_integration(
            make_entry(
                **{
                    CONF_PH_CALIB_7: 1600,
                    CONF_PH_REF_7: 7.0,
                    CONF_PH_CALIB_4: 1601,  # near-zero slope -> invalid pH
                    CONF_PH_REF_4: 4.0,
                }
            )
        )
    assert coord.data["ph"] is None
    assert coord.data["lsi"] is None
    assert "out of the physical range" in caplog.text


async def test_invalid_stored_calibration_uses_factory_default(
    setup_integration, caplog
):
    with caplog.at_level(logging.WARNING):
        coord = await setup_integration(make_entry(**{CONF_PH_CALIB_4: "garbage"}))
    assert "Invalid pH 4 calibration value" in caplog.text
    assert coord.data["ph"] is not None


# ---------------------------------------------------------------------------
# Wi-Fi Gateway / Calibrationommands
# ---------------------------------------------------------------------------
async def test_gateway_first_cycle_sends_sync_mode(setup_integration, ble):
    coord = await setup_integration(
        make_entry(**{CONF_USE_GATEWAY: True, CONF_SYNC_MODE: "2"})
    )
    assert ble.client.writes[0] == (SYNC_CHAR_UUID, b"\x02")
    assert coord.data["bluetooth_status"] == BT_STATUS_SYNC_APPLIED


async def test_after_init_commands_go_back_to_analyze(setup_integration, ble):
    coord = await setup_integration(
        make_entry(**{CONF_USE_GATEWAY: True, CONF_SYNC_MODE: "2"})
    )
    ble.client.frames = [_frame(1)]
    await coord.async_refresh()
    assert ble.client.writes[-1] == (FLIPR_ANALYZE_UUID, b"\x01")
    assert coord.data["bluetooth_status"] == BT_STATUS_SUCCESS


async def test_changing_sync_mode_option_queues_command(hass, setup_integration):
    entry = make_entry(**{CONF_USE_GATEWAY: True, CONF_SYNC_MODE: "2"})
    coord = await setup_integration(entry)
    # HA's debouncer would defer the refresh (10 s cooldown):
    # so we check the request, not its execution.
    coord.async_request_refresh = AsyncMock()
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, CONF_SYNC_MODE: "0"}
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    assert (coord._pending_cmd_type, coord._pending_cmd_val) == ("mode", 0)
    assert coord._force_one_shot is True
    coord.async_request_refresh.assert_awaited_once()


async def test_unrelated_option_change_does_not_queue_command(hass, setup_integration):
    entry = make_entry(**{CONF_USE_GATEWAY: True, CONF_SYNC_MODE: "2"})
    coord = await setup_integration(entry)
    coord.async_request_refresh = AsyncMock()
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, CONF_TEMP_OFFSET: 1.0}
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    assert coord._pending_cmd_type == "analyze"
    coord.async_request_refresh.assert_not_awaited()


# ---------------------------------------------------------------------------
# Specific frames
# ---------------------------------------------------------------------------
async def test_identical_frame_is_ignored_until_a_new_one_arrives(coordinator, ble):
    """A frame identical to the previous one = no new measurement."""
    same = build_frame()
    new = _frame(5)
    ble.client.frames = [same, new]
    await coordinator.async_refresh()
    assert coordinator.data["raw_frame"] == new.hex().upper()
    assert coordinator.data["battery"] == 3295
    # 1st write -> identical frame ignored -> timeout -> 2nd write -> new frame
    assert len([w for w in ble.client.writes if w[0] == FLIPR_ANALYZE_UUID]) == 3


async def test_standby_frame_keeps_previous_data(coordinator, ble):
    ble.client.frames = [STANDBY_FRAME]
    before = coordinator.data["ph"]
    await coordinator.async_refresh()
    assert coordinator.data["bluetooth_status"] == BT_STATUS_WAITING
    assert coordinator.data["ph"] == before
    assert coordinator.retry_count == 0


async def test_standby_without_history_fails_update(setup_integration, ble):
    ble.client = FakeBleakClient([STANDBY_FRAME])
    coord = await setup_integration(make_entry())
    assert coord.data.get("ph_raw") is None
    assert coord.last_update_success is False
    assert coord.data["bluetooth_status"] == BT_STATUS_WAITING


async def test_implausible_frame_triggers_retry(coordinator, ble):
    ble.client.frames = [build_frame(ph_mv=100)]  # 100 mV: out of range
    before = coordinator.data["ph"]
    await coordinator.async_refresh()
    assert coordinator.data["bluetooth_status"] == BT_STATUS_ERROR_RETRY
    assert coordinator.retry_count == 1
    assert coordinator._retry_cancel is not None
    assert coordinator.data["ph"] == before  # the last good measurement is kept


async def test_retry_escalates_then_gives_up(coordinator, ble):
    ble.client.frames = [build_frame(ph_mv=100 + i) for i in range(3)]
    statuses = []
    for _ in range(3):
        await coordinator.async_refresh()
        statuses.append(coordinator.data["bluetooth_status"])
    assert statuses == [BT_STATUS_ERROR_RETRY, BT_STATUS_ERROR_RETRY, BT_STATUS_ERROR]
    assert coordinator.retry_count == 0  # reset to zero after giving up
    assert coordinator.data["ph"] is not None  # history kept


# ---------------------------------------------------------------------------
# BLE errors
# ---------------------------------------------------------------------------
async def test_write_timeout_then_success(setup_integration, ble):
    ble.client = FakeBleakClient([_frame()], write_errors=[TimeoutError(), None])
    coord = await setup_integration(make_entry())
    assert coord.data["bluetooth_status"] == BT_STATUS_SUCCESS
    assert len(ble.client.writes) == 2


async def test_write_error_on_both_attempts_is_write_failed(setup_integration, ble):
    ble.client = FakeBleakClient(write_errors=[OSError("gatt"), OSError("gatt")])
    coord = await setup_integration(make_entry())
    assert coord.data["bluetooth_status"] == BT_STATUS_ERROR_RETRY
    assert coord.retry_count == 1
    assert ble.client.disconnected


async def test_write_failure_status_after_retries_exhausted(coordinator, ble):
    coordinator.retry_count = 2  # retries already consumed
    ble.client.write_errors = [OSError("x"), OSError("x")]
    await coordinator.async_refresh()
    assert coordinator.data["bluetooth_status"] == BT_STATUS_WRITE_FAILED


async def test_no_notification_received_is_an_error(coordinator, ble):
    ble.client.frames = []  # nothing received: two NOTIFY_WAIT_TIMEOUT waits
    await coordinator.async_refresh()
    assert coordinator.data["bluetooth_status"] == BT_STATUS_ERROR_RETRY
    assert len(ble.client.writes) == 3  # 1 initial cycle + 2 attempts


async def test_unexpected_exception_is_contained(coordinator, ble):
    ble.establish.side_effect = RuntimeError("boom")
    await coordinator.async_refresh()
    assert coordinator.data["bluetooth_status"] == BT_STATUS_ERROR_RETRY
    assert coordinator.last_update_success


async def test_connect_timeout_while_advertising_is_transient(coordinator, ble):
    ble.establish.side_effect = TimeoutError()
    await coordinator.async_refresh()
    assert coordinator.data["bluetooth_status"] == BT_STATUS_ERROR_RETRY


async def test_connect_timeout_without_advertisement_is_out_of_range(coordinator, ble):
    async def _lose_signal(*_a, **_k):
        ble.last_seen_age = 999
        raise TimeoutError

    ble.establish.side_effect = _lose_signal
    await coordinator.async_refresh()
    assert coordinator.data["bluetooth_status"] == BT_STATUS_OUT_OF_RANGE
    assert coordinator.data["ph"] is not None


async def test_connect_timeout_out_of_range_without_history_fails(
    setup_integration, ble
):
    async def _lose_signal(*_a, **_k):
        ble.last_seen_age = 999
        raise TimeoutError

    ble.establish.side_effect = _lose_signal
    coord = await setup_integration(make_entry())
    assert coord.last_update_success is False


# ---------------------------------------------------------------------------
# TIMEOUT_GATT_OP: a device that stops responding after connecting must
# never block the cycle indefinitely (start_notify / stop_notify / disconnect).
# ---------------------------------------------------------------------------
async def test_start_notify_hang_times_out(setup_integration, ble):
    ble.client = FakeBleakClient([_frame()], start_notify_hangs=True)
    coord = await setup_integration(make_entry())
    # The cycle ends (no hang) and falls back to a transient error,
    # exactly like a regular connection timeout.
    assert coord.data["bluetooth_status"] == BT_STATUS_ERROR_RETRY


async def test_stop_notify_hang_does_not_block_disconnect(coordinator, ble):
    # stop_notify sits in a `finally` guarded by a broad except Exception:
    # even if it hangs, it must not block the disconnect or crash the cycle.
    # is_connected must be reset: see test_disconnect_hang_does_not_block_cycle.
    ble.client.is_connected = True
    ble.client.frames = [_frame(1)]
    ble.client._stop_notify_hangs = True
    await coordinator.async_refresh()
    assert coordinator.data["bluetooth_status"] == BT_STATUS_SUCCESS
    assert ble.client.disconnected


async def test_disconnect_hang_does_not_block_cycle(coordinator, ble):
    # _safely_disconnect already swallows every exception: a hang must not
    # make the cycle wait indefinitely either.
    # is_connected must be reset: the fake client is disconnected (and thus
    # already reports is_connected=False) at the end of the coordinator's
    # first cycle during the `coordinator` fixture's own setup, and
    # establish_connection is mocked to always hand back this same object
    # rather than a freshly (re)connected one.
    ble.client.is_connected = True
    ble.client.frames = [_frame(1)]
    ble.client._disconnect_hangs = True
    await coordinator.async_refresh()
    assert coordinator.data["bluetooth_status"] == BT_STATUS_SUCCESS


async def test_start_max_read_hang_times_out(setup_integration, ble):
    ble.device_name = "Flipr 01234"  # triggers Start Max mode (direct read)
    ble.client = FakeBleakClient([_frame()])

    async def _hanging_read(uuid: str):
        await asyncio.Event().wait()

    ble.client.read_gatt_char = _hanging_read
    coord = await setup_integration(make_entry())
    assert coord.data["bluetooth_status"] == BT_STATUS_ERROR_RETRY


async def test_error_without_history_raises_update_failed(setup_integration, ble):
    ble.client = FakeBleakClient([build_frame(ph_mv=100)] * 3)
    coord = await setup_integration(make_entry())
    retries = 0
    while coord.data.get("bluetooth_status") == BT_STATUS_ERROR_RETRY and retries < 5:
        ble.client.frames = [build_frame(ph_mv=100 + retries)]
        await coord.async_refresh()
        retries += 1
    assert coord.last_update_success is False
    assert coord.data.get("ph_raw") is None


# ---------------------------------------------------------------------------
# Bluetooth availability
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "condition",
    [
        {"scanner_count": 0},
        {"last_seen_age": 500},
        {"last_seen_age": None},
        {"device_present": False},
    ],
)
async def test_unavailable_bluetooth_does_not_connect(coordinator, ble, condition):
    ble.establish.reset_mock()
    for attr, value in condition.items():
        setattr(ble, attr, value)
    await coordinator.async_refresh()
    ble.establish.assert_not_called()
    assert coordinator.data["bluetooth_status"] == BT_STATUS_OUT_OF_RANGE
    assert coordinator.data["ph"] is not None  # history kept


async def test_unavailable_bluetooth_without_history_fails(setup_integration, ble):
    ble.scanner_count = 0
    coord = await setup_integration(make_entry())
    assert coord.last_update_success is False


async def test_device_not_found_without_history_fails(setup_integration, ble):
    """Bluetooth reports the signal as available, but the BLEDevice itself
    isn't in Home Assistant's cache: with no prior history, this must fail
    the update instead of fabricating data."""
    ble.device_present = False
    coord = await setup_integration(make_entry())
    assert coord.last_update_success is False
    assert coord.data.get("ph_raw") is None


async def test_device_not_found_keeps_history(coordinator, ble):
    """Same scenario, but with prior history: the last known data must be
    kept rather than discarded."""
    ble.device_present = False
    before_ph = coordinator.data["ph"]
    await coordinator.async_refresh()
    assert coordinator.data["ph"] == before_ph
    assert coordinator.data["bluetooth_status"] == BT_STATUS_OUT_OF_RANGE


async def test_entry_removed_mid_cycle_fails_update(coordinator, hass):
    """If the config entry disappears between scheduling and running an
    update cycle, the cycle must fail cleanly instead of crashing."""
    original_async_get_entry = hass.config_entries.async_get_entry
    hass.config_entries.async_get_entry = lambda entry_id: None
    try:
        await coordinator.async_refresh()
        assert coordinator.last_update_success is False
    finally:
        hass.config_entries.async_get_entry = original_async_get_entry


def test_ble_available_property(coordinator, ble):
    assert coordinator.ble_available is True
    ble.last_seen_age = 119
    assert coordinator.ble_available is True
    ble.last_seen_age = 121
    assert coordinator.ble_available is False


async def test_signal_lost_and_found_callbacks(coordinator):
    coordinator._on_ble_unavailable(None)
    assert coordinator.data["bluetooth_status"] == BT_STATUS_OUT_OF_RANGE
    assert coordinator.ble_available is False

    coordinator._on_ble_seen(None, None)
    assert coordinator.data["bluetooth_status"] == BT_STATUS_WAITING


async def test_signal_found_does_not_resume_when_paused(coordinator):
    coordinator.update_volatile_state(
        {"active_measures": False, "bluetooth_status": BT_STATUS_OUT_OF_RANGE}
    )
    coordinator._on_ble_seen(None, None)
    assert coordinator.data["bluetooth_status"] == BT_STATUS_OUT_OF_RANGE


async def test_signal_lost_cancels_pending_retry(coordinator):
    """If a retry was already scheduled when the signal drops again, that
    stale timer must be cancelled rather than left to fire later."""
    cancels = []
    coordinator._retry_cancel = lambda: cancels.append(True)
    coordinator._on_ble_unavailable(None)
    assert cancels == [True]
    assert coordinator._retry_cancel is None


async def test_signal_seen_again_while_already_available_logs_recovery(coordinator):
    """If the status is still out_of_range but the coordinator never
    actually marked the signal as unavailable (previously_unavailable is
    False), it must still recover to \"waiting\" instead of staying stuck."""
    coordinator.update_volatile_state(
        {"active_measures": True, "bluetooth_status": BT_STATUS_OUT_OF_RANGE}
    )
    assert coordinator.ble_available is True  # not previously marked unavailable
    coordinator._on_ble_seen(None, None)
    assert coordinator.data["bluetooth_status"] == BT_STATUS_WAITING


# ---------------------------------------------------------------------------
# Pause / forced analysis / shutdown
# ---------------------------------------------------------------------------
async def test_paused_measurements_skip_connection(coordinator, ble):
    ble.establish.reset_mock()
    coordinator.update_volatile_state({"active_measures": False})
    await coordinator.async_refresh()
    ble.establish.assert_not_called()
    assert coordinator.data["bluetooth_status"] == BT_STATUS_PAUSED


async def test_one_shot_analysis_works_while_paused(coordinator, ble):
    coordinator.update_volatile_state({"active_measures": False})
    ble.client.frames = [_frame(3)]
    coordinator.request_one_shot_analysis()
    await coordinator.async_refresh()
    assert coordinator.data["battery"] == 3297
    assert coordinator.data["bluetooth_status"] == BT_STATUS_SUCCESS
    # The flag is consumed: the next cycle goes back to "paused".
    await coordinator.async_refresh()
    assert coordinator.data["bluetooth_status"] == BT_STATUS_PAUSED


async def test_no_connection_after_shutdown(coordinator, ble):
    await coordinator.async_shutdown()
    ble.establish.reset_mock()
    await coordinator.async_refresh()
    ble.establish.assert_not_called()


async def test_shutdown_cancels_pending_timers(coordinator, ble):
    ble.client.frames = [build_frame(ph_mv=100)]
    await coordinator.async_refresh()  # schedules a retry in 60 s
    assert coordinator._retry_cancel is not None
    await coordinator.async_shutdown()
    assert coordinator._retry_cancel is None
    assert coordinator._save_cancel is None


# ---------------------------------------------------------------------------
# Flipr Start Max (direct read, no notifications)
# ---------------------------------------------------------------------------
async def test_start_max_reads_characteristic_instead_of_notifying(
    setup_integration, ble
):
    ble.device_name = "Flipr 01234"
    ble.client = FakeBleakClient([_frame()])
    coord = await setup_integration(make_entry())
    assert not ble.client.notify_started
    assert ble.client.reads == 1
    assert coord.data["bluetooth_status"] == BT_STATUS_SUCCESS
    assert FLIPR_CHARACTERISTIC_UUID  # constant used for the read


async def test_start_max_unchanged_frame_ends_in_error(setup_integration, ble):
    ble.device_name = "Flipr 01234"
    same = _frame()
    ble.client = FakeBleakClient([same])
    coord = await setup_integration(make_entry())
    ble.client.frames = [same] * 3
    await coord.async_refresh()
    assert coord.data["bluetooth_status"] == BT_STATUS_ERROR_RETRY


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
async def test_save_strips_transient_state_and_serializes_datetime(
    coordinator, hass_storage
):
    await coordinator.async_save_to_disk()
    saved = hass_storage[store_key(MAC)]["data"]
    assert "bluetooth_status" not in saved
    assert "action_running" not in saved
    assert isinstance(saved["last_received"], str)
    assert saved["ph_raw"] == 1600


async def test_restore_from_disk_skips_initial_analysis(
    setup_integration, ble, hass_storage
):
    hass_storage[store_key(MAC)] = {
        "version": 1,
        "minor_version": 1,
        "key": store_key(MAC),
        "data": {
            "raw_frame": build_frame().hex().upper(),
            "last_received": "2026-01-02T03:04:05+00:00",
            "temperature": 24.0,
            "temp_raw": 24.0,
            "ph_raw": 1600,
            "ph": 7.1,
            "orp": 690,
            "tac": 90,
            # keys removed in 1.2.0: must not be re-injected
            "estimated_free_chlorine": 1.2,
            "active_chlorine_hocl": 0.05,
        },
    }
    coord = await setup_integration(make_entry())
    ble.establish.assert_not_called()
    assert coord.data["ph"] == 7.1
    assert coord.data["tac"] == 90
    assert coord.data["last_received"].year == 2026
    assert "estimated_free_chlorine" not in coord.data
    assert "active_chlorine_hocl" not in coord.data


async def test_restore_ignores_corrupted_timestamp(setup_integration, hass_storage):
    hass_storage[store_key(MAC)] = {
        "version": 1,
        "minor_version": 1,
        "key": store_key(MAC),
        "data": {"raw_frame": "AA" * 13, "ph_raw": 1600, "last_received": "not-a-date"},
    }
    coord = await setup_integration(make_entry())
    assert "last_received" not in coord.data


async def test_restore_skips_non_string_timestamp(setup_integration, hass_storage):
    """A last_received value that isn't a string (e.g. legacy/corrupted
    storage) must be left untouched rather than crash the parser."""
    hass_storage[store_key(MAC)] = {
        "version": 1,
        "minor_version": 1,
        "key": store_key(MAC),
        "data": {"raw_frame": "AA" * 13, "ph_raw": 1600, "last_received": 12345},
    }
    coord = await setup_integration(make_entry())
    assert coord.data["last_received"] == 12345


async def test_corrupted_reference_frame_is_ignored(coordinator, ble, caplog):
    coordinator.data["raw_frame"] = "ZZ" * 13  # 26 characters but not hex
    ble.client.frames = [_frame(2)]
    with caplog.at_level(logging.WARNING):
        await coordinator.async_refresh()
    assert "Corrupted raw_frame" in caplog.text
    assert coordinator.data["bluetooth_status"] == BT_STATUS_SUCCESS


# ---------------------------------------------------------------------------
# Forced analysis out of range
# ---------------------------------------------------------------------------
async def test_forced_analysis_connects_even_without_recent_advertisement(
    coordinator, ble
):
    await coordinator.async_refresh()
    ble.establish.reset_mock()
    ble.last_seen_age = 500
    ble.client.frames = [_frame(4)]
    coordinator.request_one_shot_analysis()
    await coordinator.async_refresh()
    ble.establish.assert_awaited_once()
    assert coordinator.data["bluetooth_status"] == BT_STATUS_SUCCESS
    assert coordinator.data["battery"] == 3296


async def test_scheduled_analysis_is_still_skipped_when_out_of_range(coordinator, ble):
    await coordinator.async_refresh()
    ble.establish.reset_mock()
    ble.last_seen_age = 500
    await coordinator.async_refresh()  # not forced
    ble.establish.assert_not_called()
    assert coordinator.data["bluetooth_status"] == BT_STATUS_OUT_OF_RANGE


async def test_forced_analysis_that_cannot_reach_the_device_is_out_of_range(
    coordinator, ble
):
    await coordinator.async_refresh()

    async def _lose_signal(*_a, **_k):
        raise TimeoutError

    ble.establish.side_effect = _lose_signal
    ble.last_seen_age = 500
    coordinator.request_one_shot_analysis()
    await coordinator.async_refresh()
    assert coordinator.data["bluetooth_status"] == BT_STATUS_OUT_OF_RANGE
    assert coordinator.data["ph"] is not None  # history kept


async def test_forced_flag_is_consumed_even_if_the_device_is_unknown(coordinator, ble):
    """Without this, the forced analysis would stay armed and bypass the pause later."""
    await coordinator.async_refresh()
    ble.device_present = False
    coordinator.request_one_shot_analysis()
    await coordinator.async_refresh()
    assert coordinator._force_one_shot is False
    assert coordinator.data["bluetooth_status"] == BT_STATUS_OUT_OF_RANGE


async def test_forced_flag_is_consumed_when_paused_and_out_of_range(coordinator, ble):
    await coordinator.async_refresh()
    coordinator.update_volatile_state({"active_measures": False})
    ble.scanner_count = 0
    ble.device_present = False
    coordinator.request_one_shot_analysis()
    await coordinator.async_refresh()
    assert coordinator._force_one_shot is False
    ble.establish.reset_mock()
    await coordinator.async_refresh()  # next cycle: paused again
    ble.establish.assert_not_called()
    assert coordinator.data["bluetooth_status"] == BT_STATUS_PAUSED


# ---------------------------------------------------------------------------
# Scheduling
# ---------------------------------------------------------------------------
async def test_schedule_is_aligned_on_reference_time(setup_integration):
    coord = await setup_integration(
        make_entry(**{CONF_SCAN_INTERVAL: 120, CONF_REFERENCE_TIME: "08:00"})
    )
    coord.update_schedule()
    slot = coord.next_slot
    assert slot.minute == 0
    assert (slot.hour - 8) % 2 == 0  # slots at 08:00, 10:00, 12:00...
    expected = (slot - dt_util.now()).total_seconds()
    assert coord.update_interval.total_seconds() == pytest.approx(expected, abs=1)


async def test_schedule_tolerates_garbage_reference_time(setup_integration):
    coord = await setup_integration(make_entry(**{CONF_REFERENCE_TIME: "garbage"}))
    coord.update_schedule()
    assert coord.next_slot is not None


def _armed_refresh_delay(hass, action) -> float:
    """Run `action` and return the delay (s) of the coordinator refresh timer it armed.

    Only the DataUpdateCoordinator refresh timer is captured (not the 2 s save
    debounce, which also goes through loop.call_at).
    """
    captured: list[float] = []
    real_call_at = hass.loop.call_at

    def spy(when, callback, *args, **kwargs):
        if "wrap_handle_refresh_interval" in getattr(callback, "__name__", ""):
            captured.append(when - hass.loop.time())
        return real_call_at(when, callback, *args, **kwargs)

    hass.loop.call_at = spy
    try:
        action()
    finally:
        hass.loop.call_at = real_call_at
    assert captured, "no refresh timer was armed"
    return captured[-1]


async def test_interval_change_rearms_refresh_timer_immediately(
    hass, setup_integration
):
    """A new Analysis Interval must be used by the very next timer, not one update later."""
    coord = await setup_integration(
        make_entry(**{CONF_SCAN_INTERVAL: 60, CONF_REFERENCE_TIME: "08:00"})
    )
    delay = _armed_refresh_delay(
        hass, lambda: coord.update_local_state({CONF_SCAN_INTERVAL: 5})
    )
    assert delay <= 5 * 60 + 2  # a 5 min interval: the next slot is at most 5 min away
    assert delay == pytest.approx(coord.update_interval.total_seconds(), abs=2.5)


async def test_reference_time_change_rearms_refresh_timer_immediately(
    hass, setup_integration
):
    from datetime import timedelta

    coord = await setup_integration(
        make_entry(**{CONF_SCAN_INTERVAL: 1440, CONF_REFERENCE_TIME: "08:00"})
    )
    new_ref = (dt_util.now() + timedelta(hours=3)).strftime("%H:%M")
    delay = _armed_refresh_delay(
        hass, lambda: coord.update_local_state({CONF_REFERENCE_TIME: new_ref})
    )
    assert delay == pytest.approx(3 * 3600, abs=90)  # HH:MM granularity


async def test_state_update_does_not_delay_the_timer_past_its_slot(
    hass, setup_integration, freezer
):
    """A status update 30 min after the last schedule computation must not re-arm the
    timer with the stale delay (60 min): the next slot is 30 min away."""
    from datetime import datetime

    coord = await setup_integration(
        make_entry(**{CONF_SCAN_INTERVAL: 60, CONF_REFERENCE_TIME: "08:00"})
    )
    tz = dt_util.get_default_time_zone()
    freezer.move_to(datetime(2026, 6, 1, 10, 0, 5, tzinfo=tz))
    coord.update_schedule()  # next slot 11:00 -> ~3595 s
    freezer.move_to(datetime(2026, 6, 1, 10, 30, 0, tzinfo=tz))

    delay = _armed_refresh_delay(
        hass, lambda: coord.update_volatile_state({"bluetooth_status": "waiting"})
    )
    assert delay == pytest.approx(30 * 60, abs=2.5)


async def test_slot_less_than_10_seconds_away_is_skipped(setup_integration, freezer):
    """5 s before the 11:00 slot, the next analysis is scheduled for 12:00."""
    from datetime import datetime

    coord = await setup_integration(
        make_entry(**{CONF_SCAN_INTERVAL: 60, CONF_REFERENCE_TIME: "08:00"})
    )
    tz = dt_util.get_default_time_zone()

    freezer.move_to(datetime(2026, 6, 1, 10, 59, 55, tzinfo=tz))
    coord.update_schedule()
    assert (coord.next_slot.hour, coord.next_slot.minute) == (12, 0)

    freezer.move_to(datetime(2026, 6, 1, 10, 59, 45, tzinfo=tz))
    coord.update_schedule()
    assert (coord.next_slot.hour, coord.next_slot.minute) == (11, 0)


async def test_update_schedule_noop_after_shutdown(coordinator):
    """update_schedule must be a no-op once the coordinator is shut down,
    so a stray late call cannot resurrect timers post-teardown."""
    next_slot_before = coordinator.next_slot
    coordinator._is_shutdown = True
    coordinator.update_schedule()
    assert coordinator.next_slot is next_slot_before


async def test_startup_with_no_recent_ble_signal_marks_out_of_range(
    setup_integration, ble
):
    """If Bluetooth has no recent advertisement for this device at startup,
    the coordinator must start out already flagged out_of_range."""
    ble.last_seen_age = None  # no cached advertisement at all
    coord = await setup_integration(make_entry())
    assert coord.data["bluetooth_status"] == BT_STATUS_OUT_OF_RANGE
    assert coord.ble_available is False


async def test_shutdown_swallows_final_save_error(coordinator):
    """A failure while persisting state during shutdown must not prevent
    shutdown from completing."""
    with patch.object(
        coordinator.store, "async_save", AsyncMock(side_effect=OSError("disk full"))
    ):
        await coordinator.async_shutdown()  # must not raise
    assert coordinator._is_shutdown is True


async def test_schedule_save_noop_after_shutdown(coordinator):
    """_schedule_save must not arm a new timer once shut down."""
    pending_before = coordinator._save_cancel
    coordinator._is_shutdown = True
    coordinator._schedule_save()
    # Unchanged: neither cancelled nor replaced by a new timer.
    assert coordinator._save_cancel is pending_before


async def test_do_save_noop_after_shutdown(coordinator):
    """A debounced save callback that fires after shutdown must bail out
    without touching disk."""
    # _do_save() only drops the Python reference to the pending timer, it
    # doesn't cancel it: cancel the real one scheduled during setup so it
    # doesn't trip the test framework's lingering-timer check.
    if coordinator._save_cancel:
        coordinator._save_cancel.cancel()
    coordinator._is_shutdown = True
    with patch.object(coordinator.store, "async_save", AsyncMock()) as mock_save:
        await coordinator._do_save()
    mock_save.assert_not_called()
    coordinator._is_shutdown = False


async def test_do_save_swallows_error(coordinator):
    """A failure during a debounced background save must be logged, not
    raised (it runs detached from any caller that could handle it)."""
    if coordinator._save_cancel:
        coordinator._save_cancel.cancel()
    with patch.object(
        coordinator.store, "async_save", AsyncMock(side_effect=OSError("disk full"))
    ):
        await coordinator._do_save()  # must not raise


async def test_schedule_save_callback_falls_back_without_entry(
    hass, coordinator, monkeypatch
):
    """If the config entry is gone by the time the debounced save timer
    fires, the save must still happen via hass.async_create_task."""
    monkeypatch.setattr(
        "custom_components.flipr_local.coordinator.SAVE_DEBOUNCE_DELAY", 0.01
    )
    original_async_get_entry = hass.config_entries.async_get_entry
    hass.config_entries.async_get_entry = lambda entry_id: None
    try:
        with patch.object(coordinator.store, "async_save", AsyncMock()) as mock_save:
            coordinator._schedule_save()
            await asyncio.sleep(0.05)
            await hass.async_block_till_done()
        mock_save.assert_called()
    finally:
        hass.config_entries.async_get_entry = original_async_get_entry


# ---------------------------------------------------------------------------
# Coverage: real behaviour paths not otherwise exercised
# ---------------------------------------------------------------------------
async def test_notification_queue_full_is_logged(setup_integration, ble, caplog):
    # 40 distinct frames delivered at once by the same write: the queue
    # (maxsize=32) is bound to overflow, which must be logged (not silent).
    frames = [_frame(i) for i in range(40)]
    ble.client = FakeBleakClient(frames=frames, frames_per_trigger=40)
    with caplog.at_level(logging.DEBUG):
        coord = await setup_integration(make_entry())
    assert "Notification queue full" in caplog.text
    # The cycle still succeeds: the last frames of the burst are enough.
    assert coord.data["bluetooth_status"] == BT_STATUS_SUCCESS


async def test_write_timeout_on_both_attempts_is_write_failed(coordinator, ble):
    coordinator.retry_count = 2  # retries already consumed
    ble.client.write_errors = [TimeoutError(), TimeoutError()]
    await coordinator.async_refresh()
    assert coordinator.data["bluetooth_status"] == BT_STATUS_WRITE_FAILED


async def test_stale_issue_handles_naive_last_received(coordinator):
    """A naive (tz-less) last_received timestamp must be treated as UTC
    instead of crashing the staleness check."""
    from datetime import datetime

    coordinator.data["last_received"] = datetime.now()  # naive, recent
    coordinator._check_stale_issue()  # must not raise


async def test_ph_calibration_falls_back_on_invalid_c7(coordinator, entry):
    """An invalid pH 7 calibration value must fall back to the factory
    default instead of propagating the ValueError."""
    hass = coordinator.hass
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, CONF_PH_CALIB_7: "not-a-number"}
    )
    _c4_mv, c7_mv, _ph_ref_4, _ph_ref_7 = coordinator._load_ph_calibration(entry)
    from custom_components.flipr_local.chemistry import get_mv_from_input
    from custom_components.flipr_local.const import DEFAULT_PH_CALIB_7

    assert c7_mv == get_mv_from_input(DEFAULT_PH_CALIB_7)


async def test_derive_measurements_with_no_raw_values_returns_empty(coordinator, entry):
    """With no raw temperature, pH or ORP reading, nothing should be
    derived (no crash, no fabricated data)."""
    assert coordinator._derive_measurements(entry, None, None, None) == {}


async def test_recompute_derived_values_noop_without_data(coordinator):
    coordinator.data.clear()
    coordinator.recompute_derived_values()  # must not raise
    assert coordinator.data == {}


async def test_recompute_derived_values_noop_when_entry_is_gone(hass, coordinator):
    original_async_get_entry = hass.config_entries.async_get_entry
    hass.config_entries.async_get_entry = lambda entry_id: None
    try:
        before = dict(coordinator.data)
        coordinator.recompute_derived_values()
        assert coordinator.data == before
    finally:
        hass.config_entries.async_get_entry = original_async_get_entry


async def test_async_update_data_short_circuits_after_shutdown(coordinator):
    coordinator._is_shutdown = True
    result = await coordinator._async_update_data()
    assert result == coordinator.data


async def test_deferred_recompute_noop_without_data(coordinator):
    """A debounced recompute that fires after the data has been cleared
    must not try to recompute anything."""
    captured = {}

    def _fake_call_later(hass_, delay, action):
        captured["action"] = action
        return lambda: None

    with patch(
        "custom_components.flipr_local.coordinator.async_call_later",
        _fake_call_later,
    ):
        coordinator.request_deferred_recompute()

    coordinator.data.clear()
    captured["action"](None)  # simulate the timer firing
    assert coordinator.data == {}


def _capture_retry_callback(coordinator, error_msg="Communication error: boom"):
    captured = {}

    def _fake_call_later(hass_, delay, action):
        captured["action"] = action
        return lambda: None

    with patch(
        "custom_components.flipr_local.coordinator.async_call_later",
        _fake_call_later,
    ):
        coordinator._handle_ble_error(error_msg, BT_STATUS_ERROR)
    return captured["action"]


async def test_retry_callback_noop_after_shutdown(coordinator):
    """A scheduled BLE-error retry that fires after shutdown must not try
    to request a refresh."""
    callback = _capture_retry_callback(coordinator)
    coordinator._is_shutdown = True
    coordinator.async_request_refresh = AsyncMock()
    callback(None)
    coordinator.async_request_refresh.assert_not_called()


async def test_retry_callback_uses_background_task_when_entry_present(
    hass, coordinator, entry
):
    """When the config entry is still there, the retry must be scheduled
    as a tracked background task on it."""
    callback = _capture_retry_callback(coordinator)
    with patch.object(entry, "async_create_background_task") as mock_bg_task:
        callback(None)
    mock_bg_task.assert_called_once()
    assert mock_bg_task.call_args.args[2] == "flipr_retry_refresh"
    mock_bg_task.call_args.args[1].close()  # avoid an un-awaited coroutine warning


async def test_retry_callback_falls_back_without_entry(hass, coordinator):
    """If the config entry is gone by the time the retry timer fires, the
    refresh must still be scheduled via hass.async_create_task."""
    callback = _capture_retry_callback(coordinator)
    original_async_get_entry = hass.config_entries.async_get_entry
    hass.config_entries.async_get_entry = lambda entry_id: None
    try:
        with patch.object(hass, "async_create_task") as mock_task:
            callback(None)
        mock_task.assert_called_once()
        mock_task.call_args.args[0].close()  # avoid an un-awaited coroutine warning
    finally:
        hass.config_entries.async_get_entry = original_async_get_entry
