# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

from homeassistant.components.sensor import (
    SensorEntity, SensorDeviceClass, EntityCategory,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, CONF_MAC_ADDRESS, get_flipr_model

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    mac_address = entry.data[CONF_MAC_ADDRESS]
    model_name = entry.data.get("model") or get_flipr_model(entry.title)

    async_add_entities([
        FliprSensor(coordinator, mac_address, "Température", "temperature", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, 2, model_name=model_name),
        FliprSensor(coordinator, mac_address, "pH", "ph", SensorDeviceClass.PH, None, 2, model_name=model_name),
        FliprSensor(coordinator, mac_address, "Redox", "orp", None, "mV", model_name=model_name),
        FliprSensor(coordinator, mac_address, "Chlore Actif (HOCl) (beta)", "chlore_actif_hocl", None, "mg/L", 2, icon="mdi:pool", model_name=model_name),
        FliprSensor(coordinator, mac_address, "Indice de Langelier", "isl", None, None, 2, category=EntityCategory.DIAGNOSTIC, icon="mdi:scale-balance", model_name=model_name),
        FliprSensor(coordinator, mac_address, "Indice de Langelier Statut", "isl_statut", None, None, None, category=EntityCategory.DIAGNOSTIC, icon="mdi:water-alert", model_name=model_name),
        FliprSensor(coordinator, mac_address, "pH d'Équilibre (Taylor)", "ph_equilibre_cible", None, None, 2, category=EntityCategory.DIAGNOSTIC, icon="mdi:target", model_name=model_name),
        FliprSensor(coordinator, mac_address, "Batterie", "battery", SensorDeviceClass.VOLTAGE, "mV", category=EntityCategory.DIAGNOSTIC, icon="mdi:battery", model_name=model_name),
        FliprSensor(coordinator, mac_address, "pH Brut (mV)", "ph_raw", None, "mV", category=EntityCategory.DIAGNOSTIC, icon="mdi:flash-outline", model_name=model_name),
        FliprSensor(coordinator, mac_address, "pH Brut (Usine)", "ph_usine", SensorDeviceClass.PH, None, 2, category=EntityCategory.DIAGNOSTIC, icon="mdi:factory", model_name=model_name),
        FliprSensor(coordinator, mac_address, "Dernière mesure", "last_received", SensorDeviceClass.TIMESTAMP, None, category=EntityCategory.DIAGNOSTIC, icon="mdi:clock-check-outline", model_name=model_name),
        FliprSensor(coordinator, mac_address, "Trame Brute", "raw_frame", None, None, category=EntityCategory.DIAGNOSTIC, icon="mdi:bluetooth-transfer", model_name=model_name),
        FliprSensor(coordinator, mac_address, "Signal Bluetooth", "rssi", SensorDeviceClass.SIGNAL_STRENGTH, "dBm", category=EntityCategory.DIAGNOSTIC, model_name=model_name),
    ])

class FliprSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator, mac, name, key, device_class=None, unit=None, precision=None, category=None, icon=None, model_name="Flipr"):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{mac}_{key}"
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_suggested_display_precision = precision
        self._attr_entity_category = category
        if icon: self._attr_icon = icon
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)}, 
            name=model_name, 
            manufacturer="Flipr", 
            model=model_name
        )

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self._key)