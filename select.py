# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, CONF_MAC_ADDRESS
from .chemistry import compute_active_chlorine

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FliprModelSelect(coordinator, entry)], True)

class FliprModelSelect(CoordinatorEntity, SelectEntity):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry
        self._mac = entry.data[CONF_MAC_ADDRESS]
        
        self._attr_unique_id = f"{entry.entry_id}_chlore_model"
        self._attr_name = "Modèle de calcul du désinfectant"
        self._attr_icon = "mdi:flask-round-bottom"
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._mac)},
            "name": f"Flipr {self._mac}",
            "manufacturer": "Flipr"
        }
        
        self._attr_options = [
            "Galets / Chlore Stabilisé", 
            "Sticks / Sel Chlore Non Stabilisé",
            "Brome",
            "Calibration Personnalisée"
        ]
        
        self._mapping = {
            "Galets / Chlore Stabilisé": "stabilized",
            "Sticks / Sel Chlore Non Stabilisé": "nernst",
            "Brome": "bromine",
            "Calibration Personnalisée": "custom"
        }
        self._reverse_mapping = {v: k for k, v in self._mapping.items()}

    @property
    def current_option(self):
        model = self._entry.options.get("chlore_model", "stabilized")
        return self._reverse_mapping.get(model)

    async def async_select_option(self, option: str):
        new_model = self._mapping.get(option)
        new_options = dict(self._entry.options)
        new_options["chlore_model"] = new_model
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        
        if self.coordinator.data:
            new_data = dict(self.coordinator.data)
            mac_data = self.coordinator.hass.data[DOMAIN].get(self._mac, {})
            cya = mac_data.get("cya", 40)
            
            new_data["chlore_actif"] = compute_active_chlorine(
                new_data["orp"], new_data["ph"], new_data["temperature"], cya, new_model
            )
            self.coordinator.async_set_updated_data(new_data)