# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

import asyncio
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_MAC_ADDRESS,
    TIMEOUT_FORCE_REFRESH,
    flipr_device_info,
)
from .coordinator import FliprDataCoordinator
from .model import get_flipr_model

_LOGGER = logging.getLogger(__name__)


# Single Bluetooth connection to the device: commands must be serialized.
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    mac = entry.data[CONF_MAC_ADDRESS]
    model_name = entry.data.get("model") or get_flipr_model(entry.title)

    async_add_entities([FliprForceAnalysisButton(coordinator, mac, model_name)])


class FliprForceAnalysisButton(CoordinatorEntity[FliprDataCoordinator], ButtonEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "force_analysis"

    def __init__(
        self, coordinator: FliprDataCoordinator, mac: str, model_name: str
    ) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._attr_unique_id = f"{mac}_force_analysis"
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
            except TimeoutError:
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
