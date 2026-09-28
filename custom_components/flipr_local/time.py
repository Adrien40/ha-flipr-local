# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

import logging
from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_MAC_ADDRESS,
    CONF_REFERENCE_TIME,
    DOMAIN,
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
    entry_id = entry.entry_id
    model_name = entry.data.get("model") or get_flipr_model(entry.title)

    async_add_entities([FliprReferenceTime(coordinator, mac, model_name, entry_id)])


class FliprReferenceTime(CoordinatorEntity[FliprDataCoordinator], TimeEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "reference_time"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: FliprDataCoordinator,
        mac: str,
        model_name: str,
        entry_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._entry_id = entry_id
        self._attr_unique_id = f"{mac}_{CONF_REFERENCE_TIME}"
        self._attr_device_info = flipr_device_info(mac, model_name)
        # Last value seen in the options: only react to an actual change
        # in the options (see _handle_options_updated).
        self._last_option_val: str | None = None

    def _read_option_value(self) -> str | None:
        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        if entry and CONF_REFERENCE_TIME in entry.options:
            return str(entry.options[CONF_REFERENCE_TIME])
        return None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        time_str = self.coordinator.data.get(CONF_REFERENCE_TIME)
        if time_str is None:
            time_str = self._read_option_value()
        if time_str is None:
            entry = self.hass.config_entries.async_get_entry(self._entry_id)
            if entry and CONF_REFERENCE_TIME in entry.data:
                time_str = str(entry.data[CONF_REFERENCE_TIME])
        if time_str is None:
            time_str = "08:00"

        self._last_option_val = self._read_option_value()
        self.coordinator.update_volatile_state({CONF_REFERENCE_TIME: time_str})

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self._mac}_options_updated",
                self._handle_options_updated,
            )
        )

        self.async_write_ha_state()

    @callback
    def _handle_options_updated(self) -> None:
        # Only apply the option if it changed: otherwise a change made
        # through this entity would be overwritten by the old options value as
        # soon as ANOTHER setting is changed (e.g. the chlorine/bromine selector).
        new_val = self._read_option_value()
        if new_val is not None and new_val != self._last_option_val:
            self._last_option_val = new_val
            current_val = self.coordinator.data.get(CONF_REFERENCE_TIME)
            if new_val != current_val:
                self.coordinator.update_local_state({CONF_REFERENCE_TIME: new_val})
        self.async_write_ha_state()

    @property
    def native_value(self) -> time | None:
        time_str = self.coordinator.data.get(CONF_REFERENCE_TIME)
        if not time_str:
            entry = self.hass.config_entries.async_get_entry(self._entry_id)
            if entry:
                time_str = entry.options.get(
                    CONF_REFERENCE_TIME, entry.data.get(CONF_REFERENCE_TIME, "08:00")
                )
        if time_str:
            try:
                parts = time_str.split(":")
                return time(hour=int(parts[0]), minute=int(parts[1]))
            # PEP 758 (Python 3.14): parentheses are optional when there is no `as` clause. Intentional.
            except ValueError, IndexError:
                pass
        return time(hour=8, minute=0)

    async def async_set_value(self, value: time) -> None:
        time_str = value.strftime("%H:%M")
        self.coordinator.update_local_state({CONF_REFERENCE_TIME: time_str})
        self.async_write_ha_state()
