# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import (
    DOMAIN,
    CONF_MAC_ADDRESS,
    CONF_CHLORINE_MODEL,
    get_flipr_model,
    flipr_device_info,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    mac = entry.data[CONF_MAC_ADDRESS]
    model_name = entry.data.get("model") or get_flipr_model(entry.title)

    async_add_entities([FliprModelSelect(coordinator, entry.entry_id, mac, model_name)])


class FliprModelSelect(CoordinatorEntity, SelectEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "chlorine_model"
    _attr_options = ["chlorine", "bromine"]

    def __init__(self, coordinator, entry_id: str, mac: str, model_name: str) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._mac = mac
        self._attr_unique_id = f"{mac}_chlorine_model"
        self._attr_device_info = flipr_device_info(mac, model_name)
        self._current_option: str = "chlorine"

    def _refresh_current_option(self) -> None:
        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        if entry:
            self._current_option = entry.options.get(
                CONF_CHLORINE_MODEL, entry.data.get(CONF_CHLORINE_MODEL, "chlorine")
            )

    @property
    def available(self) -> bool:
        return True

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._refresh_current_option()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self._mac}_options_updated",
                self._handle_options_updated,
            )
        )

    @callback
    def _handle_options_updated(self) -> None:
        self._refresh_current_option()
        self.async_write_ha_state()

    @property
    def current_option(self) -> str:
        return self._current_option

    async def async_select_option(self, option: str) -> None:
        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        if not entry:
            return
        new_options = dict(entry.options)
        new_options[CONF_CHLORINE_MODEL] = option
        self.hass.config_entries.async_update_entry(entry, options=new_options)
