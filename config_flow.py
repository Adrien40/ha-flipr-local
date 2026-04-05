# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak, async_discovered_service_info
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN, CONF_MAC_ADDRESS, CONF_USE_GATEWAY, CONF_PH_CALIB_4, CONF_PH_CALIB_7,
    CONF_PH_MIN, CONF_PH_MAX, CONF_ORP_MIN, CONF_TEMP_MIN, CONF_TEMP_MAX,
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
            if info.name and (info.name.startswith("Flipr") or info.name.startswith("F3B")):
                discovered_devices[info.address] = f"{info.name} ({info.address})"

        schema = {}
        if not self._mac_address:
            if len(discovered_devices) > 1:
                schema[vol.Required(CONF_MAC_ADDRESS)] = vol.In(discovered_devices)
            else:
                schema[vol.Required(CONF_MAC_ADDRESS)] = str

        schema.update({
            vol.Required(CONF_USE_GATEWAY, default=False): bool,
            vol.Required(CONF_PH_CALIB_7, default=8.40): selector.NumberSelector(selector.NumberSelectorConfig(step=0.01, mode=selector.NumberSelectorMode.BOX)),
            vol.Required(CONF_PH_CALIB_4, default=6.02): selector.NumberSelector(selector.NumberSelectorConfig(step=0.01, mode=selector.NumberSelectorMode.BOX)),
        })

        return self.async_show_form(step_id="user", data_schema=vol.Schema(schema), errors=errors)

    async def async_step_manual(self, user_input=None):
        errors = {}
        if user_input is not None:
            self._mac_address = user_input[CONF_MAC_ADDRESS].upper()
            self._discovered_name = f"Flipr {self._mac_address}"
            return await self.async_step_user()

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema({vol.Required(CONF_MAC_ADDRESS): str}),
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return FliprOptionsFlowHandler(config_entry)

class FliprOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        opt = self.config_entry.options
        dat = self.config_entry.data
        
        # Extraction propre des valeurs pour éviter tout crash silencieux
        use_gw = opt.get(CONF_USE_GATEWAY, dat.get(CONF_USE_GATEWAY, False))
        c7 = float(opt.get(CONF_PH_CALIB_7, dat.get(CONF_PH_CALIB_7, 8.40)))
        r7 = float(opt.get(CONF_PH_REF_7, 7.02))
        c4 = float(opt.get(CONF_PH_CALIB_4, dat.get(CONF_PH_CALIB_4, 6.02)))
        r4 = float(opt.get(CONF_PH_REF_4, 4.00))
        p_min = float(opt.get(CONF_PH_MIN, 6.90))
        p_max = float(opt.get(CONF_PH_MAX, 7.50))
        o_min = int(opt.get(CONF_ORP_MIN, 650))
        t_min = float(opt.get(CONF_TEMP_MIN, 6.0))
        t_max = float(opt.get(CONF_TEMP_MAX, 32.0))

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_USE_GATEWAY, default=use_gw): bool,
                vol.Required(CONF_PH_CALIB_7, default=c7): selector.NumberSelector(selector.NumberSelectorConfig(step=0.01, mode=selector.NumberSelectorMode.BOX)),
                vol.Required(CONF_PH_REF_7, default=r7): selector.NumberSelector(selector.NumberSelectorConfig(step=0.01, mode=selector.NumberSelectorMode.BOX)),
                vol.Required(CONF_PH_CALIB_4, default=c4): selector.NumberSelector(selector.NumberSelectorConfig(step=0.01, mode=selector.NumberSelectorMode.BOX)),
                vol.Required(CONF_PH_REF_4, default=r4): selector.NumberSelector(selector.NumberSelectorConfig(step=0.01, mode=selector.NumberSelectorMode.BOX)),
                vol.Required(CONF_PH_MIN, default=p_min): selector.NumberSelector(selector.NumberSelectorConfig(step=0.01, mode=selector.NumberSelectorMode.BOX)),
                vol.Required(CONF_PH_MAX, default=p_max): selector.NumberSelector(selector.NumberSelectorConfig(step=0.01, mode=selector.NumberSelectorMode.BOX)),
                vol.Required(CONF_ORP_MIN, default=o_min): selector.NumberSelector(selector.NumberSelectorConfig(step=1, mode=selector.NumberSelectorMode.BOX)),
                vol.Required(CONF_TEMP_MIN, default=t_min): selector.NumberSelector(selector.NumberSelectorConfig(step=0.5, mode=selector.NumberSelectorMode.BOX)),
                vol.Required(CONF_TEMP_MAX, default=t_max): selector.NumberSelector(selector.NumberSelectorConfig(step=0.5, mode=selector.NumberSelectorMode.BOX)),
            })
        )