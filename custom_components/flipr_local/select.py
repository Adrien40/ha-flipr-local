# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, CONF_MAC_ADDRESS, CONF_CHLORE_MODEL, get_flipr_model

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    mac = entry.data[CONF_MAC_ADDRESS]
    model_name = entry.data.get("model") or get_flipr_model(entry.title)

    async_add_entities([FliprModelSelect(coordinator, entry, mac, model_name)])

class FliprModelSelect(CoordinatorEntity, SelectEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "chlore_model"
    _attr_options = ["stabilized", "nernst", "bromine", "custom"]

    def __init__(self, coordinator, entry, mac, model_name):
        super().__init__(coordinator)
        self.entry = entry
        self._mac = mac
        self._attr_unique_id = f"{mac}_chlore_model"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)}, 
            name=model_name, 
            manufacturer="Flipr", 
            model=model_name
        )

    @property
    def current_option(self):
        return self.entry.options.get(CONF_CHLORE_MODEL, self.entry.data.get(CONF_CHLORE_MODEL, "stabilized"))

    async def async_select_option(self, option: str) -> None:
        new_options = dict(self.entry.options)
        new_options[CONF_CHLORE_MODEL] = option
        self.coordinator.hass.config_entries.async_update_entry(self.entry, options=new_options)
        await self.coordinator.async_request_refresh()