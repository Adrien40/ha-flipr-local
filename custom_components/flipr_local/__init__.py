# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store

from .const import (
    CONF_MAC_ADDRESS,
    CONF_SYNC_MODE,
    CONF_USE_GATEWAY,
    DOMAIN,
    PLATFORMS,
    REMOVED_ENTITIES,
)
from .coordinator import FliprDataCoordinator, format_mac_safe, get_opt, store_key

_LOGGER = logging.getLogger(__name__)

type FliprConfigEntry = ConfigEntry[FliprDataCoordinator]


async def update_listener(hass: HomeAssistant, entry: FliprConfigEntry) -> None:
    coordinator = entry.runtime_data
    if not coordinator:
        return

    new_sync_mode = entry.options.get(CONF_SYNC_MODE)
    new_use_gw = get_opt(entry, CONF_USE_GATEWAY, True)

    mode_changed = new_sync_mode != coordinator.last_configured_sync_mode
    gw_changed = new_use_gw != coordinator.last_configured_use_gw

    coordinator.last_configured_sync_mode = new_sync_mode
    coordinator.last_configured_use_gw = new_use_gw

    coordinator.recompute_derived_values()

    async_dispatcher_send(
        hass,
        f"{DOMAIN}_{coordinator.mac}_options_updated",
    )

    if (mode_changed or gw_changed) and new_use_gw and new_sync_mode is not None:
        coordinator.set_pending_cmd("mode", int(new_sync_mode))
        coordinator.request_one_shot_analysis()
        if coordinator._is_shutdown:
            _LOGGER.debug(
                "Skipping sync mode refresh for %s: coordinator is shutting down",
                coordinator.safe_mac,
            )
            return
        if not coordinator.ble_lock.locked():
            entry.async_create_background_task(
                hass,
                coordinator.async_request_refresh(),
                "flipr_sync_mode_refresh",
            )
        else:
            _LOGGER.debug(
                "BLE lock already held for %s - sync mode refresh will apply on next cycle",
                coordinator.safe_mac,
            )


async def async_migrate_entry(hass: HomeAssistant, entry: FliprConfigEntry) -> bool:
    """Migrate an entry created before the chlorine sensors were removed (1.2.0).

    Removes the two retired sensors from the registry, otherwise they would
    stay "unavailable" forever. Only the minor version changes: a downgrade
    remains possible. Options (CyA, treatment type) are kept.
    """
    if entry.version > 1:
        return False

    if entry.minor_version < 2:
        _LOGGER.debug("Migrating Flipr entry %s to 1.2", entry.entry_id)
        hass.config_entries.async_update_entry(entry, minor_version=2)

        ent_reg = er.async_get(hass)
        for reg_entry in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
            if any(
                reg_entry.domain == platform
                and reg_entry.unique_id.endswith(f"_{suffix}")
                for platform, suffix in REMOVED_ENTITIES
            ):
                _LOGGER.debug("Removing obsolete entity %s", reg_entry.entity_id)
                ent_reg.async_remove(reg_entry.entity_id)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: FliprConfigEntry) -> bool:
    mac = entry.data[CONF_MAC_ADDRESS]
    safe_mac = format_mac_safe(mac)

    coordinator = FliprDataCoordinator(hass, entry, mac, safe_mac)
    await coordinator.async_initialize()

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not coordinator.data.get("ph_raw"):
        _LOGGER.debug("No history found, launching initial analysis.")
        entry.async_create_background_task(
            hass,
            coordinator.async_request_refresh(),
            "flipr_initial_refresh",
        )
    else:
        _LOGGER.debug("History found on disk, restoring state.")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: FliprConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if ok:
        coordinator = entry.runtime_data
        if coordinator:
            await coordinator.async_shutdown()

    return ok


async def async_remove_entry(hass: HomeAssistant, entry: FliprConfigEntry) -> None:
    mac = entry.data.get(CONF_MAC_ADDRESS)
    if mac:
        store: Store[dict[str, Any]] = Store(hass, 1, store_key(mac))
        await store.async_remove()
