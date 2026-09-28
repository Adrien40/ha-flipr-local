"""Setup, unload, removal, and migration of the entry."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import entity_registry as er

from custom_components.flipr_local import (
    async_migrate_entry,
    async_remove_entry,
    async_unload_entry,
    update_listener,
)
from custom_components.flipr_local.const import (
    CONF_CHLORINE_MODEL,
    CONF_CYA,
    CONF_MAC_ADDRESS,
    CONF_SYNC_MODE,
    CONF_USE_GATEWAY,
    DOMAIN,
    PLATFORMS,
)
from custom_components.flipr_local.coordinator import store_key

from .conftest import make_entry
from .helpers import MAC

EXPECTED_UNIQUE_IDS = {
    ("sensor", "temperature"),
    ("sensor", "ph"),
    ("sensor", "orp"),
    ("sensor", "target_equilibrium_ph"),
    ("sensor", "lsi"),
    ("sensor", "lsi_status"),
    ("sensor", "ph_raw"),
    ("sensor", "orp_raw"),
    ("sensor", "factory_ph"),
    ("sensor", "battery_level"),
    ("sensor", "battery"),
    ("sensor", "last_received"),
    ("sensor", "raw_frame"),
    ("sensor", "sync_mode"),
    ("sensor", "bluetooth_status"),
    ("sensor", "rssi"),
    ("sensor", "next_analysis"),
    ("binary_sensor", "ph_status"),
    ("binary_sensor", "orp_status"),
    ("binary_sensor", "temperature_status"),
    ("button", "force_analysis"),
    ("switch", "active_measures"),
    ("select", "chlorine_model"),
    ("number", "scan_interval"),
    ("number", "tac"),
    ("number", "th"),
    ("number", "tds"),
    ("number", "cya"),
    ("time", "reference_time"),
}


def test_platforms():
    assert set(PLATFORMS) == {
        "sensor",
        "binary_sensor",
        "button",
        "number",
        "select",
        "switch",
        "time",
    }


async def test_setup_creates_exactly_the_expected_entities(hass, coordinator, entry):
    registered = {
        (e.domain, e.unique_id.removeprefix(f"{MAC}_"))
        for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    }
    assert registered == EXPECTED_UNIQUE_IDS


async def test_no_chlorine_sensors(hass, coordinator, entry):
    unique_ids = {
        e.unique_id
        for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    }
    assert not any("free_chlorine" in u or "hocl" in u for u in unique_ids)


async def test_every_entity_has_a_translated_name(hass, coordinator, entry):
    """A missing translation key would give an entity with no name."""
    for reg in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id):
        assert reg.original_name, f"{reg.unique_id} has no translated name"


async def test_entry_is_loaded_and_coordinator_registered(hass, coordinator, entry):
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data is coordinator


async def test_unload_shuts_coordinator_down(hass, coordinator, entry):
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert coordinator._is_shutdown is True


async def test_unload_saves_data_to_disk(hass, coordinator, entry, hass_storage):
    await hass.config_entries.async_unload(entry.entry_id)
    assert hass_storage[store_key(MAC)]["data"]["ph_raw"] == 1600


async def test_unload_entry_without_runtime_data_does_not_crash(
    hass, coordinator, entry
):
    """If platforms unload successfully but no coordinator is attached
    (e.g. setup failed before it was assigned), unload must not try to
    shut it down."""
    original_unload_platforms = hass.config_entries.async_unload_platforms
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    entry.runtime_data = None
    try:
        assert await async_unload_entry(hass, entry) is True
        assert coordinator._is_shutdown is False
    finally:
        hass.config_entries.async_unload_platforms = original_unload_platforms


async def test_remove_entry_deletes_stored_data(hass, coordinator, entry, hass_storage):
    await coordinator.async_save_to_disk()
    assert store_key(MAC) in hass_storage
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert store_key(MAC) not in hass_storage


async def test_update_listener_noop_without_coordinator(hass):
    """Guards against a stale/duplicate listener call before setup finished."""
    entry = make_entry()
    entry.add_to_hass(hass)
    entry.runtime_data = None
    await update_listener(hass, entry)  # must not raise


async def test_update_listener_skips_refresh_while_shutting_down(
    hass, coordinator, entry
):
    coordinator.async_request_refresh = AsyncMock()
    coordinator._is_shutdown = True
    try:
        hass.config_entries.async_update_entry(
            entry,
            options={
                **entry.options,
                CONF_SYNC_MODE: "0",
                CONF_USE_GATEWAY: True,
            },
        )
        await hass.async_block_till_done(wait_background_tasks=True)
        coordinator.async_request_refresh.assert_not_awaited()
    finally:
        coordinator._is_shutdown = False


async def test_update_listener_defers_refresh_when_ble_lock_held(
    hass, coordinator, entry
):
    coordinator.async_request_refresh = AsyncMock()
    await coordinator.ble_lock.acquire()
    try:
        hass.config_entries.async_update_entry(
            entry,
            options={
                **entry.options,
                CONF_SYNC_MODE: "0",
                CONF_USE_GATEWAY: True,
            },
        )
        await hass.async_block_till_done(wait_background_tasks=True)
        coordinator.async_request_refresh.assert_not_awaited()
    finally:
        coordinator.ble_lock.release()


async def test_migrate_entry_rejects_future_major_version(hass):
    """Called directly: Home Assistant's own core intercepts this case first
    in the normal setup flow, so the integration's own guard is never
    reached via `hass.config_entries.async_setup`."""
    entry = make_entry(version=2)
    entry.add_to_hass(hass)
    assert await async_migrate_entry(hass, entry) is False


async def test_unload_entry_skips_shutdown_when_platforms_fail(
    hass, coordinator, entry
):
    """If unloading the platforms fails, the coordinator must not be shut down."""
    original_unload_platforms = hass.config_entries.async_unload_platforms
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)
    try:
        assert await async_unload_entry(hass, entry) is False
        assert coordinator._is_shutdown is False
    finally:
        # Restore before returning: the `coordinator` fixture's teardown
        # calls the real `hass.config_entries.async_unload(...)` right
        # after this test function returns, and that goes through this
        # same method to actually unload the platforms and shut the
        # coordinator down cleanly.
        hass.config_entries.async_unload_platforms = original_unload_platforms


async def test_remove_entry_without_mac_is_a_noop(hass):
    entry = make_entry()
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        entry, data={k: v for k, v in entry.data.items() if k != CONF_MAC_ADDRESS}
    )
    await async_remove_entry(hass, entry)  # must not raise


async def test_setup_survives_first_cycle_failure(setup_integration, ble):
    ble.scanner_count = 0  # no adapter: the 1st cycle fails
    entry = make_entry()
    await setup_integration(entry)
    assert entry.state is ConfigEntryState.LOADED  # the integration stays loaded


# ---------------------------------------------------------------------------
# Migration 1.1 -> 1.2 (removal of estimated chlorine sensors)
# ---------------------------------------------------------------------------
def _legacy_entry():
    return make_entry(minor_version=1, **{CONF_CYA: 60, CONF_CHLORINE_MODEL: "bromine"})


async def test_migration_removes_orphan_chlorine_entities(hass, setup_integration):
    entry = _legacy_entry()
    entry.add_to_hass(hass)
    ent_reg = er.async_get(hass)
    for platform, key in (
        ("sensor", "estimated_free_chlorine"),
        ("sensor", "active_chlorine_hocl"),
        ("sensor", "ph"),  # must survive
    ):
        ent_reg.async_get_or_create(
            platform, DOMAIN, f"{MAC}_{key}", config_entry=entry
        )

    await setup_integration(entry)

    assert (
        ent_reg.async_get_entity_id("sensor", DOMAIN, f"{MAC}_estimated_free_chlorine")
        is None
    )
    assert (
        ent_reg.async_get_entity_id("sensor", DOMAIN, f"{MAC}_active_chlorine_hocl")
        is None
    )
    assert ent_reg.async_get_entity_id("sensor", DOMAIN, f"{MAC}_ph") is not None
    assert entry.minor_version == 2


async def test_migration_keeps_user_options(setup_integration):
    """CyA and treatment type are kept: these settings still exist."""
    entry = _legacy_entry()
    await setup_integration(entry)
    assert entry.options[CONF_CYA] == 60
    assert entry.options[CONF_CHLORINE_MODEL] == "bromine"
    assert entry.options[CONF_SYNC_MODE] == "1"


async def test_current_version_entry_is_left_untouched(hass, setup_integration):
    entry = make_entry()
    ent_reg = er.async_get(hass)
    entry.add_to_hass(hass)
    ent_reg.async_get_or_create(
        "sensor", DOMAIN, f"{MAC}_estimated_free_chlorine", config_entry=entry
    )
    await setup_integration(entry)
    # Already on 1.2: no migration, the registry entry is left untouched.
    assert (
        ent_reg.async_get_entity_id("sensor", DOMAIN, f"{MAC}_estimated_free_chlorine")
        is not None
    )


async def test_downgrade_within_same_major_still_loads(setup_integration):
    entry = make_entry(minor_version=5)  # created by a compatible future version
    await setup_integration(entry)
    assert entry.state is ConfigEntryState.LOADED


async def test_future_major_version_is_refused(hass, enable_bluetooth, ble):
    entry = make_entry(version=2)
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.MIGRATION_ERROR


@pytest.mark.parametrize("minor", [0, 1])
async def test_migration_is_idempotent(hass, setup_integration, minor):
    entry = make_entry(minor_version=minor)
    await setup_integration(entry)
    assert entry.minor_version == 2
    # Reloading must not break anything.
    assert await hass.config_entries.async_reload(entry.entry_id)
    assert entry.state is ConfigEntryState.LOADED
