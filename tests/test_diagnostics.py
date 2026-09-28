"""diagnostics.py: presence of expected data, MAC address redacted."""

from __future__ import annotations

from custom_components.flipr_local.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .conftest import MAC


async def test_diagnostics_redacts_mac_address(hass, coordinator, entry):
    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["entry"]["data"]["mac_address"] == "**REDACTED**"
    assert MAC not in str(result)


async def test_diagnostics_includes_coordinator_state(hass, coordinator, entry):
    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["coordinator"]["last_update_success"] is True
    assert "ph" in result["coordinator"]["data"]
    assert result["entry"]["version"] == entry.version
