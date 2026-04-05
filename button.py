# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

"""Boutons pour Flipr AnalysR 3."""
import logging, asyncio
from bleak import BleakClient
from bleak_retry_connector import establish_connection
from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, CONF_MAC_ADDRESS, FLIPR_COMMAND_UUID

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    mac = entry.data[CONF_MAC_ADDRESS]
    
    async_add_entities([
        FliprActionTaskButton(coordinator, mac, "Nouvelle Analyse (~60s)", "nouvelle_analyse", FLIPR_COMMAND_UUID, "mdi:test-tube"),
        FliprRefreshButton(coordinator, mac, "Récupérer dernière mesure", "recup_derniere", "mdi:cloud-download")
    ])

class FliprActionTaskButton(CoordinatorEntity, ButtonEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator, mac, name, key, action_uuid, icon):
        super().__init__(coordinator)
        self._mac = mac
        self._attr_name = name
        self._attr_unique_id = f"{mac}_{key}_btn"
        self._attr_icon = icon
        self._action_uuid = action_uuid
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, mac)}, name="Flipr AnalysR 3", manufacturer="Flipr", model="AnalysR 3")

    @property
    def available(self) -> bool:
        return True

    async def async_press(self) -> None:
        _LOGGER.info("Action manuelle : Nouvelle analyse lancée pour %s", self._mac)
        self.hass.async_create_task(self._run_analysis_cycle())

    async def _run_analysis_cycle(self):
        device = async_ble_device_from_address(self.hass, self._mac, connectable=True)
        if not device:
            _LOGGER.error("Bouton : Flipr hors de portée Bluetooth.")
            return
        try:
            client = await establish_connection(BleakClient, device, self._mac)
            await client.write_gatt_char(self._action_uuid, bytearray([0x01]), response=True)
            await client.disconnect()
            await asyncio.sleep(45)
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Erreur bouton : %s", err)

class FliprRefreshButton(CoordinatorEntity, ButtonEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator, mac, name, key, icon):
        super().__init__(coordinator)
        self._mac = mac
        self._attr_name = name
        self._attr_unique_id = f"{mac}_{key}_btn"
        self._attr_icon = icon
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, mac)}, name="Flipr AnalysR 3", manufacturer="Flipr", model="AnalysR 3")

    @property
    def available(self) -> bool:
        return True

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()
