# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import (
    DOMAIN,
    CONF_MAC_ADDRESS,
    get_flipr_model,
    flipr_device_info,
    CONF_PH_MIN,
    CONF_PH_MAX,
    CONF_ORP_MIN,
    CONF_ORP_MAX,
    CONF_TEMP_MIN,
    CONF_TEMP_MAX,
    DEFAULT_PH_MIN,
    DEFAULT_PH_MAX,
    DEFAULT_ORP_MIN,
    DEFAULT_ORP_MAX,
    DEFAULT_TEMP_MIN,
    DEFAULT_TEMP_MAX,
)

_DEFAULT_THRESHOLDS: dict[str, float] = {
    CONF_PH_MIN: DEFAULT_PH_MIN,
    CONF_PH_MAX: DEFAULT_PH_MAX,
    CONF_ORP_MIN: DEFAULT_ORP_MIN,
    CONF_ORP_MAX: DEFAULT_ORP_MAX,
    CONF_TEMP_MIN: DEFAULT_TEMP_MIN,
    CONF_TEMP_MAX: DEFAULT_TEMP_MAX,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    mac = entry.data[CONF_MAC_ADDRESS]
    model_name = entry.data.get("model") or get_flipr_model(entry.title)

    async_add_entities(
        [
            FliprAlertSensor(
                coordinator, entry.entry_id, mac, model_name, "ph_status", "ph"
            ),
            FliprAlertSensor(
                coordinator, entry.entry_id, mac, model_name, "orp_status", "orp"
            ),
            FliprAlertSensor(
                coordinator,
                entry.entry_id,
                mac,
                model_name,
                "temperature_status",
                "temperature",
            ),
        ]
    )


class FliprAlertSensor(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    # DO NOT REMOVE: Alert binary sensors are placed in the Diagnostic category
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator,
        entry_id: str,
        mac: str,
        model_name: str,
        translation_key: str,
        data_key: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._mac = mac
        self._data_key = data_key

        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{mac}_{translation_key}"
        self._attr_device_info = flipr_device_info(mac, model_name)
        self._cached_thresholds: dict[str, float] = dict(_DEFAULT_THRESHOLDS)

    def _refresh_cached_thresholds(self) -> None:
        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        if not entry:
            return
        self._cached_thresholds = {
            key: float(
                entry.options.get(key, entry.data.get(key, _DEFAULT_THRESHOLDS[key]))
            )
            for key in _DEFAULT_THRESHOLDS
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._refresh_cached_thresholds()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self._mac}_options_updated",
                self._handle_options_updated,
            )
        )

    @callback
    def _handle_options_updated(self) -> None:
        self._refresh_cached_thresholds()
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool | None:
        if not self.coordinator.data:
            return None

        val = self.coordinator.data.get(self._data_key)
        if val is None:
            return None

        t = self._cached_thresholds

        if self._data_key == "ph":
            return val < t[CONF_PH_MIN] or val > t[CONF_PH_MAX]
        if self._data_key == "orp":
            return val < t[CONF_ORP_MIN] or val > t[CONF_ORP_MAX]
        if self._data_key == "temperature":
            return val < t[CONF_TEMP_MIN] or val > t[CONF_TEMP_MAX]

        return None
