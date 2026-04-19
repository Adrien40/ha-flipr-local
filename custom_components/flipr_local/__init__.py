# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

import logging
import asyncio
from typing import Any
import homeassistant.util.dt as dt_util
from bleak import BleakClient
from bleak_retry_connector import establish_connection
from time import monotonic
from homeassistant.components.bluetooth import (
    async_ble_device_from_address,
    async_last_service_info,
    async_scanner_count,
    async_register_callback,
    async_track_unavailable,
    BluetoothCallbackMatcher,
    BluetoothChange,
    BluetoothServiceInfoBleak,
    BluetoothScanningMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback, CALLBACK_TYPE
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.storage import Store
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .chemistry import (
    compute_isl,
    compute_active_chlorine_from_fc,
    estimate_free_chlorine,
    get_mv_from_input,
    compute_ph_equilibrium,
)
from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_MAC_ADDRESS,
    CONF_PH_CALIB_4,
    CONF_PH_CALIB_7,
    CONF_PH_REF_7,
    CONF_PH_REF_4,
    CONF_ORP_REF,
    CONF_ORP_CALIB,
    CONF_TEMP_OFFSET,
    CONF_CYA,
    CONF_TAC,
    CONF_TH,
    CONF_TDS,
    CONF_CHLORINE_MODEL,
    CONF_USE_GATEWAY,
    CONF_SYNC_MODE,
    FLIPR_CHARACTERISTIC_UUID,
    FLIPR_ANALYZE_UUID,
    SYNC_CHAR_UUID,
    PH_FACTORY_OFFSET,
    PH_FACTORY_SLOPE,
    BATTERY_MIN_MV,
    BATTERY_MAX_MV,
    DEFAULT_UPDATE_INTERVAL,
    TIMEOUT_BLE_CONN,
    SAVE_DEBOUNCE_DELAY,
    DEBOUNCE_COOLDOWN,
    VALID_SYNC_MODES,
    EXPECTED_FRAME_HEX_LEN,
    BT_STATUS_WAITING,
    BT_STATUS_CONNECTING,
    BT_STATUS_WAKING_UP,
    BT_STATUS_REQUESTING,
    BT_STATUS_READING,
    BT_STATUS_WRITING_SYNC,
    BT_STATUS_SUCCESS,
    BT_STATUS_SYNC_APPLIED,
    BT_STATUS_ERROR,
    BT_STATUS_ERROR_RETRY,
    BT_STATUS_WRITE_FAILED,
    BT_STATUS_PAUSED,
    BT_STATUS_OUT_OF_RANGE,
    DATA_ESTIMATED_FREE_CHLORINE,
    DATA_ACTIVE_CHLORINE_HOCL,
    DEFAULT_PH_CALIB_4,
    DEFAULT_PH_CALIB_7,
    DEFAULT_PH_REF_4,
    DEFAULT_PH_REF_7,
    DEFAULT_ORP_CALIB,
    DEFAULT_ORP_REF,
    BLE_RECENTLY_SEEN_THRESHOLD_S,
)

_LOGGER = logging.getLogger(__name__)

_TEMP_MIN_PLAUSIBLE = 0.0
_TEMP_MAX_PLAUSIBLE = 50.0
_ORP_MIN_PLAUSIBLE = 0.0
_ORP_MAX_PLAUSIBLE = 1500.0
_BAT_MIN_PLAUSIBLE = BATTERY_MIN_MV - 500
_BAT_MAX_PLAUSIBLE = BATTERY_MAX_MV + 500
_PH_MV_MIN_PLAUSIBLE = 500
_PH_MV_MAX_PLAUSIBLE = 3000

_BATTERY_DENOM = max(BATTERY_MAX_MV - BATTERY_MIN_MV, 1)


def _store_key(mac: str) -> str:
    return f"{DOMAIN}_{mac.replace(':', '').lower()}"


def _format_mac_safe(mac: str | None) -> str:
    if not mac or len(mac) < 17:
        return "XX:XX:XX:XX:XX:XX"
    return f"{mac[:8]}...{mac[-5:]}"


async def _safely_disconnect(client: BleakClient | None) -> None:
    if client and client.is_connected:
        try:
            await client.disconnect()
        except Exception as err:
            _LOGGER.debug("Ignored error during disconnect: %s", err)


def _get_opt(entry: ConfigEntry, key: str, default: Any = None) -> Any:
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
            name=f"Flipr {safe_mac}",
            update_interval=DEFAULT_UPDATE_INTERVAL,
        )
        self._entry_id = entry.entry_id
        self.mac = mac
        self.safe_mac = safe_mac
        self.store = Store(hass, 1, _store_key(mac))

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

        self._ble_available: bool = True
        self._ble_unavail_cancel: CALLBACK_TYPE | None = None
        self._ble_avail_cancel: CALLBACK_TYPE | None = None

        self.data: dict[str, Any] = {
            "active_measures": True,
            "action_running": False,
            "bluetooth_status": BT_STATUS_WAITING,
        }

        self.last_configured_sync_mode = entry.options.get(CONF_SYNC_MODE)
        self.last_configured_use_gw = _get_opt(entry, CONF_USE_GATEWAY, True)

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
        def _do_recompute(_now) -> None:
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

            self.data.update(saved_data)
            self._init_done = True
            _LOGGER.debug("Data restored from disk for %s", self.safe_mac)
        else:
            _LOGGER.debug("No valid history on disk for %s", self.safe_mac)

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

        # FIX: Cancel the debounce timer BEFORE saving. If the timer already fired and
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

    def update_local_state(self, updates: dict[str, Any]) -> None:
        new_data = {**self.data, **updates}
        self.async_set_updated_data(new_data)
        self._schedule_save()

    def update_volatile_state(self, updates: dict[str, Any]) -> None:
        new_data = {**self.data, **updates}
        self.async_set_updated_data(new_data)

    def _set_bt_status(self, status: str) -> None:
        self.update_volatile_state({"bluetooth_status": status})

    def _compute_ph_calibrated(
        self,
        ph_raw_mv: float,
        c4_mv: float,
        c7_mv: float,
        ph_ref_4: float,
        ph_ref_7: float,
    ) -> float:
        if abs(ph_ref_4 - ph_ref_7) < 1e-9:
            return 7.0
        slope = (float(c4_mv) - float(c7_mv)) / (ph_ref_4 - ph_ref_7)
        if abs(slope) < 1e-9:
            return 7.0
        return ph_ref_7 + (ph_raw_mv - float(c7_mv)) / slope

    def _load_ph_calibration(
        self, entry: ConfigEntry
    ) -> tuple[float, float, float, float]:
        raw_c4 = _get_opt(entry, CONF_PH_CALIB_4, DEFAULT_PH_CALIB_4)
        raw_c7 = _get_opt(entry, CONF_PH_CALIB_7, DEFAULT_PH_CALIB_7)
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
        ph_ref_7 = float(_get_opt(entry, CONF_PH_REF_7, DEFAULT_PH_REF_7))
        ph_ref_4 = float(_get_opt(entry, CONF_PH_REF_4, DEFAULT_PH_REF_4))
        return c4_mv, c7_mv, ph_ref_4, ph_ref_7

    def _build_chemistry_updates(
        self,
        temp: float | None,
        ph: float | None,
        orp: float | None,
        tac: float,
        th: float,
        tds: float,
        cya: float,
        chlorine_model: str,
    ) -> dict[str, Any]:
        updates: dict[str, Any] = {}

        if temp is not None and tac > 0 and th > 0:
            updates["target_equilibrium_ph"] = compute_ph_equilibrium(
                temp, tac, th, tds
            )
        else:
            updates["target_equilibrium_ph"] = None

        if temp is not None and ph is not None and tac > 0 and th > 0:
            lsi_val = compute_isl(temp, ph, tac, th, tds)
            updates["lsi"] = lsi_val
            if lsi_val is not None:
                if lsi_val < -0.3:
                    updates["lsi_status"] = "corrosive"
                elif lsi_val > 0.3:
                    updates["lsi_status"] = "scaling"
                else:
                    updates["lsi_status"] = "balanced"
            else:
                updates["lsi_status"] = "unknown"
        else:
            updates["lsi"] = None
            updates["lsi_status"] = "unknown"

        if ph is not None:
            if orp is None or chlorine_model == "bromine":
                updates[DATA_ESTIMATED_FREE_CHLORINE] = None
                updates[DATA_ACTIVE_CHLORINE_HOCL] = None
            else:
                fc = estimate_free_chlorine(orp, ph, cya)
                updates[DATA_ESTIMATED_FREE_CHLORINE] = fc
                updates[DATA_ACTIVE_CHLORINE_HOCL] = (
                    compute_active_chlorine_from_fc(
                        fc, ph, temp if temp is not None else 25.0, cya
                    )
                    if fc is not None
                    else None
                )
        else:
            updates[DATA_ESTIMATED_FREE_CHLORINE] = None
            updates[DATA_ACTIVE_CHLORINE_HOCL] = None

        return updates

    def recompute_derived_values(self) -> None:
        if not self.data:
            return

        current_entry = self.entry
        if not current_entry:
            return

        raw_temp = self.data.get("temp_raw", self.data.get("temperature"))
        ph_raw_mv = self.data.get("ph_raw")
        raw_orp = self.data.get("orp_raw")

        tac = self.data.get(CONF_TAC) or 0
        th = self.data.get(CONF_TH) or 0
        tds = self.data.get(CONF_TDS) or 0

        cya_raw = self.data.get(CONF_CYA)
        cya = float(cya_raw) if cya_raw is not None else 40.0

        chlorine_model = _get_opt(current_entry, CONF_CHLORINE_MODEL, "chlorine")
        updates: dict[str, Any] = {}

        temp_offset = float(_get_opt(current_entry, CONF_TEMP_OFFSET, 0.0))
        if raw_temp is not None:
            updates["temperature"] = round(raw_temp + temp_offset, 2)
            temp = updates["temperature"]
        else:
            temp = None

        if ph_raw_mv is not None:
            c4_mv, c7_mv, ph_ref_4, ph_ref_7 = self._load_ph_calibration(current_entry)
            ph_calculated = self._compute_ph_calibrated(
                ph_raw_mv, c4_mv, c7_mv, ph_ref_4, ph_ref_7
            )
            updates["ph"] = round(ph_calculated, 2)
            ph = updates["ph"]
        else:
            ph = self.data.get("ph")

        if raw_orp is not None:
            orp_target = float(_get_opt(current_entry, CONF_ORP_REF, DEFAULT_ORP_REF))
            orp_measured = float(
                _get_opt(current_entry, CONF_ORP_CALIB, DEFAULT_ORP_CALIB)
            )
            orp_offset = orp_target - orp_measured
            updates["orp"] = round(raw_orp + orp_offset)
            orp = updates["orp"]
        else:
            orp = self.data.get("orp")

        updates.update(
            self._build_chemistry_updates(
                temp, ph, orp, tac, th, tds, cya, chlorine_model
            )
        )

        # FIX: use `k not in self.data` to correctly detect keys that are new (not yet
        # present in self.data) even when their computed value is None. The previous
        # `self.data.get(k) != v` would silently skip a new key whose value is None,
        # since get() also returns None for missing keys — identical but not the same.
        changed_updates = {
            k: v for k, v in updates.items() if k not in self.data or self.data[k] != v
        }
        if changed_updates:
            self.update_volatile_state(changed_updates)

    def _parse_raw_frame(
        self, data: bytes
    ) -> tuple[float, float, float, str | None, int] | None:
        if len(data) < 13:
            _LOGGER.debug("Frame too short: %d bytes", len(data))
            return None
        try:
            raw_temp = int.from_bytes(data[0:2], "little") * 0.06
            ph_raw_mv = int.from_bytes(data[2:4], "little")
            raw_orp = int.from_bytes(data[4:6], "little") / 2.0
            sync_mode_raw = str(data[8])
            bat_raw = int.from_bytes(data[11:13], "little")
        except ValueError as e:
            _LOGGER.debug("Frame parsing error: %s", e)
            return None

        if not (_PH_MV_MIN_PLAUSIBLE <= ph_raw_mv <= _PH_MV_MAX_PLAUSIBLE):
            _LOGGER.warning("Implausible pH raw value %d mV", ph_raw_mv)
            return None

        if not (_TEMP_MIN_PLAUSIBLE <= raw_temp <= _TEMP_MAX_PLAUSIBLE):
            _LOGGER.warning("Implausible temperature value %.2f", raw_temp)
            return None

        if not (_ORP_MIN_PLAUSIBLE <= raw_orp <= _ORP_MAX_PLAUSIBLE):
            _LOGGER.warning("Implausible ORP value %.1f mV", raw_orp)
            return None

        if not (_BAT_MIN_PLAUSIBLE <= bat_raw <= _BAT_MAX_PLAUSIBLE):
            _LOGGER.warning("Implausible battery value %d mV", bat_raw)
            return None

        return raw_temp, ph_raw_mv, raw_orp, sync_mode_raw, bat_raw

    async def _async_update_data(self) -> dict[str, Any]:
        if self._is_shutdown:
            _LOGGER.debug(
                "Skipping update for %s: coordinator is shutting down",
                self.safe_mac,
            )
            return dict(self.data)

        if not self.data.get("active_measures", True):
            if self._force_one_shot:
                _LOGGER.debug("Force one-shot analysis requested for %s", self.safe_mac)
            else:
                _LOGGER.debug("Measurements paused by user for %s", self.safe_mac)
                self._set_bt_status(BT_STATUS_PAUSED)
                self.retry_count = 0
                return dict(self.data)

        if not self.ble_available:
            _LOGGER.debug(
                "Flipr %s: Bluetooth signal unavailable, connection ignored",
                self.safe_mac,
            )
            self._set_bt_status(BT_STATUS_OUT_OF_RANGE)
            self.retry_count = 0
            if self.data.get("ph_raw") is not None:
                return dict(self.data)
            raise UpdateFailed(
                f"Flipr {self.safe_mac} out of range and no history available"
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
                f"Flipr {self.safe_mac}: Bluetooth device not found despite recent signal"
            )

        force_was_set = self._force_one_shot
        self._force_one_shot = False
        if force_was_set:
            _LOGGER.debug("Manual analysis triggered for %s", self.safe_mac)

        current_entry = self.entry
        if not current_entry:
            raise UpdateFailed("Config entry no longer available")

        is_init_done = self._init_done
        use_gw = _get_opt(current_entry, CONF_USE_GATEWAY, True)

        if not is_init_done:
            if use_gw:
                cmd_type = "mode"
                cmd_val = int(_get_opt(current_entry, CONF_SYNC_MODE, "2"))
            else:
                cmd_type = "analyze"
                cmd_val = 0x01
        else:
            cmd_type = self._pending_cmd_type
            cmd_val = self._pending_cmd_val

        target_uuid = SYNC_CHAR_UUID if cmd_type == "mode" else FLIPR_ANALYZE_UUID

        old_raw_frame_hex = self.data.get("raw_frame") or ""
        try:
            # FIX: use EXPECTED_FRAME_HEX_LEN constant instead of magic number 26
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

        client: BleakClient | None = None
        notify_started = False
        received_payload: bytes | None = None

        loop = asyncio.get_running_loop()

        async with self.ble_lock:
            try:
                self._set_bt_status(BT_STATUS_CONNECTING)

                client = await asyncio.wait_for(
                    establish_connection(BleakClient, device, self.mac, max_attempts=3),
                    timeout=TIMEOUT_BLE_CONN,
                )

                received_data_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=32)

                def notification_handler(sender, data: bytes) -> None:
                    try:
                        loop.call_soon_threadsafe(received_data_queue.put_nowait, data)
                    except asyncio.QueueFull:
                        _LOGGER.debug(
                            "Notification queue full for %s, dropping frame",
                            self.safe_mac,
                        )

                await client.start_notify(
                    FLIPR_CHARACTERISTIC_UUID, notification_handler
                )
                notify_started = True

                reference_frame_bytes = old_raw_frame_bytes

                for attempt in range(1, 3):
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
                            timeout=15.0,
                        )
                    except asyncio.TimeoutError:
                        _LOGGER.warning(
                            "GATT write timed out for Flipr %s on attempt %d/2",
                            self.safe_mac,
                            attempt,
                        )
                        if attempt == 2:
                            return self._handle_ble_error(
                                "GATT write timed out", BT_STATUS_WRITE_FAILED
                            )
                        await asyncio.sleep(1.0)
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
                        await asyncio.sleep(1.0)
                        continue

                    self._set_bt_status(BT_STATUS_READING)

                    try:
                        timeout_limit = loop.time() + 60.0
                        while True:
                            time_left = timeout_limit - loop.time()
                            if time_left <= 0:
                                raise asyncio.TimeoutError()

                            payload = await asyncio.wait_for(
                                received_data_queue.get(), timeout=time_left
                            )

                            if len(payload) == 13:
                                if cmd_type == "mode":
                                    if (
                                        not reference_frame_bytes
                                        or payload != reference_frame_bytes
                                    ):
                                        received_payload = payload
                                        break
                                else:
                                    received_payload = payload
                                    break

                        if received_payload:
                            break

                    except asyncio.TimeoutError:
                        _LOGGER.warning(
                            "Timeout waiting for notification from Flipr %s on attempt %d/2.",
                            self.safe_mac,
                            attempt,
                        )

                if not received_payload:
                    return self._handle_ble_error(
                        "No notification received from Flipr after 120 seconds.",
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

            except asyncio.TimeoutError:
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
                        f"Flipr {self.safe_mac} unreachable after {TIMEOUT_BLE_CONN}s and no advertisement"
                    )
            except Exception as err:
                return self._handle_ble_error(
                    f"Communication error: {err}", BT_STATUS_ERROR
                )
            finally:
                if notify_started and client and client.is_connected:
                    try:
                        await client.stop_notify(FLIPR_CHARACTERISTIC_UUID)
                    except Exception:
                        pass
                await _safely_disconnect(client)

        self.retry_count = 0

        data = received_payload
        hex_frame = data.hex().upper()

        if hex_frame.startswith("0000"):
            # FIX: device in standby — reset retry_count so it doesn't accumulate
            # across standby cycles and cause spurious retry escalation.
            self.retry_count = 0
            return self._handle_ble_error(
                "Sensor is in standby or frame is empty", BT_STATUS_WAITING
            )

        parsed = self._parse_raw_frame(data)
        if parsed is None:
            return self._handle_ble_error("Payload parsing error", BT_STATUS_ERROR)

        raw_temp, ph_raw_mv, raw_orp, sync_mode_raw, bat_raw = parsed
        actual_sync_mode = sync_mode_raw if sync_mode_raw in VALID_SYNC_MODES else None

        temp_offset = float(_get_opt(current_entry, CONF_TEMP_OFFSET, 0.0))
        orp_target = float(_get_opt(current_entry, CONF_ORP_REF, DEFAULT_ORP_REF))
        orp_measured = float(_get_opt(current_entry, CONF_ORP_CALIB, DEFAULT_ORP_CALIB))
        orp_offset = orp_target - orp_measured

        temp = raw_temp + temp_offset
        orp = raw_orp + orp_offset

        c4_mv, c7_mv, ph_ref_4, ph_ref_7 = self._load_ph_calibration(current_entry)
        ph_calculated = self._compute_ph_calibrated(
            ph_raw_mv, c4_mv, c7_mv, ph_ref_4, ph_ref_7
        )
        factory_ph = PH_FACTORY_SLOPE * ph_raw_mv + PH_FACTORY_OFFSET

        tac_val = self.data.get(CONF_TAC) or 0
        th_val = self.data.get(CONF_TH) or 0
        tds_val = self.data.get(CONF_TDS) or 0

        cya_raw = self.data.get(CONF_CYA)
        cya_val = float(cya_raw) if cya_raw is not None else 40.0

        chlorine_model = _get_opt(current_entry, CONF_CHLORINE_MODEL, "chlorine")

        now = dt_util.utcnow()
        measurement_time = (
            (self.data.get("last_received") or now)
            if self.data.get("raw_frame") == hex_frame
            else now
        )

        bat_pct: int = round(
            max(0.0, min((bat_raw - BATTERY_MIN_MV) / _BATTERY_DENOM * 100.0, 100.0))
        )

        new_data: dict[str, Any] = {
            **self.data,
            "temp_raw": raw_temp,
            "temperature": round(temp, 2),
            "ph": round(ph_calculated, 2),
            "ph_raw": ph_raw_mv,
            "factory_ph": round(factory_ph, 2),
            "orp_raw": raw_orp,
            "orp": round(orp),
            "battery": bat_raw,
            "battery_level": bat_pct,
            "sync_mode": actual_sync_mode,
            "last_received": measurement_time,
            "raw_frame": hex_frame,
            "bluetooth_status": (
                BT_STATUS_SYNC_APPLIED if cmd_type == "mode" else BT_STATUS_SUCCESS
            ),
        }

        new_data.update(
            self._build_chemistry_updates(
                round(temp, 2),
                round(ph_calculated, 2),
                round(orp),
                tac_val,
                th_val,
                tds_val,
                cya_val,
                chlorine_model,
            )
        )
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
                "Bluetooth error for %s: %s. Retrying in 60s (Attempt %d/3)...",
                self.safe_mac,
                error_msg,
                self.retry_count,
            )
            if self._retry_cancel:
                self._retry_cancel()
                self._retry_cancel = None

            @callback
            def _trigger_retry(_now) -> None:
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

            self._retry_cancel = async_call_later(self.hass, 60, _trigger_retry)
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
        raise UpdateFailed(f"Flipr unreachable and no history: {error_msg}")


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    coordinator: FliprDataCoordinator | None = hass.data.get(DOMAIN, {}).get(
        entry.entry_id
    )
    if not coordinator:
        return

    new_sync_mode = entry.options.get(CONF_SYNC_MODE)
    new_use_gw = _get_opt(entry, CONF_USE_GATEWAY, True)

    mode_changed = new_sync_mode != coordinator.last_configured_sync_mode
    gw_changed = new_use_gw != coordinator.last_configured_use_gw

    coordinator.last_configured_sync_mode = new_sync_mode
    coordinator.last_configured_use_gw = new_use_gw

    coordinator.recompute_derived_values()

    async_dispatcher_send(
        hass,
        f"{DOMAIN}_{coordinator.mac}_options_updated",
    )

    if (mode_changed or gw_changed) and new_use_gw and new_sync_mode is not None:
        coordinator.set_pending_cmd("mode", int(new_sync_mode))
        coordinator.request_one_shot_analysis()
        if coordinator._is_shutdown:
            _LOGGER.debug(
                "Skipping sync mode refresh for %s: coordinator is shutting down",
                coordinator.safe_mac,
            )
            return
        if not coordinator.ble_lock.locked():
            entry.async_create_background_task(
                hass,
                coordinator.async_request_refresh(),
                "flipr_sync_mode_refresh",
            )
        else:
            _LOGGER.debug(
                "BLE lock already held for %s - sync mode refresh will apply on next cycle",
                coordinator.safe_mac,
            )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    mac = entry.data[CONF_MAC_ADDRESS]
    safe_mac = _format_mac_safe(mac)

    coordinator = FliprDataCoordinator(hass, entry, mac, safe_mac)
    await coordinator.async_initialize()

    hass.data[DOMAIN][entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not coordinator.data.get("ph_raw"):
        _LOGGER.debug("No history found, launching initial analysis.")
        entry.async_create_background_task(
            hass,
            coordinator.async_request_refresh(),
            "flipr_initial_refresh",
        )
    else:
        _LOGGER.debug("History found on disk, restoring state.")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if ok:
        coordinator: FliprDataCoordinator | None = hass.data[DOMAIN].get(entry.entry_id)
        if coordinator:
            await coordinator.async_shutdown()
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    mac = entry.data.get(CONF_MAC_ADDRESS)
    if mac:
        store = Store(hass, 1, _store_key(mac))
        await store.async_remove()
