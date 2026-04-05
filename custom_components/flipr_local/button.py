# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

import logging, asyncio
from bleak import BleakClient
from bleak_retry_connector import establish_connection
from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, CONF_MAC_ADDRESS, get_flipr_model

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    mac = entry.data[CONF_MAC_ADDRESS]
    
    model_name = entry.data.get("model") or get_flipr_model(entry.title)
    
    async_add_entities([
        FliprActionTaskButton(coordinator, mac, "Nouvelle Analyse (~60s)", "nouvelle_analyse", "0000940d-0000-1000-8000-00805f9b34fb", "mdi:test-tube", model_name),
        FliprRefreshButton(coordinator, mac, "Récupérer dernière mesure", "recup_derniere", "mdi:cloud-download", model_name)
    ])

class FliprActionTaskButton(CoordinatorEntity, ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, mac, name, key, action_uuid, icon, model_name):
        super().__init__(coordinator)
        self._mac = mac
        self._attr_name = name
        self._attr_unique_id = f"{mac}_{key}"
        self._attr_icon = icon
        self._action_uuid = action_uuid
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, mac)}, name=model_name, manufacturer="Flipr", model=model_name)

    @property
    def available(self) -> bool:
        return True

    async def async_press(self) -> None:
        _LOGGER.info("Démarrage du cycle d'analyse pour %s", self._mac)
        self.hass.async_create_task(self._run_analysis_cycle())

    async def _run_analysis_cycle(self):
        device = async_ble_device_from_address(self.hass, self._mac, connectable=True)
        if not device:
            _LOGGER.error("Impossible de lancer l'analyse : Flipr hors de portée.")
            return

        try:
            client = await establish_connection(BleakClient, device, self._mac)
            try:
                await client.write_gatt_char(self._action_uuid, bytearray([0x01]), response=True)
                _LOGGER.info("Pompe activée. Attente de 45 secondes pour la chimie...")
            finally:
                await client.disconnect()
        except Exception as err:
            _LOGGER.error("Échec de l'activation de la pompe : %s", err)
            return

        await asyncio.sleep(45)

        _LOGGER.info("Chimie terminée. Demande de rafraîchissement au Coordinateur.")
        await self.coordinator.async_request_refresh()

class FliprRefreshButton(CoordinatorEntity, ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, mac, name, key, icon, model_name):
        super().__init__(coordinator)
        self._mac = mac
        self._attr_name = name
        self._attr_unique_id = f"{mac}_{key}"
        self._attr_icon = icon
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, mac)}, name=model_name, manufacturer="Flipr", model=model_name)

    @property
    def available(self) -> bool:
        return True

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()