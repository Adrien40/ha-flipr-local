"""Repair issue: created when unreachable for too long, cleared on recovery."""

from __future__ import annotations

from datetime import timedelta

import homeassistant.util.dt as dt_util
from homeassistant.helpers import issue_registry as ir

from custom_components.flipr_local.const import DOMAIN

from .helpers import build_frame


async def test_stale_device_creates_repair_issue(hass, coordinator, ble):
    coordinator.update_volatile_state(
        {"last_received": dt_util.utcnow() - timedelta(days=5)}
    )
    ble.last_seen_age = 999
    await coordinator.async_refresh()

    issue = ir.async_get(hass).async_get_issue(DOMAIN, f"stale_{coordinator.safe_mac}")
    assert issue is not None


async def test_recovered_device_clears_repair_issue(hass, coordinator, ble):
    coordinator.update_volatile_state(
        {"last_received": dt_util.utcnow() - timedelta(days=5)}
    )
    ble.last_seen_age = 999
    await coordinator.async_refresh()
    assert (
        ir.async_get(hass).async_get_issue(DOMAIN, f"stale_{coordinator.safe_mac}")
        is not None
    )

    ble.last_seen_age = 0.0
    ble.client.frames = [build_frame(battery_mv=3301)]
    await coordinator.async_refresh()

    issue = ir.async_get(hass).async_get_issue(DOMAIN, f"stale_{coordinator.safe_mac}")
    assert issue is None


async def test_recent_unavailability_does_not_create_issue(coordinator, ble, hass):
    ble.last_seen_age = 999
    await coordinator.async_refresh()

    issue = ir.async_get(hass).async_get_issue(DOMAIN, f"stale_{coordinator.safe_mac}")
    assert issue is None
