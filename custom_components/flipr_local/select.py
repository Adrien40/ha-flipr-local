# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, CONF_MAC_ADDRESS, CONF_CHLORE_MODEL, CONF_CYA, get_flipr_model
from .chemistry import compute_active_chlorine

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
        # 1. On recalcule la donnée tout de suite en local pour éviter le vide
        if self.coordinator.data:
            new_data = dict(self.coordinator.data)
            mac_data = self.coordinator.hass.data[DOMAIN].get(self._mac, {})
            cya = mac_data.get(CONF_CYA, 40)
            temp = new_data.get("temperature")
            ph = new_data.get("ph")
            orp = new_data.get("orp")
            
            if temp is not None and ph is not None:
                new_data["chlore_actif_hocl"] = compute_active_chlorine(orp, ph, temp, cya, option)
                self.coordinator.async_set_updated_data(new_data)
                # On met à jour la mémoire pour le redémarrage
                self.coordinator.hass.data[DOMAIN][self._mac]["last_data"] = new_data

        # 2. Sauvegarde officielle (provoque un redémarrage invisible en fond)
        new_options = dict(self.entry.options)
        new_options[CONF_CHLORE_MODEL] = option
        self.coordinator.hass.config_entries.async_update_entry(self.entry, options=new_options)