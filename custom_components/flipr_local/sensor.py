# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

from __future__ import annotations

from datetime import datetime as dt_datetime
from typing import Any
import logging
import homeassistant.util.dt as dt_util
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
    RestoreSensor,
)
from homeassistant.components.bluetooth import (
    async_register_callback,
    BluetoothCallbackMatcher,
    BluetoothChange,
    BluetoothServiceInfoBleak,
    async_last_service_info,
    BluetoothScanningMode,
)
from homeassistant.const import UnitOfTemperature, EntityCategory
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import (
    DOMAIN,
    CONF_MAC_ADDRESS,
    CONF_CHLORINE_MODEL,
    get_flipr_model,
    flipr_device_info,
    DATA_ESTIMATED_FREE_CHLORINE,
    DATA_ACTIVE_CHLORINE_HOCL,
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
)

_LOGGER = logging.getLogger(__name__)

# Sensors whose availability depends on the selected chlorine model.
_CHLORINE_MODEL_DEPENDENT_KEYS = frozenset(
    {DATA_ESTIMATED_FREE_CHLORINE, DATA_ACTIVE_CHLORINE_HOCL}
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    mac_address = entry.data[CONF_MAC_ADDRESS]
    model_name = entry.data.get("model") or get_flipr_model(entry.title)

    async_add_entities(
        [
            FliprSensor(
                coordinator,
                mac_address,
                "temperature",
                SensorDeviceClass.TEMPERATURE,
                UnitOfTemperature.CELSIUS,
                2,
                model_name=model_name,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            FliprSensor(
                coordinator,
                mac_address,
                "ph",
                SensorDeviceClass.PH,
                None,
                2,
                model_name=model_name,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            FliprSensor(
                coordinator,
                mac_address,
                "orp",
                None,
                "mV",
                model_name=model_name,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            FliprSensor(
                coordinator,
                mac_address,
                DATA_ESTIMATED_FREE_CHLORINE,
                None,
                "ppm",
                2,
                model_name=model_name,
                state_class=SensorStateClass.MEASUREMENT,
                icon="mdi:water-percent",
            ),
            FliprSensor(
                coordinator,
                mac_address,
                DATA_ACTIVE_CHLORINE_HOCL,
                None,
                "mg/L",
                4,
                model_name=model_name,
                state_class=SensorStateClass.MEASUREMENT,
                icon="mdi:molecule",
            ),
            FliprSensor(
                coordinator,
                mac_address,
                "target_equilibrium_ph",
                SensorDeviceClass.PH,
                None,
                2,
                category=EntityCategory.DIAGNOSTIC,
                model_name=model_name,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            FliprSensor(
                coordinator,
                mac_address,
                "lsi",
                None,
                None,
                2,
                category=EntityCategory.DIAGNOSTIC,
                model_name=model_name,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            FliprSensor(
                coordinator,
                mac_address,
                "lsi_status",
                SensorDeviceClass.ENUM,
                None,
                category=EntityCategory.DIAGNOSTIC,
                model_name=model_name,
                options=["corrosive", "balanced", "scaling", "unknown"],
            ),
            FliprSensor(
                coordinator,
                mac_address,
                "ph_raw",
                None,
                "mV",
                category=EntityCategory.DIAGNOSTIC,
                icon="mdi:lightning-bolt",
                model_name=model_name,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            FliprSensor(
                coordinator,
                mac_address,
                "factory_ph",
                SensorDeviceClass.PH,
                None,
                2,
                category=EntityCategory.DIAGNOSTIC,
                icon="mdi:factory",
                model_name=model_name,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            FliprSensor(
                coordinator,
                mac_address,
                "battery_level",
                SensorDeviceClass.BATTERY,
                "%",
                category=EntityCategory.DIAGNOSTIC,
                model_name=model_name,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            FliprSensor(
                coordinator,
                mac_address,
                "battery",
                None,
                "mV",
                category=EntityCategory.DIAGNOSTIC,
                icon="mdi:battery-bluetooth",
                model_name=model_name,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            FliprSensor(
                coordinator,
                mac_address,
                "last_received",
                SensorDeviceClass.TIMESTAMP,
                None,
                category=EntityCategory.DIAGNOSTIC,
                icon="mdi:clock-check",
                model_name=model_name,
            ),
            FliprSensor(
                coordinator,
                mac_address,
                "raw_frame",
                None,
                None,
                category=EntityCategory.DIAGNOSTIC,
                icon="mdi:bluetooth-transfer",
                model_name=model_name,
            ),
            FliprSyncModeSensor(coordinator, mac_address, model_name),
            FliprBluetoothStatusSensor(coordinator, mac_address, model_name),
            FliprRealTimeRSSISensor(coordinator, mac_address, model_name),
            FliprNextAnalysisSensor(coordinator, mac_address, model_name),
        ]
    )


class FliprSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        mac: str,
        key: str,
        device_class: SensorDeviceClass | None = None,
        unit: str | None = None,
        precision: int | None = None,
        category: EntityCategory | None = None,
        icon: str | None = None,
        model_name: str = "Flipr",
        options: list[str] | None = None,
        state_class: SensorStateClass | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._key = key
        self._attr_translation_key = key
        self._attr_unique_id = f"{mac}_{key}"
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_suggested_display_precision = precision
        self._attr_entity_category = category
        self._attr_state_class = state_class
        self._attr_icon = icon
        if options:
            self._attr_options = options
        self._attr_device_info = flipr_device_info(mac, model_name)

        # FIX: only sensors that depend on the chlorine model need this attribute.
        # Other sensors initialise it to None to make the distinction explicit.
        self._chlorine_model: str | None = (
            "chlorine" if key in _CHLORINE_MODEL_DEPENDENT_KEYS else None
        )

    def _refresh_chlorine_model(self) -> None:
        """Refresh the cached chlorine model from config entry options."""
        entry = self.hass.config_entries.async_get_entry(self.coordinator.entry_id)
        if entry:
            self._chlorine_model = entry.options.get(
                CONF_CHLORINE_MODEL, entry.data.get(CONF_CHLORINE_MODEL, "chlorine")
            )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        # FIX: subscribe to the chlorine model dispatcher ONLY for sensors whose
        # availability depends on it. Subscribing all ~14 sensors was wasting memory
        # and causing unnecessary dispatcher callbacks on every options update.
        if self._key in _CHLORINE_MODEL_DEPENDENT_KEYS:
            self._refresh_chlorine_model()
            self.async_on_remove(
                async_dispatcher_connect(
                    self.hass,
                    f"{DOMAIN}_{self._mac}_options_updated",
                    self._handle_options_updated,
                )
            )

    @callback
    def _handle_options_updated(self) -> None:
        self._refresh_chlorine_model()
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        is_avail = super().available
        if self._key in _CHLORINE_MODEL_DEPENDENT_KEYS:
            return is_avail and self._chlorine_model != "bromine"
        return is_avail

    @property
    def native_value(self) -> Any | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self._key)


class FliprSyncModeSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_translation_key = "sync_mode_state"
    _attr_options = ["0", "1", "2", "3"]

    def __init__(self, coordinator, mac: str, model_name: str) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._attr_unique_id = f"{mac}_sync_mode"
        self._attr_device_info = flipr_device_info(mac, model_name)

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        val = self.coordinator.data.get("sync_mode")
        return str(val) if val is not None else None

    @property
    def icon(self) -> str:
        icons = {
            "0": "mdi:power-sleep",
            "1": "mdi:waves",
            "2": "mdi:leaf",
            "3": "mdi:rocket-launch",
        }
        return icons.get(self.native_value or "", "mdi:sync-alert")


class FliprBluetoothStatusSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_translation_key = "bluetooth_status"
    _attr_options = [
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
    ]

    def __init__(self, coordinator, mac: str, model_name: str) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._attr_unique_id = f"{mac}_bluetooth_status"
        self._attr_device_info = flipr_device_info(mac, model_name)

    @property
    def native_value(self) -> str:
        if not self.coordinator.data:
            return BT_STATUS_WAITING
        return self.coordinator.data.get("bluetooth_status", BT_STATUS_WAITING)

    @property
    def icon(self) -> str:
        icons = {
            BT_STATUS_WAITING: "mdi:bluetooth-off",
            BT_STATUS_CONNECTING: "mdi:bluetooth-connect",
            BT_STATUS_WAKING_UP: "mdi:bluetooth-audio",
            BT_STATUS_REQUESTING: "mdi:bluetooth-transfer",
            BT_STATUS_READING: "mdi:bluetooth-transfer",
            BT_STATUS_WRITING_SYNC: "mdi:bluetooth-settings",
            BT_STATUS_SUCCESS: "mdi:bluetooth",
            BT_STATUS_SYNC_APPLIED: "mdi:bluetooth-connect",
            BT_STATUS_ERROR: "mdi:bluetooth-off",
            BT_STATUS_ERROR_RETRY: "mdi:timer-sand",
            BT_STATUS_WRITE_FAILED: "mdi:alert-circle",
            BT_STATUS_PAUSED: "mdi:pause-circle",
            BT_STATUS_OUT_OF_RANGE: "mdi:bluetooth-off",
        }
        return icons.get(self.native_value, "mdi:bluetooth-alert")


class FliprRealTimeRSSISensor(RestoreSensor):
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_native_unit_of_measurement = "dBm"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "rssi"
    _attr_should_poll = False

    def __init__(self, coordinator, mac: str, model_name: str) -> None:
        super().__init__()
        self._coordinator = coordinator
        self._mac = mac
        self._attr_unique_id = f"{mac}_rssi"
        self._attr_device_info = flipr_device_info(mac, model_name)
        self._attr_native_value = None

    @property
    def available(self) -> bool:
        if (
            self._coordinator.data
            and self._coordinator.data.get("bluetooth_status") == BT_STATUS_OUT_OF_RANGE
        ):
            return False
        return self._coordinator.ble_available and self._attr_native_value is not None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        last_info = async_last_service_info(self.hass, self._mac, connectable=False)
        if last_info and hasattr(last_info, "rssi"):
            self._attr_native_value = last_info.rssi
        else:
            last_sensor_data = await self.async_get_last_sensor_data()
            if last_sensor_data and last_sensor_data.native_value is not None:
                self._attr_native_value = last_sensor_data.native_value

        self.async_write_ha_state()

        @callback
        def _async_on_bluetooth_change(
            info: BluetoothServiceInfoBleak, change: BluetoothChange
        ) -> None:
            self._attr_native_value = info.rssi
            self.async_write_ha_state()

        self.async_on_remove(
            async_register_callback(
                self.hass,
                _async_on_bluetooth_change,
                BluetoothCallbackMatcher(address=self._mac),
                BluetoothScanningMode.PASSIVE,
            )
        )

        # FIX: removed the coordinator listener that was calling async_write_ha_state()
        # on every coordinator poll cycle. The RSSI value is driven exclusively by BLE
        # advertisement callbacks, not by coordinator data, so that listener was causing
        # spurious state writes with no actual state change every N minutes.


class FliprNextAnalysisSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "next_analysis"
    _attr_icon = "mdi:clock-end"

    def __init__(self, coordinator, mac: str, model_name: str) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._attr_unique_id = f"{mac}_next_analysis"
        self._attr_device_info = flipr_device_info(mac, model_name)

    @property
    def native_value(self) -> dt_datetime | None:
        if not self.coordinator.data:
            return None
        if not self.coordinator.data.get("active_measures", True):
            return None
        if self.coordinator.data.get("action_running", False):
            return None
        last = self.coordinator.data.get("last_received")
        interval = self.coordinator.update_interval
        if not last or not interval:
            return None
        if last.tzinfo is None:
            last = dt_util.as_utc(last)
        next_dt = last + interval
        if next_dt < dt_util.utcnow():
            return None
        return next_dt
