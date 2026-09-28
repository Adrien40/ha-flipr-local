# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

from __future__ import annotations

import logging
from datetime import datetime as dt_datetime
from typing import Any

import homeassistant.util.dt as dt_util
from homeassistant.components.bluetooth import (
    BluetoothCallbackMatcher,
    BluetoothChange,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
    async_last_service_info,
    async_register_callback,
)
from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
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
    CONF_MAC_ADDRESS,
    flipr_device_info,
)
from .coordinator import FliprDataCoordinator
from .model import get_flipr_model

_LOGGER = logging.getLogger(__name__)


# Coordinator centralizes updates; entities are read-only.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
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
                model_name=model_name,
                state_class=SensorStateClass.MEASUREMENT,
                enabled_default=False,
            ),
            FliprSensor(
                coordinator,
                mac_address,
                "orp_raw",
                None,
                "mV",
                1,
                category=EntityCategory.DIAGNOSTIC,
                model_name=model_name,
                state_class=SensorStateClass.MEASUREMENT,
                enabled_default=False,
            ),
            FliprSensor(
                coordinator,
                mac_address,
                "factory_ph",
                SensorDeviceClass.PH,
                None,
                2,
                category=EntityCategory.DIAGNOSTIC,
                model_name=model_name,
                state_class=SensorStateClass.MEASUREMENT,
                enabled_default=False,
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
                model_name=model_name,
                state_class=SensorStateClass.MEASUREMENT,
                enabled_default=False,
            ),
            FliprSensor(
                coordinator,
                mac_address,
                "last_received",
                SensorDeviceClass.TIMESTAMP,
                None,
                category=EntityCategory.DIAGNOSTIC,
                model_name=model_name,
            ),
            FliprSensor(
                coordinator,
                mac_address,
                "raw_frame",
                None,
                None,
                category=EntityCategory.DIAGNOSTIC,
                model_name=model_name,
                enabled_default=False,
            ),
            FliprSyncModeSensor(coordinator, mac_address, model_name),
            FliprBluetoothStatusSensor(coordinator, mac_address, model_name),
            FliprRealTimeRSSISensor(coordinator, mac_address, model_name),
            FliprNextAnalysisSensor(coordinator, mac_address, model_name),
        ]
    )


class FliprSensor(CoordinatorEntity[FliprDataCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FliprDataCoordinator,
        mac: str,
        key: str,
        device_class: SensorDeviceClass | None = None,
        unit: str | None = None,
        precision: int | None = None,
        category: EntityCategory | None = None,
        model_name: str = "Flipr",
        options: list[str] | None = None,
        state_class: SensorStateClass | None = None,
        enabled_default: bool = True,
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
        self._attr_entity_registry_enabled_default = enabled_default
        if options:
            self._attr_options = options
        self._attr_device_info = flipr_device_info(mac, model_name)

    @property
    def native_value(self) -> Any | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self._key)


class FliprSyncModeSensor(CoordinatorEntity[FliprDataCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_translation_key = "sync_mode_state"
    _attr_options = ["0", "1", "2", "3"]

    def __init__(
        self, coordinator: FliprDataCoordinator, mac: str, model_name: str
    ) -> None:
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


class FliprBluetoothStatusSensor(CoordinatorEntity[FliprDataCoordinator], SensorEntity):
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

    def __init__(
        self, coordinator: FliprDataCoordinator, mac: str, model_name: str
    ) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._attr_unique_id = f"{mac}_bluetooth_status"
        self._attr_device_info = flipr_device_info(mac, model_name)

    @property
    def native_value(self) -> str:
        if not self.coordinator.data:
            return BT_STATUS_WAITING
        return str(self.coordinator.data.get("bluetooth_status", BT_STATUS_WAITING))


class FliprRealTimeRSSISensor(CoordinatorEntity[FliprDataCoordinator], RestoreSensor):
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_native_unit_of_measurement = "dBm"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "rssi"
    _attr_should_poll = False

    def __init__(
        self, coordinator: FliprDataCoordinator, mac: str, model_name: str
    ) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._attr_unique_id = f"{mac}_rssi"
        self._attr_device_info = flipr_device_info(mac, model_name)
        self._attr_native_value = None

    @property
    def available(self) -> bool:
        if (
            self.coordinator.data
            and self.coordinator.data.get("bluetooth_status") == BT_STATUS_OUT_OF_RANGE
        ):
            return False
        return self.coordinator.ble_available and self._attr_native_value is not None

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


class FliprNextAnalysisSensor(CoordinatorEntity[FliprDataCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "next_analysis"

    def __init__(
        self, coordinator: FliprDataCoordinator, mac: str, model_name: str
    ) -> None:
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
        next_slot = getattr(self.coordinator, "next_slot", None)
        if next_slot is None:
            return None
        if next_slot.tzinfo is None:
            next_slot = dt_util.as_utc(next_slot)
        return next_slot
