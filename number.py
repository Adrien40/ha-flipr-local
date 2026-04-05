# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

"""Configuration et réglages pour Flipr"""
import logging
from datetime import timedelta
from homeassistant.components.number import RestoreNumber
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN, CONF_MAC_ADDRESS, CONF_CYA, CONF_USE_GATEWAY, CONF_SCAN_INTERVAL
from .chemistry import compute_isl, compute_active_chlorine

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    mac = entry.data[CONF_MAC_ADDRESS]
    entry_id = entry.entry_id
    use_gateway = entry.options.get(CONF_USE_GATEWAY, entry.data.get(CONF_USE_GATEWAY, False))
    
    hass.data.setdefault(DOMAIN, {})
    if mac not in hass.data[DOMAIN]:
        hass.data[DOMAIN][mac] = {}

    async_add_entities([
        FliprIntervalNumber(coordinator, mac, use_gateway),
        FliprWaterConfigNumber(coordinator, mac, "TAC : Alcalinité", "tac", 0, 500, 1, 100, "mdi:water-percent", entry_id),
        FliprWaterConfigNumber(coordinator, mac, "TDS : Solides Dissous", "tds", 0, 5000, 10, 500, "mdi:blur", entry_id),
        FliprWaterConfigNumber(coordinator, mac, "TH : Dureté Calcique", "th", 0, 800, 1, 200, "mdi:water-outline", entry_id),
        FliprWaterConfigNumber(coordinator, mac, "CyA : Stabilisant", CONF_CYA, 0, 150, 1, 40, "mdi:shield-sun", entry_id),
    ])

class FliprIntervalNumber(RestoreNumber):
    _attr_has_entity_name = True
    def __init__(self, coordinator, mac, use_gateway):
        self.coordinator = coordinator
        self._mac = mac
        self._use_gateway = use_gateway
        self._attr_name = "Intervalle de lecture passive"
        self._attr_unique_id = f"{mac}_{CONF_SCAN_INTERVAL}"
        self._attr_native_min_value = 15
        self._attr_native_max_value = 1440
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = "min"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:timer-outline"
        self._attr_mode = "box"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, mac)}, name=f"Flipr {mac}")

    @property
    def available(self) -> bool:
        """Grise le curseur si le mode Passerelle est activé."""
        return not self._use_gateway

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        val = int(float(last.native_value)) if last and last.native_value is not None else 75
        self._attr_native_value = val
        if not self._use_gateway:
            self.coordinator.update_interval = timedelta(minutes=val)

    async def async_set_native_value(self, value):
        val = int(float(value))
        self._attr_native_value = val
        if not self._use_gateway:
            self.coordinator.update_interval = timedelta(minutes=val)
        self.async_write_ha_state()

class FliprWaterConfigNumber(RestoreNumber):
    _attr_has_entity_name = True
    def __init__(self, coordinator, mac, name, key, min_val, max_val, step, default_val, icon, entry_id):
        self.coordinator = coordinator
        self._mac = mac
        self._key = key
        self._entry_id = entry_id
        self._attr_name = name
        self._attr_unique_id = f"{mac}_{key}"
        self._attr_native_min_value = min_val
        self._attr_native_max_value = max_val
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = "mg/L"
        self._attr_icon = icon
        self._default_val = default_val
        self._attr_mode = "box"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, mac)}, name=f"Flipr {mac}")

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        val = int(float(last.native_value)) if last and last.native_value is not None else self._default_val
        self._attr_native_value = val
        self.coordinator.hass.data[DOMAIN][self._mac][self._key] = val

    async def async_set_native_value(self, value):
        int_val = int(float(value))
        self._attr_native_value = int_val
        self.coordinator.hass.data[DOMAIN][self._mac][self._key] = int_val
        self.async_write_ha_state()
        
        if self.coordinator.data:
            new_data = dict(self.coordinator.data)
            mac_data = self.coordinator.hass.data[DOMAIN].get(self._mac, {})
            
            tac = mac_data.get("tac", 0)
            th = mac_data.get("th", 0)
            tds = mac_data.get("tds", 0)
            cya = mac_data.get(CONF_CYA, 40)
            
            temp = new_data.get("temperature")
            ph = new_data.get("ph")
            orp = new_data.get("orp")
            
            if temp is not None and ph is not None:
                new_data["isl"] = compute_isl(temp, ph, tac, th, tds)
                entry = self.coordinator.hass.config_entries.async_get_entry(self._entry_id)
                chlore_model = entry.options.get("chlore_model", "stabilized")
                new_data["chlore_actif_hocl"] = compute_active_chlorine(orp, ph, temp, cya, chlore_model)
                self.coordinator.async_set_updated_data(new_data)