# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import EntityCategory
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import (
    DOMAIN,
    CONF_MAC_ADDRESS,
    get_flipr_model,
    flipr_device_info,
    BT_STATUS_OUT_OF_RANGE,
    BT_STATUS_PAUSED,
    BT_STATUS_WAITING,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    mac = entry.data[CONF_MAC_ADDRESS]
    model_name = entry.data.get("model") or get_flipr_model(entry.title)

    async_add_entities([FliprActiveMeasuresSwitch(coordinator, mac, model_name)])


class FliprActiveMeasuresSwitch(CoordinatorEntity, SwitchEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "active_measures"
    _attr_icon = "mdi:bluetooth-connect"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, mac: str, model_name: str) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._attr_unique_id = f"{mac}_active_measures"
        self._attr_device_info = flipr_device_info(mac, model_name)

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return True
        return self.coordinator.data.get("active_measures", True)

    async def async_turn_on(self, **kwargs) -> None:
        if not self.coordinator.ble_available:
            _LOGGER.warning(
                "Cannot resume analyses for %s: real-time Bluetooth signal unavailable",
                self.coordinator.safe_mac,
            )
            self.coordinator.update_local_state(
                {
                    "active_measures": True,
                    "bluetooth_status": BT_STATUS_OUT_OF_RANGE,
                }
            )
            return

        self.coordinator.update_local_state(
            {
                "active_measures": True,
                "bluetooth_status": BT_STATUS_WAITING,
            }
        )
        if self.coordinator._is_shutdown:
            return
        entry = self.hass.config_entries.async_get_entry(self.coordinator.entry_id)
        if not entry:
            _LOGGER.warning(
                "Cannot resume refresh for %s: config entry no longer available",
                self.coordinator.safe_mac,
            )
            return
        entry.async_create_background_task(
            self.hass,
            self.coordinator.async_request_refresh(),
            "flipr_resume_refresh",
        )

    async def async_turn_off(self, **kwargs) -> None:
        self.coordinator.update_local_state(
            {
                "active_measures": False,
                "bluetooth_status": BT_STATUS_PAUSED,
            }
        )
