# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

import logging
from datetime import timedelta
from homeassistant.components.number import RestoreNumber
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import (
    DOMAIN,
    CONF_MAC_ADDRESS,
    CONF_CYA,
    CONF_TAC,
    CONF_TH,
    CONF_TDS,
    CONF_SCAN_INTERVAL,
    CONF_CHLORINE_MODEL,
    get_flipr_model,
    flipr_device_info,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    mac = entry.data[CONF_MAC_ADDRESS]
    entry_id = entry.entry_id
    model_name = entry.data.get("model") or get_flipr_model(entry.title)

    async_add_entities(
        [
            FliprUpdateIntervalNumber(coordinator, mac, model_name),
            FliprWaterConfigNumber(
                coordinator,
                mac,
                CONF_TAC,
                0,
                500,
                1,
                0,
                "mdi:water-percent",
                entry_id,
                model_name,
                "mg/L",
            ),
            FliprWaterConfigNumber(
                coordinator,
                mac,
                CONF_TDS,
                0,
                5000,
                1,
                0,
                "mdi:blur",
                entry_id,
                model_name,
                "ppm",
            ),
            FliprWaterConfigNumber(
                coordinator,
                mac,
                CONF_TH,
                0,
                800,
                1,
                0,
                "mdi:water-outline",
                entry_id,
                model_name,
                "mg/L",
            ),
            FliprWaterConfigNumber(
                coordinator,
                mac,
                CONF_CYA,
                0,
                150,
                1,
                0,
                "mdi:shield-sun",
                entry_id,
                model_name,
                "mg/L",
            ),
        ]
    )


class FliprUpdateIntervalNumber(CoordinatorEntity, RestoreNumber):
    _attr_has_entity_name = True
    _attr_translation_key = "scan_interval"

    def __init__(self, coordinator, mac: str, model_name: str) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._attr_unique_id = f"{mac}_{CONF_SCAN_INTERVAL}"
        self._attr_native_min_value = 5
        self._attr_native_max_value = 1440
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = "min"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:sync"
        self._attr_mode = "box"
        self._attr_device_info = flipr_device_info(mac, model_name)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        val = (
            int(round(float(last.native_value)))
            if last and last.native_value is not None
            else 60
        )
        val = max(self._attr_native_min_value, min(val, self._attr_native_max_value))
        self._attr_native_value = val
        self.coordinator.update_interval = timedelta(minutes=val)
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        val = int(round(float(value)))
        val = max(self._attr_native_min_value, min(val, self._attr_native_max_value))
        self._attr_native_value = val
        self.coordinator.update_interval = timedelta(minutes=val)
        self.async_write_ha_state()
        # Trigger a volatile (no-save) coordinator update so that FliprNextAnalysisSensor
        # recalculates its value based on the new interval without writing to disk.
        self.coordinator.update_volatile_state({})


class FliprWaterConfigNumber(CoordinatorEntity, RestoreNumber):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        mac: str,
        key: str,
        min_val: float,
        max_val: float,
        step: float,
        default_val: float,
        icon: str,
        entry_id: str,
        model_name: str,
        unit: str,
    ) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._key = key
        self._entry_id = entry_id
        self._attr_translation_key = key
        self._attr_unique_id = f"{mac}_{key}"
        self._attr_native_min_value = min_val
        self._attr_native_max_value = max_val
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._default_val = default_val
        self._attr_mode = "box"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_info = flipr_device_info(mac, model_name)
        self._chlorine_model: str = "chlorine"

    def _refresh_chlorine_model(self) -> None:
        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        if entry:
            self._chlorine_model = entry.options.get(
                CONF_CHLORINE_MODEL, entry.data.get(CONF_CHLORINE_MODEL, "chlorine")
            )

    @property
    def available(self) -> bool:
        if self._key == CONF_CYA:
            return self._chlorine_model != "bromine"
        return True

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        val = self.coordinator.data.get(self._key) if self.coordinator.data else None
        if val is None:
            entry = self.hass.config_entries.async_get_entry(self._entry_id)
            if entry and self._key in entry.options:
                val = int(round(float(entry.options[self._key])))
        if val is None:
            last = await self.async_get_last_number_data()
            val = (
                int(round(float(last.native_value)))
                if last and last.native_value is not None
                else self._default_val
            )

        val = max(self._attr_native_min_value, min(val, self._attr_native_max_value))
        self._attr_native_value = val

        # FIX: use update_volatile_state instead of update_local_state.
        # The value being set here was just read from coordinator data, entry options,
        # or HA state restore — it is already persisted. Calling update_local_state
        # would trigger _schedule_save(), unnecessarily rewriting data to disk on
        # every HA restart. update_volatile_state notifies entities without saving.
        self.coordinator.update_volatile_state({self._key: val})
        self._refresh_chlorine_model()

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self._mac}_options_updated",
                self._handle_options_updated,
            )
        )

        self.async_write_ha_state()

    @callback
    def _handle_options_updated(self) -> None:
        self._refresh_chlorine_model()
        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        if entry and self._key in entry.options:
            new_val = int(round(float(entry.options[self._key])))
            new_val = max(
                int(self._attr_native_min_value),
                min(new_val, int(self._attr_native_max_value)),
            )
            if new_val != self._attr_native_value:
                self._attr_native_value = new_val
                self.coordinator.update_local_state({self._key: new_val})
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        int_val = int(round(float(value)))
        int_val = max(
            int(self._attr_native_min_value),
            min(int_val, int(self._attr_native_max_value)),
        )
        self._attr_native_value = int_val
        self.async_write_ha_state()
        self.coordinator.update_local_state({self._key: int_val})
        self.coordinator.request_deferred_recompute()
