# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import FliprConfigEntry
from .const import CONF_MAC_ADDRESS

TO_REDACT = {CONF_MAC_ADDRESS}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: FliprConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data

    return {
        "entry": {
            "title": entry.title,
            "version": entry.version,
            "minor_version": entry.minor_version,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "ble_available": coordinator.ble_available,
            "retry_count": coordinator.retry_count,
            "update_interval": str(coordinator.update_interval),
            "next_slot": str(coordinator.next_slot) if coordinator.next_slot else None,
            "data": async_redact_data(dict(coordinator.data), TO_REDACT),
        },
    }
