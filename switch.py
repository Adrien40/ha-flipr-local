# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

"""Interrupteurs pour Flipr"""
import logging
from datetime import timedelta
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, CONF_MAC_ADDRESS, get_flipr_model

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    mac = entry.data[CONF_MAC_ADDRESS]
    model_name = entry.data.get("model") or get_flipr_model(entry.title)

    async_add_entities([
        FliprActivePollingSwitch(coordinator, mac, model_name)
    ])

class FliprActivePollingSwitch(CoordinatorEntity, SwitchEntity, RestoreEntity):
    """Interrupteur pour activer ou désactiver l'interrogation Bluetooth active."""
    _attr_has_entity_name = True

    def __init__(self, coordinator, mac, model_name):
        super().__init__(coordinator)
        self._mac = mac
        self._attr_name = "Interrogation Active"
        self._attr_unique_id = f"{mac}_active_polling"
        self._attr_icon = "mdi:bluetooth-connect"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)},
            name=model_name,
            manufacturer="Flipr",
            model=model_name
        )
        self._is_on = True

    @property
    def is_on(self):
        return self._is_on

    async def async_added_to_hass(self):
        """Restaure l'état précédent au redémarrage."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state:
            self._is_on = last_state.state == "on"
        else:
            self._is_on = True  # Par défaut, on active l'interrogation
            
        self._update_interval()

    async def async_turn_on(self, **kwargs):
        """Active l'interrogation Bluetooth."""
        self._is_on = True
        self._update_interval()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Passe en écoute passive (désactive l'interrogation)."""
        self._is_on = False
        self._update_interval()
        self.async_write_ha_state()

    def _update_interval(self):
        """Met à jour l'intervalle du coordinateur en lisant la valeur configurée."""
        # On récupère l'intervalle sauvegardé par le curseur (défaut: 75 min)
        interval_min = self.coordinator.hass.data[DOMAIN].get(self._mac, {}).get("scan_interval", 75)
        
        if self._is_on:
            self.coordinator.update_interval = timedelta(minutes=interval_min)
            _LOGGER.debug("Interrogation Active ON : %s min", interval_min)
        else:
            self.coordinator.update_interval = None
            _LOGGER.debug("Interrogation Active OFF : Mode écoute passive")