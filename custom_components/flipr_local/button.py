# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

import logging
import asyncio
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import (
    DOMAIN,
    CONF_MAC_ADDRESS,
    get_flipr_model,
    flipr_device_info,
    TIMEOUT_FORCE_REFRESH,
    BT_STATUS_OUT_OF_RANGE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    mac = entry.data[CONF_MAC_ADDRESS]
    model_name = entry.data.get("model") or get_flipr_model(entry.title)

    async_add_entities([FliprForceAnalysisButton(coordinator, mac, model_name)])


class FliprForceAnalysisButton(CoordinatorEntity, ButtonEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "force_analysis"

    def __init__(self, coordinator, mac: str, model_name: str) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._attr_unique_id = f"{mac}_force_analysis"
        self._attr_icon = "mdi:refresh-circle"
        self._attr_device_info = flipr_device_info(mac, model_name)

    async def async_press(self) -> None:
        if self.coordinator._is_shutdown:
            _LOGGER.debug(
                "Ignoring button press for %s: coordinator is shutting down",
                self.coordinator.safe_mac,
            )
            return

        if self.coordinator.data and self.coordinator.data.get("action_running", False):
            _LOGGER.warning(
                "Analysis already running on Flipr (timeout: %ss)",
                TIMEOUT_FORCE_REFRESH,
            )
            return

        if not self.coordinator.ble_available:
            _LOGGER.warning(
                "Cannot start analysis for %s: real-time Bluetooth signal unavailable",
                self.coordinator.safe_mac,
            )
            self.coordinator.update_volatile_state(
                {"bluetooth_status": BT_STATUS_OUT_OF_RANGE}
            )
            return

        self.coordinator.request_one_shot_analysis()
        self.coordinator.update_volatile_state({"action_running": True})

        _LOGGER.info(
            "New analysis requested for %s (~60s)...",
            self.coordinator.safe_mac,
        )

        async def _run_analysis() -> None:
            try:
                await asyncio.wait_for(
                    self.coordinator.async_request_refresh(),
                    timeout=TIMEOUT_FORCE_REFRESH,
                )
            except asyncio.TimeoutError:
                _LOGGER.error(
                    "Analysis exceeded timeout of %s seconds for %s",
                    TIMEOUT_FORCE_REFRESH,
                    self.coordinator.safe_mac,
                )
            except Exception as err:
                _LOGGER.error(
                    "Analysis failed for %s: %s",
                    self.coordinator.safe_mac,
                    err,
                )
            finally:
                self.coordinator.update_volatile_state({"action_running": False})

        entry = self.hass.config_entries.async_get_entry(self.coordinator.entry_id)
        if entry:
            entry.async_create_background_task(
                self.hass,
                _run_analysis(),
                "flipr_button_refresh",
            )
