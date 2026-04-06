# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

import logging, asyncio
from bleak import BleakClient
from bleak_retry_connector import establish_connection
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.components.bluetooth import async_ble_device_from_address
from .const import DOMAIN, CONF_MAC_ADDRESS, FLIPR_COMMAND_UUID, get_flipr_model

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    mac = entry.data[CONF_MAC_ADDRESS]
    model_name = entry.data.get("model") or get_flipr_model(entry.title)

    async_add_entities([
        FliprForceAnalysisButton(coordinator, mac, model_name),
        FliprFetchButton(coordinator, mac, model_name)
    ])

class FliprForceAnalysisButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, mac, model_name):
        self.coordinator = coordinator
        self._mac = mac
        self._attr_name = "Nouvelle Analyse (~60s)"
        self._attr_unique_id = f"{mac}_nouvelle_analyse"
        self._attr_icon = "mdi:water-sync"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, mac)}, name=model_name, manufacturer="Flipr", model=model_name)

    async def async_press(self) -> None:
        """L'interface affichera un chargement pendant toute l'exécution de cette fonction."""
        device = async_ble_device_from_address(self.hass, self._mac, connectable=True)
        if not device:
            device = async_ble_device_from_address(self.hass, self._mac, connectable=False)
        
        if not device:
            _LOGGER.error("Flipr %s introuvable. Impossible de forcer la pompe.", self._mac)
            return

        try:
            client = await establish_connection(BleakClient, device, self._mac, max_attempts=3)
            try:
                await client.write_gatt_char(FLIPR_COMMAND_UUID, bytearray([0x01]), response=True)
                
                # NOUVEAU : On garde le client connecté pendant 55s pour bloquer la passerelle
                await asyncio.sleep(55)
            finally:
                await client.disconnect()

            # L'eau est renouvelée, on lit les données
            await self.coordinator.async_request_refresh()

        except Exception as e:
            _LOGGER.error("Erreur Bluetooth lors du cycle de nouvelle analyse : %s", e)

class FliprFetchButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, mac, model_name):
        self.coordinator = coordinator
        self._mac = mac
        self._attr_name = "Récupérer dernière mesure"
        self._attr_unique_id = f"{mac}_recup_derniere"
        self._attr_icon = "mdi:bluetooth-transfer"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, mac)}, name=model_name, manufacturer="Flipr", model=model_name)

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()