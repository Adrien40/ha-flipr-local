# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    BT_STATUS_OUT_OF_RANGE,
    BT_STATUS_PAUSED,
    BT_STATUS_WAITING,
    CONF_MAC_ADDRESS,
    flipr_device_info,
)
from .coordinator import FliprDataCoordinator
from .model import get_flipr_model

_LOGGER = logging.getLogger(__name__)


# Single Bluetooth connection to the device: commands must be serialized.
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    mac = entry.data[CONF_MAC_ADDRESS]
    model_name = entry.data.get("model") or get_flipr_model(entry.title)

    async_add_entities([FliprActiveMeasuresSwitch(coordinator, mac, model_name)])


class FliprActiveMeasuresSwitch(CoordinatorEntity[FliprDataCoordinator], SwitchEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "active_measures"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, coordinator: FliprDataCoordinator, mac: str, model_name: str
    ) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._attr_unique_id = f"{mac}_active_measures"
        self._attr_device_info = flipr_device_info(mac, model_name)

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return True
        return bool(self.coordinator.data.get("active_measures", True))

    async def async_turn_on(self, **kwargs: Any) -> None:
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

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.coordinator.update_local_state(
            {
                "active_measures": False,
                "bluetooth_status": BT_STATUS_PAUSED,
            }
        )
