# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

import re
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers import selector

from .const import (
    CONF_CHLORINE_MODEL,
    CONF_CYA,
    CONF_MAC_ADDRESS,
    CONF_ORP_CALIB,
    CONF_ORP_MAX,
    CONF_ORP_MIN,
    CONF_ORP_REF,
    CONF_PH_CALIB_4,
    CONF_PH_CALIB_7,
    CONF_PH_MAX,
    CONF_PH_MIN,
    CONF_PH_REF_4,
    CONF_PH_REF_7,
    CONF_REFERENCE_TIME,
    CONF_SCAN_INTERVAL,
    CONF_SYNC_MODE,
    CONF_TEMP_MAX,
    CONF_TEMP_MIN,
    CONF_TEMP_OFFSET,
    CONF_USE_GATEWAY,
    DEFAULT_ORP_CALIB,
    DEFAULT_ORP_MAX,
    DEFAULT_ORP_MIN,
    DEFAULT_ORP_REF,
    DEFAULT_PH_CALIB_4,
    DEFAULT_PH_CALIB_7,
    DEFAULT_PH_MAX,
    DEFAULT_PH_MIN,
    DEFAULT_PH_REF_4,
    DEFAULT_PH_REF_7,
    DEFAULT_TEMP_MAX,
    DEFAULT_TEMP_MIN,
    DOMAIN,
)
from .model import get_flipr_model
from .validation import _flatten_sections, validate_calibration

MANUAL_ENTRY = "manual"
MAC_PATTERN = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")

SYNC_MODE_OPTIONS = ["0", "1", "2", "3"]
CHLORINE_MODEL_OPTIONS = ["chlorine", "bromine"]


class FliprConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 2

    def __init__(self) -> None:
        super().__init__()
        self._mac_address: str | None = None
        self._bt_name: str | None = None
        self._discovered_name: str = "Flipr"

    def _get_display_name(self, bt_name: str | None, model: str) -> str:
        if bt_name and bt_name != "Flipr" and not bt_name.startswith("Flipr Analys"):
            return f"{model} ({bt_name})"
        return model

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> config_entries.ConfigFlowResult:
        await self.async_set_unique_id(discovery_info.address.upper())
        self._abort_if_unique_id_configured()

        self._mac_address = discovery_info.address.upper()
        self._bt_name = discovery_info.name or ""

        model = get_flipr_model(self._bt_name)
        self._discovered_name = self._get_display_name(self._bt_name, model)

        self.context["title_placeholders"] = {"name": self._discovered_name}

        return await self.async_step_user()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            mac = user_input.get(CONF_MAC_ADDRESS)

            # FIX: use _flatten_sections() — the same logic as async_step_init —
            # so that section (dict) values consistently take priority over top-level
            # scalars in both flows.
            flat_input: dict[str, Any] = _flatten_sections(user_input)

            validation = validate_calibration(flat_input)
            if isinstance(validation, tuple):
                field, error_key = validation
                errors[field] = error_key
            else:
                normalized_input = validation

                raw_selection = mac or self._mac_address or ""
                if raw_selection.lower() == MANUAL_ENTRY:
                    return await self.async_step_manual()

                mac_match = re.search(
                    r"([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", raw_selection
                )
                if mac_match:
                    final_mac = mac_match.group(0).upper()
                else:
                    final_mac = raw_selection.upper()

                if not final_mac or not MAC_PATTERN.match(final_mac):
                    errors[CONF_MAC_ADDRESS] = "invalid_mac"
                else:
                    if final_mac != self._mac_address:
                        await self.async_set_unique_id(final_mac)
                        self._abort_if_unique_id_configured()

                    if not self._bt_name:
                        for info in async_discovered_service_info(self.hass, False):
                            if info.address.upper() == final_mac and info.name:
                                self._bt_name = info.name
                                break

                    model = get_flipr_model(self._bt_name)
                    title = self._get_display_name(self._bt_name, model)

                    entry_data = {
                        CONF_MAC_ADDRESS: final_mac,
                        "model": model,
                    }
                    normalized_input.pop(CONF_MAC_ADDRESS, None)
                    normalized_input.pop("model", None)

                    if CONF_SYNC_MODE not in normalized_input:
                        normalized_input[CONF_SYNC_MODE] = (
                            "2" if normalized_input.get(CONF_USE_GATEWAY, True) else "1"
                        )

                    return self.async_create_entry(
                        title=title, data=entry_data, options=normalized_input
                    )

        device_entries: list[str] = []
        mac_to_display: dict[str, str] = {}
        for info in async_discovered_service_info(self.hass, False):
            if info.name:
                name_up = info.name.upper()
                if name_up.startswith(("FLIPR", "F2", "F3")):
                    list_model = get_flipr_model(info.name)
                    display = self._get_display_name(info.name, list_model)
                    entry = f"{display} ({info.address.upper()})"
                    device_entries.append(entry)
                    mac_to_display[info.address.upper()] = entry

        default_selection: str | None = None
        if self._mac_address:
            if self._mac_address in mac_to_display:
                default_selection = mac_to_display[self._mac_address]
            else:
                model_auto = get_flipr_model(self._bt_name)
                display_auto = self._get_display_name(self._bt_name, model_auto)
                auto_entry = f"{display_auto} ({self._mac_address})"
                device_entries.insert(0, auto_entry)
                mac_to_display[self._mac_address] = auto_entry
                default_selection = auto_entry

        selector_options: list[str] = [MANUAL_ENTRY, *device_entries]

        schema: dict[Any, Any] = {}
        if len(selector_options) > 1:
            mac_key = (
                vol.Required(CONF_MAC_ADDRESS, default=default_selection)
                if default_selection
                else vol.Required(CONF_MAC_ADDRESS)
            )
            schema[mac_key] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=selector_options,
                    mode=selector.SelectSelectorMode.LIST,
                    translation_key="mac_address_select",
                    sort=False,
                )
            )
        else:
            schema[vol.Required(CONF_MAC_ADDRESS)] = str

        schema.update(
            {
                vol.Required("general"): section(
                    vol.Schema(
                        {
                            vol.Required(CONF_USE_GATEWAY, default=True): bool,
                            vol.Required(
                                CONF_CHLORINE_MODEL, default="chlorine"
                            ): selector.SelectSelector(
                                selector.SelectSelectorConfig(
                                    options=CHLORINE_MODEL_OPTIONS,
                                    mode=selector.SelectSelectorMode.DROPDOWN,
                                    translation_key="chlorine_model",
                                    sort=False,
                                )
                            ),
                            vol.Required(CONF_CYA, default=40): selector.NumberSelector(
                                selector.NumberSelectorConfig(
                                    min=0,
                                    max=150,
                                    step=1,
                                    mode=selector.NumberSelectorMode.BOX,
                                )
                            ),
                        }
                    ),
                    {"collapsed": False},
                ),
                vol.Required("synchronization"): section(
                    vol.Schema(
                        {
                            vol.Required(
                                CONF_SCAN_INTERVAL, default=60
                            ): selector.NumberSelector(
                                selector.NumberSelectorConfig(
                                    min=5,
                                    max=1440,
                                    step=1,
                                    mode=selector.NumberSelectorMode.BOX,
                                )
                            ),
                            vol.Required(
                                CONF_REFERENCE_TIME, default="08:00"
                            ): selector.TimeSelector(),
                        }
                    ),
                    {"collapsed": True},
                ),
                vol.Required("probes_calibration"): section(
                    vol.Schema(
                        {
                            vol.Required(
                                CONF_PH_CALIB_7, default=DEFAULT_PH_CALIB_7
                            ): selector.NumberSelector(
                                selector.NumberSelectorConfig(
                                    min=0,
                                    max=3000,
                                    step=0.01,
                                    mode=selector.NumberSelectorMode.BOX,
                                )
                            ),
                            vol.Required(
                                CONF_PH_REF_7, default=DEFAULT_PH_REF_7
                            ): selector.NumberSelector(
                                selector.NumberSelectorConfig(
                                    min=0,
                                    max=14,
                                    step=0.01,
                                    mode=selector.NumberSelectorMode.BOX,
                                )
                            ),
                            vol.Required(
                                CONF_PH_CALIB_4, default=DEFAULT_PH_CALIB_4
                            ): selector.NumberSelector(
                                selector.NumberSelectorConfig(
                                    min=0,
                                    max=3000,
                                    step=0.01,
                                    mode=selector.NumberSelectorMode.BOX,
                                )
                            ),
                            vol.Required(
                                CONF_PH_REF_4, default=DEFAULT_PH_REF_4
                            ): selector.NumberSelector(
                                selector.NumberSelectorConfig(
                                    min=0,
                                    max=14,
                                    step=0.01,
                                    mode=selector.NumberSelectorMode.BOX,
                                )
                            ),
                            vol.Required(
                                CONF_ORP_CALIB, default=int(DEFAULT_ORP_CALIB)
                            ): selector.NumberSelector(
                                selector.NumberSelectorConfig(
                                    min=0,
                                    max=1000,
                                    step=1,
                                    mode=selector.NumberSelectorMode.BOX,
                                )
                            ),
                            vol.Required(
                                CONF_ORP_REF, default=int(DEFAULT_ORP_REF)
                            ): selector.NumberSelector(
                                selector.NumberSelectorConfig(
                                    min=0,
                                    max=1000,
                                    step=1,
                                    mode=selector.NumberSelectorMode.BOX,
                                )
                            ),
                            vol.Required(
                                CONF_TEMP_OFFSET, default=0.0
                            ): selector.NumberSelector(
                                selector.NumberSelectorConfig(
                                    min=-5.0,
                                    max=5.0,
                                    step=0.1,
                                    mode=selector.NumberSelectorMode.BOX,
                                )
                            ),
                        }
                    ),
                    {"collapsed": False},
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema),
            errors=errors,
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            mac_raw = user_input[CONF_MAC_ADDRESS].strip()
            if not MAC_PATTERN.match(mac_raw):
                errors[CONF_MAC_ADDRESS] = "invalid_mac"
            else:
                self._mac_address = mac_raw.upper()
                self._bt_name = None
                self._discovered_name = "Flipr"
                return await self.async_step_user(user_input=None)

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema({vol.Required(CONF_MAC_ADDRESS): str}),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Point this entry at a different physical Flipr (e.g. after
        replacing the device), without losing its options, automations,
        or entity history. Only the MAC address changes; everything else
        (calibration, thresholds, sync mode) is kept as-is.
        """
        errors: dict[str, str] = {}
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            mac_raw = user_input[CONF_MAC_ADDRESS].strip()
            if not MAC_PATTERN.match(mac_raw):
                errors[CONF_MAC_ADDRESS] = "invalid_mac"
            else:
                final_mac = mac_raw.upper()
                if final_mac != reconfigure_entry.data.get(CONF_MAC_ADDRESS):
                    await self.async_set_unique_id(final_mac)
                    self._abort_if_unique_id_configured()

                bt_name = None
                for info in async_discovered_service_info(self.hass, False):
                    if info.address.upper() == final_mac and info.name:
                        bt_name = info.name
                        break
                model = get_flipr_model(bt_name)

                return self.async_update_reload_and_abort(
                    reconfigure_entry,
                    unique_id=final_mac,
                    data_updates={CONF_MAC_ADDRESS: final_mac, "model": model},
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_MAC_ADDRESS,
                        default=reconfigure_entry.data.get(CONF_MAC_ADDRESS, ""),
                    ): str
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> FliprOptionsFlowHandler:
        return FliprOptionsFlowHandler()


class FliprOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self) -> None:
        super().__init__()
        self._pending_data: dict[str, Any] | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            # FIX: use shared _flatten_sections() helper — same behaviour as config flow.
            flat_input: dict[str, Any] = _flatten_sections(user_input)

            validation = validate_calibration(flat_input)
            if isinstance(validation, tuple):
                field, error_key = validation
                errors[field] = error_key
            else:
                normalized_input = validation
                use_gw = normalized_input.get(CONF_USE_GATEWAY, True)
                sync_mode = normalized_input.get(CONF_SYNC_MODE)

                if use_gw and sync_mode in ("1", "3"):
                    self._pending_data = normalized_input
                    return await self.async_step_warning()

                return self.async_create_entry(title="", data=normalized_input)

        entry = self.config_entry
        coordinator = getattr(entry, "runtime_data", None)

        cya_coord = (
            coordinator.data.get(CONF_CYA) if coordinator and coordinator.data else None
        )
        current_cya = (
            cya_coord
            if cya_coord is not None
            else entry.options.get(CONF_CYA, entry.data.get(CONF_CYA, 40))
        )

        use_gw = entry.options.get(
            CONF_USE_GATEWAY, entry.data.get(CONF_USE_GATEWAY, True)
        )
        default_sync = "2" if use_gw else "1"
        sync_mode = entry.options.get(
            CONF_SYNC_MODE, entry.data.get(CONF_SYNC_MODE, default_sync)
        )
        current_model = entry.options.get(
            CONF_CHLORINE_MODEL, entry.data.get(CONF_CHLORINE_MODEL, "chlorine")
        )

        _c7_opt = entry.options.get(CONF_PH_CALIB_7)
        c7 = (
            _c7_opt
            if _c7_opt is not None
            else entry.data.get(CONF_PH_CALIB_7, DEFAULT_PH_CALIB_7)
        )

        _c4_opt = entry.options.get(CONF_PH_CALIB_4)
        c4 = (
            _c4_opt
            if _c4_opt is not None
            else entry.data.get(CONF_PH_CALIB_4, DEFAULT_PH_CALIB_4)
        )

        ph_ref_7 = entry.options.get(
            CONF_PH_REF_7, entry.data.get(CONF_PH_REF_7, DEFAULT_PH_REF_7)
        )
        ph_ref_4 = entry.options.get(
            CONF_PH_REF_4, entry.data.get(CONF_PH_REF_4, DEFAULT_PH_REF_4)
        )
        orp_target = entry.options.get(
            CONF_ORP_REF, entry.data.get(CONF_ORP_REF, DEFAULT_ORP_REF)
        )
        orp_measured = entry.options.get(
            CONF_ORP_CALIB, entry.data.get(CONF_ORP_CALIB, DEFAULT_ORP_CALIB)
        )
        temp_offset = entry.options.get(
            CONF_TEMP_OFFSET, entry.data.get(CONF_TEMP_OFFSET, 0.0)
        )

        ph_min = entry.options.get(CONF_PH_MIN, DEFAULT_PH_MIN)
        ph_max = entry.options.get(CONF_PH_MAX, DEFAULT_PH_MAX)
        orp_min = entry.options.get(CONF_ORP_MIN, DEFAULT_ORP_MIN)
        orp_max = entry.options.get(CONF_ORP_MAX, DEFAULT_ORP_MAX)
        temp_min = entry.options.get(CONF_TEMP_MIN, DEFAULT_TEMP_MIN)
        temp_max = entry.options.get(CONF_TEMP_MAX, DEFAULT_TEMP_MAX)

        scan_interval = (
            coordinator.data.get(CONF_SCAN_INTERVAL)
            if coordinator and coordinator.data
            else None
        )
        if scan_interval is None:
            scan_interval = entry.options.get(
                CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, 60)
            )

        current_reference_time = (
            coordinator.data.get(CONF_REFERENCE_TIME)
            if coordinator and coordinator.data
            else None
        )
        if current_reference_time is None:
            current_reference_time = entry.options.get(
                CONF_REFERENCE_TIME, entry.data.get(CONF_REFERENCE_TIME, "08:00")
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("general"): section(
                        vol.Schema(
                            {
                                vol.Required(CONF_USE_GATEWAY, default=use_gw): bool,
                                vol.Required(
                                    CONF_SYNC_MODE, default=str(sync_mode)
                                ): selector.SelectSelector(
                                    selector.SelectSelectorConfig(
                                        options=SYNC_MODE_OPTIONS,
                                        mode=selector.SelectSelectorMode.DROPDOWN,
                                        translation_key="sync_mode",
                                        sort=False,
                                    )
                                ),
                                vol.Required(
                                    CONF_CHLORINE_MODEL, default=current_model
                                ): selector.SelectSelector(
                                    selector.SelectSelectorConfig(
                                        options=CHLORINE_MODEL_OPTIONS,
                                        mode=selector.SelectSelectorMode.DROPDOWN,
                                        translation_key="chlorine_model",
                                        sort=False,
                                    )
                                ),
                                vol.Required(
                                    CONF_CYA, default=int(current_cya)
                                ): selector.NumberSelector(
                                    selector.NumberSelectorConfig(
                                        min=0,
                                        max=150,
                                        step=1,
                                        mode=selector.NumberSelectorMode.BOX,
                                    )
                                ),
                            }
                        ),
                        {"collapsed": False},
                    ),
                    vol.Required("synchronization"): section(
                        vol.Schema(
                            {
                                vol.Required(
                                    CONF_SCAN_INTERVAL, default=int(scan_interval)
                                ): selector.NumberSelector(
                                    selector.NumberSelectorConfig(
                                        min=5,
                                        max=1440,
                                        step=1,
                                        mode=selector.NumberSelectorMode.BOX,
                                    )
                                ),
                                vol.Required(
                                    CONF_REFERENCE_TIME,
                                    default=current_reference_time,
                                ): selector.TimeSelector(),
                            }
                        ),
                        {"collapsed": True},
                    ),
                    vol.Required("probes_calibration"): section(
                        vol.Schema(
                            {
                                vol.Required(
                                    CONF_PH_CALIB_7, default=float(c7)
                                ): selector.NumberSelector(
                                    selector.NumberSelectorConfig(
                                        min=0,
                                        max=3000,
                                        step=0.01,
                                        mode=selector.NumberSelectorMode.BOX,
                                    )
                                ),
                                vol.Required(
                                    CONF_PH_REF_7, default=float(ph_ref_7)
                                ): selector.NumberSelector(
                                    selector.NumberSelectorConfig(
                                        min=0,
                                        max=14,
                                        step=0.01,
                                        mode=selector.NumberSelectorMode.BOX,
                                    )
                                ),
                                vol.Required(
                                    CONF_PH_CALIB_4, default=float(c4)
                                ): selector.NumberSelector(
                                    selector.NumberSelectorConfig(
                                        min=0,
                                        max=3000,
                                        step=0.01,
                                        mode=selector.NumberSelectorMode.BOX,
                                    )
                                ),
                                vol.Required(
                                    CONF_PH_REF_4, default=float(ph_ref_4)
                                ): selector.NumberSelector(
                                    selector.NumberSelectorConfig(
                                        min=0,
                                        max=14,
                                        step=0.01,
                                        mode=selector.NumberSelectorMode.BOX,
                                    )
                                ),
                                vol.Required(
                                    CONF_ORP_CALIB, default=int(orp_measured)
                                ): selector.NumberSelector(
                                    selector.NumberSelectorConfig(
                                        min=0,
                                        max=1000,
                                        step=1,
                                        mode=selector.NumberSelectorMode.BOX,
                                    )
                                ),
                                vol.Required(
                                    CONF_ORP_REF, default=int(orp_target)
                                ): selector.NumberSelector(
                                    selector.NumberSelectorConfig(
                                        min=0,
                                        max=1000,
                                        step=1,
                                        mode=selector.NumberSelectorMode.BOX,
                                    )
                                ),
                                vol.Required(
                                    CONF_TEMP_OFFSET, default=float(temp_offset)
                                ): selector.NumberSelector(
                                    selector.NumberSelectorConfig(
                                        min=-5.0,
                                        max=5.0,
                                        step=0.1,
                                        mode=selector.NumberSelectorMode.BOX,
                                    )
                                ),
                            }
                        ),
                        {"collapsed": True},
                    ),
                    vol.Required("alert_thresholds"): section(
                        vol.Schema(
                            {
                                vol.Required(
                                    CONF_PH_MIN, default=float(ph_min)
                                ): selector.NumberSelector(
                                    selector.NumberSelectorConfig(
                                        min=0,
                                        max=14,
                                        step=0.01,
                                        mode=selector.NumberSelectorMode.BOX,
                                    )
                                ),
                                vol.Required(
                                    CONF_PH_MAX, default=float(ph_max)
                                ): selector.NumberSelector(
                                    selector.NumberSelectorConfig(
                                        min=0,
                                        max=14,
                                        step=0.01,
                                        mode=selector.NumberSelectorMode.BOX,
                                    )
                                ),
                                vol.Required(
                                    CONF_ORP_MIN, default=int(orp_min)
                                ): selector.NumberSelector(
                                    selector.NumberSelectorConfig(
                                        min=0,
                                        max=1200,
                                        step=1,
                                        mode=selector.NumberSelectorMode.BOX,
                                    )
                                ),
                                vol.Required(
                                    CONF_ORP_MAX, default=int(orp_max)
                                ): selector.NumberSelector(
                                    selector.NumberSelectorConfig(
                                        min=0,
                                        max=1200,
                                        step=1,
                                        mode=selector.NumberSelectorMode.BOX,
                                    )
                                ),
                                vol.Required(
                                    CONF_TEMP_MIN, default=float(temp_min)
                                ): selector.NumberSelector(
                                    selector.NumberSelectorConfig(
                                        min=0,
                                        max=50,
                                        step=0.5,
                                        mode=selector.NumberSelectorMode.BOX,
                                    )
                                ),
                                vol.Required(
                                    CONF_TEMP_MAX, default=float(temp_max)
                                ): selector.NumberSelector(
                                    selector.NumberSelectorConfig(
                                        min=0,
                                        max=50,
                                        step=0.5,
                                        mode=selector.NumberSelectorMode.BOX,
                                    )
                                ),
                            }
                        ),
                        {"collapsed": True},
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_warning(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if self._pending_data is None:
            return await self.async_step_init()
        if user_input is not None:
            data = self._pending_data
            self._pending_data = None
            return self.async_create_entry(title="", data=data)
        return self.async_show_form(step_id="warning")
