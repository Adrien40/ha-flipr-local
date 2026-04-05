# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

"""Alertes pour Flipr"""
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, CONF_MAC_ADDRESS, CONF_PH_MIN, CONF_PH_MAX, CONF_ORP_MIN, CONF_TEMP_MIN, CONF_TEMP_MAX

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    mac = entry.data[CONF_MAC_ADDRESS]
    async_add_entities([
        FliprStatus(coordinator, entry, mac, "pH Status", "ph"),
        FliprStatus(coordinator, entry, mac, "Chlore Status", "orp"),
        FliprStatus(coordinator, entry, mac, "Température Status", "temperature")
    ])

class FliprStatus(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    
    def __init__(self, coordinator, entry, mac, name, key):
        super().__init__(coordinator)
        self.entry = entry
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{mac}_{key}_status"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, mac)}, name=f"Flipr {mac}")

    @property
    def is_on(self):
        """Évalue si la valeur est hors des clous (True = Problème, False = OK)."""
        if not self.coordinator.data:
            return None
            
        val = self.coordinator.data.get(self._key)
        if val is None: 
            return None
            
        # Évaluation des seuils (Renvoie automatiquement True ou False)
        if self._key == "ph": 
            return val < self.entry.options.get(CONF_PH_MIN, 6.90) or val > self.entry.options.get(CONF_PH_MAX, 7.50)
            
        if self._key == "orp": 
            return val < self.entry.options.get(CONF_ORP_MIN, 650)
            
        if self._key == "temperature": 
            return val < self.entry.options.get(CONF_TEMP_MIN, 6.0) or val > self.entry.options.get(CONF_TEMP_MAX, 32.0)
            
        # Sécurité finale si la clé n'est pas reconnue
        return False