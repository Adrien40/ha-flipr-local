# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

"""Flipr coordinator: BLE cycle, calibration, persistence."""

import asyncio
import logging
import math
from datetime import datetime, timedelta
from time import monotonic
from typing import Any

import homeassistant.util.dt as dt_util
from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak_retry_connector import establish_connection
from homeassistant.components.bluetooth import (
    BluetoothCallbackMatcher,
    BluetoothChange,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
    async_ble_device_from_address,
    async_last_service_info,
    async_register_callback,
    async_scanner_count,
    async_track_unavailable,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.issue_registry import (
    IssueSeverity,
    async_create_issue,
    async_delete_issue,
)
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .chemistry import (
    PH_MAX_VALID,
    PH_MIN_VALID,
    apply_orp_offset,
    classify_lsi,
    compute_factory_ph,
    compute_isl,
    compute_ph_calibrated,
    compute_ph_equilibrium,
    get_mv_from_input,
)
from .const import (
    BLE_RECENTLY_SEEN_THRESHOLD_S,
    BT_STATUS_CONNECTING,
    BT_STATUS_ERROR,
    BT_STATUS_ERROR_RETRY,
    BT_STATUS_OUT_OF_RANGE,
    BT_STATUS_PAUSED,
    BT_STATUS_READING,
    BT_STATUS_REQUESTING,
    BT_STATUS_SUCCESS,
    BT_STATUS_SYNC_APPLIED,
    BT_STATUS_WAITING,
    BT_STATUS_WAKING_UP,
    BT_STATUS_WRITE_FAILED,
    BT_STATUS_WRITING_SYNC,
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
    DEBOUNCE_COOLDOWN,
    DEFAULT_ORP_CALIB,
    DEFAULT_ORP_REF,
    DEFAULT_PH_CALIB_4,
    DEFAULT_PH_CALIB_7,
    DEFAULT_PH_REF_4,
    DEFAULT_PH_REF_7,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    ERROR_RETRY_DELAY,
    EXPECTED_FRAME_HEX_LEN,
    FLIPR_ANALYZE_UUID,
    FLIPR_CHARACTERISTIC_UUID,
    FRAME_LENGTH_BYTES,
    GATT_WRITE_RETRY_DELAY,
    GATT_WRITE_TIMEOUT,
    NOTIFY_WAIT_TIMEOUT,
    REMOVED_DATA_KEYS,
    REPAIR_STALE_AFTER,
    SAVE_DEBOUNCE_DELAY,
    START_MAX_READ_RETRY_WAIT,
    START_MAX_SILENT_WAIT,
    SYNC_CHAR_UUID,
    TIMEOUT_BLE_CONN,
    TIMEOUT_GATT_OP,
)
from .frame import battery_percent, is_standby_frame, parse_frame
from .model import get_flipr_model

_LOGGER = logging.getLogger(__name__)


def store_key(mac: str) -> str:
    return f"{DOMAIN}_{mac.replace(':', '').lower()}"


def format_mac_safe(mac: str | None) -> str:
    if not mac or len(mac) < 17:
        return "XX:XX:XX:XX:XX:XX"
    return f"{mac[:8]}...{mac[-5:]}"


async def _safely_disconnect(client: BleakClient | None) -> None:
    if client and client.is_connected:
        try:
            await asyncio.wait_for(client.disconnect(), timeout=TIMEOUT_GATT_OP)
        except Exception as err:
            _LOGGER.debug("Ignored error during disconnect: %s", err)


def get_opt(entry: ConfigEntry, key: str, default: Any = None) -> Any:
    if key in entry.options:
        return entry.options[key]
    if key in entry.data:
        return entry.data[key]
    return default


class FliprDataCoordinator(DataUpdateCoordinator):
    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, mac: str, safe_mac: str
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"Flipr {safe_mac}",
            update_interval=DEFAULT_UPDATE_INTERVAL,
        )
        self._entry_id = entry.entry_id
        self.mac = mac
        self.safe_mac = safe_mac
        self.store: Store[dict[str, Any]] = Store(hass, 1, store_key(mac))

        self.ble_lock = asyncio.Lock()
        self.retry_count = 0

        self._pending_cmd_type: str = "analyze"
        self._pending_cmd_val: int = 0x01
        self._init_done: bool = False

        self._retry_cancel: CALLBACK_TYPE | None = None
        self._recalc_cancel: CALLBACK_TYPE | None = None
        self._save_cancel: asyncio.TimerHandle | None = None
        self._force_one_shot: bool = False
        self._is_shutdown: bool = False
        self.next_slot: datetime | None = None

        self._ble_available: bool = True
        self._ble_unavail_cancel: CALLBACK_TYPE | None = None
        self._ble_avail_cancel: CALLBACK_TYPE | None = None

        self.data: dict[str, Any] = {
            "active_measures": True,
            "action_running": False,
            "bluetooth_status": BT_STATUS_WAITING,
        }

        self.last_configured_sync_mode = entry.options.get(CONF_SYNC_MODE)
        self.last_configured_use_gw = get_opt(entry, CONF_USE_GATEWAY, True)

        self.update_schedule()

    @property
    def entry_id(self) -> str:
        return self._entry_id

    @property
    def entry(self) -> ConfigEntry | None:
        return self.hass.config_entries.async_get_entry(self._entry_id)

    @property
    def ble_available(self) -> bool:
        if async_scanner_count(self.hass, connectable=False) == 0:
            return False
        if not self._ble_available:
            return False
        last_info = async_last_service_info(self.hass, self.mac, connectable=False)
        if last_info:
            return (monotonic() - last_info.time) <= BLE_RECENTLY_SEEN_THRESHOLD_S
        return False

    def request_one_shot_analysis(self) -> None:
        self._force_one_shot = True

    def request_deferred_recompute(self) -> None:
        if self._recalc_cancel:
            self._recalc_cancel()
            self._recalc_cancel = None

        @callback
        def _do_recompute(_now: datetime) -> None:
            self._recalc_cancel = None
            if self.data:
                self.recompute_derived_values()

        self._recalc_cancel = async_call_later(
            self.hass, DEBOUNCE_COOLDOWN, _do_recompute
        )

    def set_pending_cmd(self, cmd_type: str, cmd_val: int) -> None:
        self._pending_cmd_type = cmd_type
        self._pending_cmd_val = cmd_val

    @callback
    def _on_ble_unavailable(self, _info: BluetoothServiceInfoBleak) -> None:
        _LOGGER.debug("Flipr %s: BLE signal lost", self.safe_mac)
        self._ble_available = False
        self._set_bt_status(BT_STATUS_OUT_OF_RANGE)
        if self._retry_cancel:
            self._retry_cancel()
            self._retry_cancel = None
        self.retry_count = 0

    @callback
    def _on_ble_seen(
        self, _info: BluetoothServiceInfoBleak, _change: BluetoothChange
    ) -> None:
        previously_unavailable = not self._ble_available
        self._ble_available = True

        current_status = self.data.get("bluetooth_status")
        active = self.data.get("active_measures", True)

        if current_status == BT_STATUS_OUT_OF_RANGE and active:
            if previously_unavailable:
                _LOGGER.debug("Flipr %s: BLE signal found", self.safe_mac)
            else:
                _LOGGER.debug(
                    "Flipr %s: recovering from stale out_of_range status",
                    self.safe_mac,
                )
            self._set_bt_status(BT_STATUS_WAITING)

    async def async_initialize(self) -> None:
        saved_data = await self.store.async_load()

        if saved_data and "raw_frame" in saved_data:
            ts_val = saved_data.get("last_received")
            if isinstance(ts_val, str):
                parsed = dt_util.parse_datetime(ts_val)
                if parsed:
                    saved_data["last_received"] = parsed
                else:
                    saved_data.pop("last_received", None)

            for transient in ("bluetooth_status", "action_running"):
                saved_data.pop(transient, None)
            for obsolete in REMOVED_DATA_KEYS:
                saved_data.pop(obsolete, None)

            self.data.update(saved_data)
            self._init_done = True
            _LOGGER.debug("Data restored from disk for %s", self.safe_mac)
        else:
            _LOGGER.debug("No valid history on disk for %s", self.safe_mac)

        self.update_schedule()

        last_info = async_last_service_info(self.hass, self.mac, connectable=False)
        self._ble_available = (
            last_info is not None
            and (monotonic() - last_info.time) <= BLE_RECENTLY_SEEN_THRESHOLD_S
        )
        if not self._ble_available:
            _LOGGER.debug("Flipr %s: no recent BLE signal at startup", self.safe_mac)
            self.data["bluetooth_status"] = BT_STATUS_OUT_OF_RANGE

        self._ble_unavail_cancel = async_track_unavailable(
            self.hass,
            self._on_ble_unavailable,
            self.mac,
            connectable=False,
        )
        self._ble_avail_cancel = async_register_callback(
            self.hass,
            self._on_ble_seen,
            BluetoothCallbackMatcher(address=self.mac),
            BluetoothScanningMode.PASSIVE,
        )

    async def async_shutdown(self) -> None:
        self._is_shutdown = True
        # The parent cancels the scheduled refresh and the debouncer; without this
        # call, they would survive the entry unload.
        await super().async_shutdown()

        if self._ble_unavail_cancel:
            self._ble_unavail_cancel()
            self._ble_unavail_cancel = None
        if self._ble_avail_cancel:
            self._ble_avail_cancel()
            self._ble_avail_cancel = None

        if self._retry_cancel:
            self._retry_cancel()
            self._retry_cancel = None

        if self._recalc_cancel:
            self._recalc_cancel()
            self._recalc_cancel = None

        # Cancel the debounce timer BEFORE saving. If the timer already fired and
        # spawned _do_save as a background task, that task checks _is_shutdown and bails
        # out cleanly. The authoritative save is the direct call below.
        if self._save_cancel:
            self._save_cancel.cancel()
            self._save_cancel = None

        try:
            await self.async_save_to_disk()
        except Exception as err:
            _LOGGER.debug("Error during final save on shutdown: %s", err)

    async def async_save_to_disk(self) -> None:
        data_to_save = dict(self.data)

        ts_val = data_to_save.get("last_received")
        if ts_val is not None and hasattr(ts_val, "isoformat"):
            data_to_save["last_received"] = ts_val.isoformat()

        for transient in ("bluetooth_status", "action_running"):
            data_to_save.pop(transient, None)

        await self.store.async_save(data_to_save)

    def _schedule_save(self) -> None:
        if self._is_shutdown:
            return
        if self._save_cancel:
            self._save_cancel.cancel()
            self._save_cancel = None

        loop = asyncio.get_running_loop()
        entry_id = self._entry_id

        def _schedule_save_callback() -> None:
            self._save_cancel = None  # handle has fired — clear before spawning task
            entry = self.hass.config_entries.async_get_entry(entry_id)
            if entry:
                entry.async_create_background_task(
                    self.hass, self._do_save(), "flipr_scheduled_save"
                )
            else:
                self.hass.async_create_task(self._do_save())

        self._save_cancel = loop.call_later(
            SAVE_DEBOUNCE_DELAY, _schedule_save_callback
        )

    async def _do_save(self) -> None:
        self._save_cancel = None
        if self._is_shutdown:
            return
        try:
            await self.async_save_to_disk()
        except Exception as err:
            _LOGGER.debug("Save failed: %s", err)

    def update_schedule(self) -> None:
        """Align the next scheduled analysis on a slot (interval + reference time).

        Flipr always operates actively (no
        access-code-gated passive mode), so this always computes a slot-aligned
        schedule instead of falling back to a flat interval.
        """
        if self._is_shutdown:
            return

        entry = self.entry
        if not entry:
            return

        interval_m = self.data.get(CONF_SCAN_INTERVAL)
        if interval_m is None:
            interval_m = get_opt(entry, CONF_SCAN_INTERVAL, 60)

        ref_time_str = self.data.get(CONF_REFERENCE_TIME)
        if ref_time_str is None:
            ref_time_str = get_opt(entry, CONF_REFERENCE_TIME, "08:00")

        try:
            parts = ref_time_str.split(":")
            hour = int(parts[0]) if len(parts) > 0 else 0
            minute = int(parts[1]) if len(parts) > 1 else 0
        # PEP 758 (Python 3.14): parentheses are optional when there is no `as` clause. Intentional.
        except ValueError, AttributeError, IndexError:
            hour, minute = 0, 0

        now = dt_util.now()
        base_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        interval_s = interval_m * 60
        delta_seconds = (now - base_dt).total_seconds()

        n_slots = math.floor(delta_seconds / interval_s)
        last_slot = base_dt + timedelta(seconds=n_slots * interval_s)
        next_slot = last_slot + timedelta(seconds=interval_s)

        if (next_slot - now).total_seconds() < 10:
            next_slot += timedelta(seconds=interval_s)

        self.next_slot = next_slot
        self.update_interval = next_slot - now
        _LOGGER.debug(
            "Flipr %s: Next scheduled analysis aligned to %s",
            self.safe_mac,
            next_slot.strftime("%H:%M:%S"),
        )

    def _publish(self, new_data: dict[str, Any]) -> None:
        """Publish new data with a schedule computed from that data, right now.

        `async_set_updated_data` re-arms the refresh timer with the *current*
        `update_interval`. The schedule must therefore be recomputed BEFORE it
        (from the new data, which `update_schedule` reads from `self.data`):
        computed after, a new interval / reference time would only take effect
        one update late, and the timer would keep the delay computed at the
        previous call (drifting later than the slot by the time elapsed since).
        """
        self.data = new_data
        self.update_schedule()
        self.async_set_updated_data(new_data)

    def update_local_state(self, updates: dict[str, Any]) -> None:
        self._publish({**self.data, **updates})
        self._schedule_save()

    def update_volatile_state(self, updates: dict[str, Any]) -> None:
        self._publish({**self.data, **updates})

    def _set_bt_status(self, status: str) -> None:
        self.update_volatile_state({"bluetooth_status": status})

    def _issue_id(self) -> str:
        return f"stale_{self.safe_mac}"

    def _check_stale_issue(self) -> None:
        """Create a repair issue if unreachable for longer than REPAIR_STALE_AFTER."""
        last = self.data.get("last_received")
        if not last:
            return
        if last.tzinfo is None:
            last = dt_util.as_utc(last)
        age = dt_util.utcnow() - last
        if age < REPAIR_STALE_AFTER:
            return
        async_create_issue(
            self.hass,
            DOMAIN,
            self._issue_id(),
            is_fixable=False,
            is_persistent=False,
            severity=IssueSeverity.WARNING,
            translation_key="device_unreachable",
            translation_placeholders={
                "name": self.safe_mac,
                "days": str(age.days),
            },
        )

    def _clear_stale_issue(self) -> None:
        async_delete_issue(self.hass, DOMAIN, self._issue_id())

    def _load_ph_calibration(
        self, entry: ConfigEntry
    ) -> tuple[float, float, float, float]:
        raw_c4 = get_opt(entry, CONF_PH_CALIB_4, DEFAULT_PH_CALIB_4)
        raw_c7 = get_opt(entry, CONF_PH_CALIB_7, DEFAULT_PH_CALIB_7)
        try:
            c4_mv = get_mv_from_input(raw_c4)
        except ValueError:
            _LOGGER.warning(
                "Invalid pH 4 calibration value '%s' for %s - using factory default",
                raw_c4,
                self.safe_mac,
            )
            c4_mv = get_mv_from_input(DEFAULT_PH_CALIB_4)
        try:
            c7_mv = get_mv_from_input(raw_c7)
        except ValueError:
            _LOGGER.warning(
                "Invalid pH 7 calibration value '%s' for %s - using factory default",
                raw_c7,
                self.safe_mac,
            )
            c7_mv = get_mv_from_input(DEFAULT_PH_CALIB_7)
        ph_ref_7 = float(get_opt(entry, CONF_PH_REF_7, DEFAULT_PH_REF_7))
        ph_ref_4 = float(get_opt(entry, CONF_PH_REF_4, DEFAULT_PH_REF_4))
        return c4_mv, c7_mv, ph_ref_4, ph_ref_7

    def _calibrated_ph(self, entry: ConfigEntry, ph_raw_mv: float) -> float | None:
        """Calibrated pH, or None if the result is physically impossible."""
        c4_mv, c7_mv, ph_ref_4, ph_ref_7 = self._load_ph_calibration(entry)
        try:
            ph = compute_ph_calibrated(ph_raw_mv, c4_mv, c7_mv, ph_ref_4, ph_ref_7)
        except ValueError:
            _LOGGER.warning(
                "Degenerate pH calibration for %s - falling back to factory calibration",
                self.safe_mac,
            )
            ph = compute_factory_ph(ph_raw_mv)

        if not PH_MIN_VALID <= ph <= PH_MAX_VALID:
            _LOGGER.warning(
                "Computed pH %.2f for %s is out of the physical range - ignored",
                ph,
                self.safe_mac,
            )
            return None
        return round(ph, 2)

    def _derive_measurements(
        self,
        entry: ConfigEntry,
        raw_temp: float | None,
        ph_raw_mv: float | None,
        raw_orp: float | None,
    ) -> dict[str, Any]:
        """Apply offsets and calibrations to the probes' raw values.

        Only measurements whose raw value is provided are returned.
        """
        derived: dict[str, Any] = {}
        if raw_temp is not None:
            temp_offset = float(get_opt(entry, CONF_TEMP_OFFSET, 0.0))
            derived["temperature"] = round(raw_temp + temp_offset, 2)
        if ph_raw_mv is not None:
            derived["factory_ph"] = round(compute_factory_ph(ph_raw_mv), 2)
            derived["ph"] = self._calibrated_ph(entry, ph_raw_mv)
        if raw_orp is not None:
            derived["orp"] = apply_orp_offset(
                raw_orp,
                float(get_opt(entry, CONF_ORP_REF, DEFAULT_ORP_REF)),
                float(get_opt(entry, CONF_ORP_CALIB, DEFAULT_ORP_CALIB)),
            )
        return derived

    @staticmethod
    def _build_chemistry_updates(
        temp: float | None,
        ph: float | None,
        tac: float,
        th: float,
        tds: float,
    ) -> dict[str, Any]:
        """Langelier indices; None if an input is missing (see chemistry.py)."""
        lsi = compute_isl(temp, ph, tac, th, tds)
        return {
            "target_equilibrium_ph": compute_ph_equilibrium(temp, tac, th, tds),
            "lsi": lsi,
            "lsi_status": classify_lsi(lsi),
        }

    def recompute_derived_values(self) -> None:
        if not self.data:
            return

        current_entry = self.entry
        if not current_entry:
            return

        raw_temp = self.data.get("temp_raw", self.data.get("temperature"))
        tac = self.data.get(CONF_TAC) or 0
        th = self.data.get(CONF_TH) or 0
        tds = self.data.get(CONF_TDS) or 0

        updates = self._derive_measurements(
            current_entry,
            raw_temp,
            self.data.get("ph_raw"),
            self.data.get("orp_raw"),
        )
        # Without a raw value, keep the last known measurement.
        temp = updates.get("temperature")
        ph = updates["ph"] if "ph" in updates else self.data.get("ph")
        updates.update(self._build_chemistry_updates(temp, ph, tac, th, tds))

        # `k not in self.data` catches new keys even when their value is
        # None (get() would return None in both cases).
        changed_updates = {
            k: v for k, v in updates.items() if k not in self.data or self.data[k] != v
        }
        if changed_updates:
            self.update_volatile_state(changed_updates)

    async def _async_update_data(self) -> dict[str, Any]:
        if self._is_shutdown:
            _LOGGER.debug(
                "Skipping update for %s: coordinator is shutting down",
                self.safe_mac,
            )
            return dict(self.data)

        # Forced analysis (button, mode change): consumed for this cycle regardless
        # of the outcome, so it cannot bypass the pause on the next cycle.
        force_one_shot = self._force_one_shot
        self._force_one_shot = False

        if not self.data.get("active_measures", True):
            if force_one_shot:
                _LOGGER.debug("Force one-shot analysis requested for %s", self.safe_mac)
            else:
                _LOGGER.debug("Measurements paused by user for %s", self.safe_mac)
                self._set_bt_status(BT_STATUS_PAUSED)
                self.retry_count = 0
                return dict(self.data)

        # A forced analysis still attempts the connection even if
        # no recent advertisement was received; only scheduled measurements are skipped.
        if not self.ble_available and not force_one_shot:
            _LOGGER.debug(
                "Flipr %s: Bluetooth signal unavailable, connection ignored",
                self.safe_mac,
            )
            self._set_bt_status(BT_STATUS_OUT_OF_RANGE)
            self.retry_count = 0
            self._check_stale_issue()
            if self.data.get("ph_raw") is not None:
                return dict(self.data)
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="out_of_range_no_history",
                translation_placeholders={"mac": self.safe_mac},
            )

        device = async_ble_device_from_address(self.hass, self.mac, connectable=True)
        if not device:
            device = async_ble_device_from_address(
                self.hass, self.mac, connectable=False
            )
        if not device:
            _LOGGER.debug(
                "Flipr %s: ble_available is True but BLEDevice is missing from cache",
                self.safe_mac,
            )
            self._set_bt_status(BT_STATUS_OUT_OF_RANGE)
            self.retry_count = 0
            if self.data.get("ph_raw") is not None:
                return dict(self.data)
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="device_not_found",
                translation_placeholders={"mac": self.safe_mac},
            )

        if force_one_shot:
            _LOGGER.debug("Manual analysis triggered for %s", self.safe_mac)

        current_entry = self.entry
        if not current_entry:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="entry_not_available",
            )

        is_init_done = self._init_done
        use_gw = get_opt(current_entry, CONF_USE_GATEWAY, True)

        if not is_init_done:
            if use_gw:
                cmd_type = "mode"
                cmd_val = int(get_opt(current_entry, CONF_SYNC_MODE, "2"))
            else:
                cmd_type = "analyze"
                cmd_val = 0x01
        else:
            cmd_type = self._pending_cmd_type
            cmd_val = self._pending_cmd_val

        target_uuid = SYNC_CHAR_UUID if cmd_type == "mode" else FLIPR_ANALYZE_UUID

        old_raw_frame_hex = self.data.get("raw_frame") or ""
        try:
            old_raw_frame_bytes = (
                bytes.fromhex(old_raw_frame_hex)
                if len(old_raw_frame_hex) == EXPECTED_FRAME_HEX_LEN
                else b""
            )
        except ValueError:
            _LOGGER.warning(
                "Corrupted raw_frame in storage for %s ('%s') — ignoring reference frame",
                self.safe_mac,
                old_raw_frame_hex,
            )
            old_raw_frame_bytes = b""

        # Identify model once before connecting to drive both connection options
        # and the data-reading strategy, without any GATT introspection.
        is_start_max = get_flipr_model(device.name).startswith("Flipr Start")

        client: BleakClient | None = None
        notify_started = False
        received_payload: bytes | None = None

        loop = asyncio.get_running_loop()

        async with self.ble_lock:
            try:
                self._set_bt_status(BT_STATUS_CONNECTING)

                client = await asyncio.wait_for(
                    establish_connection(
                        BleakClient,
                        device,
                        self.mac,
                        max_attempts=3,
                        use_services_cache=not is_start_max,
                    ),
                    timeout=TIMEOUT_BLE_CONN,
                )
                assert client is not None

                received_data_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=32)

                def _put(data: bytes) -> None:
                    try:
                        received_data_queue.put_nowait(data)
                    except asyncio.QueueFull:
                        _LOGGER.debug(
                            "Notification queue full for %s, dropping frame",
                            self.safe_mac,
                        )

                def notification_handler(
                    sender: BleakGATTCharacteristic, data: bytearray
                ) -> None:
                    loop.call_soon_threadsafe(_put, bytes(data))

                if not is_start_max:
                    await asyncio.wait_for(
                        client.start_notify(
                            FLIPR_CHARACTERISTIC_UUID, notification_handler
                        ),
                        timeout=TIMEOUT_GATT_OP,
                    )
                    notify_started = True

                reference_frame_bytes = old_raw_frame_bytes

                for attempt in range(1, 3):
                    if not is_start_max:
                        while not received_data_queue.empty():
                            received_data_queue.get_nowait()

                    if cmd_type == "mode":
                        self._set_bt_status(BT_STATUS_WRITING_SYNC)
                        _LOGGER.info(
                            "Sending sync mode %s to Flipr %s - Attempt %d/2",
                            cmd_val,
                            self.safe_mac,
                            attempt,
                        )
                    else:
                        self._set_bt_status(
                            BT_STATUS_WAKING_UP
                            if not is_init_done
                            else BT_STATUS_REQUESTING
                        )

                    try:
                        await asyncio.wait_for(
                            client.write_gatt_char(
                                target_uuid, bytearray([cmd_val]), response=True
                            ),
                            timeout=GATT_WRITE_TIMEOUT,
                        )
                    except TimeoutError:
                        _LOGGER.warning(
                            "GATT write timed out for Flipr %s on attempt %d/2",
                            self.safe_mac,
                            attempt,
                        )
                        if attempt == 2:
                            return self._handle_ble_error(
                                "GATT write timed out", BT_STATUS_WRITE_FAILED
                            )
                        await asyncio.sleep(GATT_WRITE_RETRY_DELAY)
                        continue
                    except Exception as write_err:
                        _LOGGER.warning(
                            "GATT write failed for Flipr %s on attempt %d/2: %s",
                            self.safe_mac,
                            attempt,
                            write_err,
                        )
                        if attempt == 2:
                            return self._handle_ble_error(
                                f"GATT write failed: {write_err}",
                                BT_STATUS_WRITE_FAILED,
                            )
                        await asyncio.sleep(GATT_WRITE_RETRY_DELAY)
                        continue

                    self._set_bt_status(BT_STATUS_READING)

                    try:
                        if not is_start_max:
                            timeout_limit = loop.time() + NOTIFY_WAIT_TIMEOUT
                            while True:
                                time_left = timeout_limit - loop.time()
                                if time_left <= 0:
                                    raise TimeoutError()

                                payload = await asyncio.wait_for(
                                    received_data_queue.get(), timeout=time_left
                                )

                                # Full byte-equality check (not just the decoded fields): the
                                # device embeds a rolling counter/checksum in the unused bytes
                                # (see frame.py), so two consecutive frames are never identical
                                # even at constant water values — safe way to detect "new data
                                # received" rather than a risk of false rejection.
                                if len(payload) == FRAME_LENGTH_BYTES and (
                                    not reference_frame_bytes
                                    or payload != reference_frame_bytes
                                ):
                                    received_payload = payload
                                    break

                            if received_payload:
                                break

                        else:
                            _LOGGER.info(
                                "Flipr %s: Start Max detected. Holding silent connection for 35s to allow internal measurement...",
                                self.safe_mac,
                            )
                            await asyncio.sleep(START_MAX_SILENT_WAIT)

                            for read_retry in range(3):
                                if read_retry > 0:
                                    _LOGGER.debug(
                                        "Flipr %s: Frame unchanged, waiting 8s more...",
                                        self.safe_mac,
                                    )
                                    await asyncio.sleep(START_MAX_READ_RETRY_WAIT)

                                try:

                                    async def _read() -> bytes:
                                        return bytes(
                                            await client.read_gatt_char(
                                                FLIPR_CHARACTERISTIC_UUID
                                            )
                                        )

                                    payload = await asyncio.wait_for(
                                        _read(), timeout=TIMEOUT_GATT_OP
                                    )
                                    _LOGGER.debug(
                                        "Flipr %s: Read attempt %d: %s | REF: %s",
                                        self.safe_mac,
                                        read_retry + 1,
                                        payload.hex().upper(),
                                        reference_frame_bytes.hex().upper()
                                        if reference_frame_bytes
                                        else "NONE",
                                    )

                                    # Same rationale as the notify branch above: the rolling
                                    # counter/checksum in the frame's unused bytes guarantees
                                    # byte-inequality on every genuinely new frame, even when
                                    # the measured values themselves haven't moved.
                                    if len(payload) == FRAME_LENGTH_BYTES and (
                                        not reference_frame_bytes
                                        or payload != reference_frame_bytes
                                    ):
                                        received_payload = payload
                                        break
                                except Exception as read_err:
                                    _LOGGER.debug(
                                        "Flipr %s: Error reading after silent wait: %s",
                                        self.safe_mac,
                                        read_err,
                                    )

                            if received_payload:
                                break

                            raise TimeoutError()

                    except TimeoutError:
                        _LOGGER.warning(
                            "Timeout waiting for new data from Flipr %s on attempt %d/2.",
                            self.safe_mac,
                            attempt,
                        )

                if not received_payload:
                    return self._handle_ble_error(
                        "No valid data received from Flipr after 120 seconds.",
                        BT_STATUS_ERROR,
                    )

                if not is_init_done:
                    self._init_done = True

                # Only reset if _pending_cmd_type hasn't been changed by update_listener
                # during this BLE cycle (race condition guard).
                # is_init_done guard: on the init cycle, cmd_type comes from config (not
                # from _pending_cmd_type), so the equality check would be accidentally True
                # even if update_listener wrote a new "mode" command during the cycle.
                if is_init_done and self._pending_cmd_type == cmd_type:
                    self._pending_cmd_type = "analyze"
                    self._pending_cmd_val = 0x01

            except TimeoutError:
                last_info_now = async_last_service_info(
                    self.hass, self.mac, connectable=False
                )
                still_advertising = (
                    last_info_now is not None
                    and (monotonic() - last_info_now.time)
                    <= BLE_RECENTLY_SEEN_THRESHOLD_S
                )
                if still_advertising:
                    _LOGGER.warning(
                        "Connection timeout (>%ss) for %s but device is still advertising — treating as transient error",
                        TIMEOUT_BLE_CONN,
                        self.safe_mac,
                    )
                    return self._handle_ble_error(
                        f"Connection timed out after {TIMEOUT_BLE_CONN}s (device still advertising)",
                        BT_STATUS_ERROR,
                    )
                else:
                    _LOGGER.warning(
                        "Connection timeout (>%ss) for %s and no recent advertisement — marking out of range",
                        TIMEOUT_BLE_CONN,
                        self.safe_mac,
                    )
                    self.retry_count = 0
                    self._set_bt_status(BT_STATUS_OUT_OF_RANGE)
                    if self.data.get("ph_raw") is not None:
                        return dict(self.data)
                    raise UpdateFailed(
                        translation_domain=DOMAIN,
                        translation_key="connection_timeout_no_history",
                        translation_placeholders={
                            "mac": self.safe_mac,
                            "timeout": str(TIMEOUT_BLE_CONN),
                        },
                    ) from None
            except Exception as err:
                return self._handle_ble_error(
                    f"Communication error: {err}", BT_STATUS_ERROR
                )
            finally:
                if notify_started and client and client.is_connected:
                    try:
                        await asyncio.wait_for(
                            client.stop_notify(FLIPR_CHARACTERISTIC_UUID),
                            timeout=TIMEOUT_GATT_OP,
                        )
                    except Exception:
                        pass
                await _safely_disconnect(client)

        data = received_payload
        hex_frame = data.hex().upper()
        self._clear_stale_issue()

        if is_standby_frame(data):
            # Sensor in standby: reset retry_count to zero to avoid an escalation
            # of attempts accumulated across several standby cycles.
            self.retry_count = 0
            return self._handle_ble_error(
                "Sensor is in standby or frame is empty", BT_STATUS_WAITING
            )

        frame = parse_frame(data)
        if frame is None:
            return self._handle_ble_error("Payload parsing error", BT_STATUS_ERROR)

        # Only reset now: before, an invalid frame reset the counter to 0 on
        # every cycle and the retry budget never ran out.
        self.retry_count = 0

        derived = self._derive_measurements(
            current_entry, frame.temperature, frame.ph_mv, frame.orp
        )

        tac_val = self.data.get(CONF_TAC) or 0
        th_val = self.data.get(CONF_TH) or 0
        tds_val = self.data.get(CONF_TDS) or 0

        now = dt_util.utcnow()
        measurement_time = (
            (self.data.get("last_received") or now)
            if self.data.get("raw_frame") == hex_frame
            else now
        )

        new_data: dict[str, Any] = {
            **self.data,
            "temp_raw": frame.temperature,
            "ph_raw": frame.ph_mv,
            "orp_raw": frame.orp,
            **derived,
            "battery": frame.battery_mv,
            "battery_level": battery_percent(frame.battery_mv),
            "sync_mode": frame.sync_mode,
            "last_received": measurement_time,
            "raw_frame": hex_frame,
            "bluetooth_status": (
                BT_STATUS_SYNC_APPLIED if cmd_type == "mode" else BT_STATUS_SUCCESS
            ),
        }
        new_data.update(
            self._build_chemistry_updates(
                derived["temperature"], derived["ph"], tac_val, th_val, tds_val
            )
        )
        self.update_schedule()
        self._schedule_save()
        return new_data

    def _handle_ble_error(
        self,
        error_msg: str,
        status: str = BT_STATUS_ERROR,
    ) -> dict[str, Any]:
        if status in (BT_STATUS_ERROR, BT_STATUS_WRITE_FAILED) and self.retry_count < 2:
            self.retry_count += 1
            self._set_bt_status(BT_STATUS_ERROR_RETRY)
            _LOGGER.warning(
                "Bluetooth error for %s: %s. Retrying in %ds (Attempt %d/3)...",
                self.safe_mac,
                error_msg,
                ERROR_RETRY_DELAY,
                self.retry_count,
            )
            if self._retry_cancel:
                self._retry_cancel()
                self._retry_cancel = None

            @callback
            def _trigger_retry(_now: datetime) -> None:
                self._retry_cancel = None
                if self._is_shutdown:
                    _LOGGER.debug(
                        "Skipping retry for %s: coordinator is shutting down",
                        self.safe_mac,
                    )
                    return
                entry = self.hass.config_entries.async_get_entry(self._entry_id)
                if entry:
                    entry.async_create_background_task(
                        self.hass,
                        self.async_request_refresh(),
                        "flipr_retry_refresh",
                    )
                else:
                    self.hass.async_create_task(self.async_request_refresh())

            self._retry_cancel = async_call_later(
                self.hass, ERROR_RETRY_DELAY, _trigger_retry
            )
            return dict(self.data)

        self._set_bt_status(status)
        if status in (BT_STATUS_ERROR, BT_STATUS_OUT_OF_RANGE, BT_STATUS_WRITE_FAILED):
            _LOGGER.error(
                "Flipr %s unreachable after retries: %s",
                self.safe_mac,
                error_msg,
            )
            self.retry_count = 0

        if self.data.get("ph_raw") is not None:
            return dict(self.data)
        raise UpdateFailed(
            translation_domain=DOMAIN,
            translation_key="unreachable_no_history",
            translation_placeholders={"error": error_msg},
        )
