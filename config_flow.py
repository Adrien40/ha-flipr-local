# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

"""Gestion de la configuration et des options pour Flipr AnalysR 3."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak, async_discovered_service_info
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN, CONF_MAC_ADDRESS, CONF_PH_CALIB_4, CONF_PH_CALIB_7,
    CONF_PH_MIN, CONF_PH_MAX, CONF_ORP_MIN, CONF_TEMP_MAX,
    CONF_PH_REF_7, CONF_PH_REF_4
)

MANUAL_ENTRY = "manual"

class FliprConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._mac_address = None
        self._discovered_name = "Flipr AnalysR 3"

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak):
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        
        self._mac_address = discovery_info.address
        self._discovered_name = discovery_info.name or f"Flipr {self._mac_address}"
        self.context["title_placeholders"] = {"name": self._discovered_name}
        
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            mac = user_input.get(CONF_MAC_ADDRESS)
            if mac == MANUAL_ENTRY:
                return await self.async_step_manual()
            
            final_mac = self._mac_address or mac
            await self.async_set_unique_id(final_mac)
            self._abort_if_unique_id_configured()
            
            user_input[CONF_MAC_ADDRESS] = final_mac
            return self.async_create_entry(title=self._discovered_name, data=user_input)

        discovered_devices = {MANUAL_ENTRY: "Entrer une adresse MAC manuellement"}
        for info in async_discovered_service_info(self.hass, False):
            if info.name and (info.name.startswith("Flipr") or info.name.startswith("F")):
                # --- NOUVEAU : EXTRACTION DYNAMIQUE DE LA VERSION ---
                if info.name.startswith("F") and len(info.name) > 1 and info.name[1].isdigit():
                    version = info.name[1]
                    display_name = f"Flipr AnalysR {version} ({info.name})"
                else:
                    display_name = f"{info.name} ({info.address})"
                
                discovered_devices[info.address] = display_name

        schema = {}
        if not self._mac_address:
            if len(discovered_devices) > 1:
                schema[vol.Required(CONF_MAC_ADDRESS)] = vol.In(discovered_devices)
            else:
                schema[vol.Required(CONF_MAC_ADDRESS)] = str

        schema.update({
            vol.Required(CONF_PH_CALIB_7, default=8.40): selector.NumberSelector(
                selector.NumberSelectorConfig(step=0.01, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(CONF_PH_CALIB_4, default=6.02): selector.NumberSelector(
                selector.NumberSelectorConfig(step=0.01, mode=selector.NumberSelectorMode.BOX)
            ),
        })

        return self.async_show_form(step_id="user", data_schema=vol.Schema(schema), errors=errors)

    async def async_step_manual(self, user_input=None):
        errors = {}
        if user_input is not None:
            mac = user_input[CONF_MAC_ADDRESS].upper()
            self._mac_address = mac
            self._discovered_name = f"Flipr {mac}"
            return await self.async_step_user(user_input)

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema({vol.Required(CONF_MAC_ADDRESS): str}),
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return FliprOptionsFlowHandler()

class FliprOptionsFlowHandler(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        c7 = self.config_entry.options.get(CONF_PH_CALIB_7) or self.config_entry.data.get(CONF_PH_CALIB_7) or 8.40
        c4 = self.config_entry.options.get(CONF_PH_CALIB_4) or self.config_entry.data.get(CONF_PH_CALIB_4) or 6.02
        ph_ref_7 = self.config_entry.options.get(CONF_PH_REF_7, 7.02)
        ph_ref_4 = self.config_entry.options.get(CONF_PH_REF_4, 4.00)
        ph_min = self.config_entry.options.get(CONF_PH_MIN, 6.90)
        ph_max = self.config_entry.options.get(CONF_PH_MAX, 7.50)
        orp_min = self.config_entry.options.get(CONF_ORP_MIN, 650)
        temp_max = self.config_entry.options.get(CONF_TEMP_MAX, 32.0)
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_PH_CALIB_7, default=float(c7)): selector.NumberSelector(selector.NumberSelectorConfig(step=0.01, mode=selector.NumberSelectorMode.BOX)),
                vol.Required(CONF_PH_REF_7, default=float(ph_ref_7)): selector.NumberSelector(selector.NumberSelectorConfig(step=0.01, mode=selector.NumberSelectorMode.BOX)),
                vol.Required(CONF_PH_CALIB_4, default=float(c4)): selector.NumberSelector(selector.NumberSelectorConfig(step=0.01, mode=selector.NumberSelectorMode.BOX)),
                vol.Required(CONF_PH_REF_4, default=float(ph_ref_4)): selector.NumberSelector(selector.NumberSelectorConfig(step=0.01, mode=selector.NumberSelectorMode.BOX)),
                vol.Required(CONF_PH_MIN, default=float(ph_min)): selector.NumberSelector(selector.NumberSelectorConfig(step=0.01, mode=selector.NumberSelectorMode.BOX)),
                vol.Required(CONF_PH_MAX, default=float(ph_max)): selector.NumberSelector(selector.NumberSelectorConfig(step=0.01, mode=selector.NumberSelectorMode.BOX)),
                vol.Required(CONF_ORP_MIN, default=int(orp_min)): selector.NumberSelector(selector.NumberSelectorConfig(step=1, mode=selector.NumberSelectorMode.BOX)),
                vol.Required(CONF_TEMP_MAX, default=float(temp_max)): selector.NumberSelector(selector.NumberSelectorConfig(step=0.5, mode=selector.NumberSelectorMode.BOX)),
            })
        )