"""Shared fixtures: simulated Bluetooth, config entry, coordinator."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from dataclasses import dataclass, field
from time import monotonic
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from bleak.backends.device import BLEDevice
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.flipr_local.const import (
    CONF_MAC_ADDRESS,
    CONF_SYNC_MODE,
    CONF_USE_GATEWAY,
    DOMAIN,
)
from custom_components.flipr_local.coordinator import FliprDataCoordinator

from .helpers import MAC, FakeBleakClient, build_frame

pytest_plugins = "pytest_homeassistant_custom_component"

PKG = "custom_components.flipr_local"


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Allow HA to load custom_components/ during the tests."""


@dataclass
class BleEnv:
    """Controllable state of simulated Bluetooth (adverts, device, GATT client)."""

    client: FakeBleakClient = field(default_factory=lambda: FakeBleakClient())
    device_name: str = "Flipr 12345"
    scanner_count: int = 1
    # Age (s) of the last advertisement received; None = never seen.
    last_seen_age: float | None = 0.0
    device_present: bool = True
    rssi: int = -60
    establish: AsyncMock = field(default_factory=AsyncMock)

    def device(self) -> BLEDevice | None:
        if not self.device_present:
            return None
        return BLEDevice(MAC, self.device_name, {})

    def service_info(self) -> SimpleNamespace | None:
        if self.last_seen_age is None:
            return None
        return SimpleNamespace(time=monotonic() - self.last_seen_age, rssi=self.rssi)


@pytest.fixture
def ble(monkeypatch: pytest.MonkeyPatch) -> Generator[BleEnv]:
    """Simulated Bluetooth: a client that returns a valid frame per write."""
    env = BleEnv(client=FakeBleakClient(frames=[build_frame()]))

    async def _establish(*_args, **_kwargs):
        return env.client

    env.establish.side_effect = _establish

    with (
        patch(
            f"{PKG}.coordinator.async_ble_device_from_address",
            lambda *a, **k: env.device(),
        ),
        patch(
            f"{PKG}.coordinator.async_last_service_info",
            lambda *a, **k: env.service_info(),
        ),
        patch(
            f"{PKG}.coordinator.async_scanner_count", lambda *a, **k: env.scanner_count
        ),
        patch(
            f"{PKG}.sensor.async_last_service_info", lambda *a, **k: env.service_info()
        ),
        patch(f"{PKG}.coordinator.establish_connection", env.establish),
    ):
        # Short cycles: tests should never actually wait 60 s.
        monkeypatch.setattr(f"{PKG}.coordinator.NOTIFY_WAIT_TIMEOUT", 0.2)
        monkeypatch.setattr(f"{PKG}.coordinator.GATT_WRITE_TIMEOUT", 0.2)
        monkeypatch.setattr(f"{PKG}.coordinator.GATT_WRITE_RETRY_DELAY", 0.0)
        monkeypatch.setattr(f"{PKG}.coordinator.START_MAX_SILENT_WAIT", 0.0)
        monkeypatch.setattr(f"{PKG}.coordinator.START_MAX_READ_RETRY_WAIT", 0.0)
        monkeypatch.setattr(f"{PKG}.coordinator.TIMEOUT_GATT_OP", 0.05)
        yield env


def make_entry(
    *, version: int = 1, minor_version: int = 2, **options
) -> MockConfigEntry:
    """Flipr entry (version 1.2); `options` completes/overrides the options."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=MAC,
        title="Flipr AnalysR 3",
        version=version,
        minor_version=minor_version,
        data={CONF_MAC_ADDRESS: MAC, "model": "Flipr AnalysR 3"},
        options={CONF_USE_GATEWAY: False, CONF_SYNC_MODE: "1", **options},
    )


@pytest.fixture
def entry() -> MockConfigEntry:
    return make_entry()


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant, enable_bluetooth: None, ble: BleEnv
) -> AsyncGenerator[Callable[..., Awaitable[FliprDataCoordinator]]]:
    """Factory: sets up the entry, waits for the first BLE cycle, unloads at the end."""
    entries: list[MockConfigEntry] = []

    async def _setup(config_entry: MockConfigEntry) -> FliprDataCoordinator:
        config_entry.add_to_hass(hass)
        entries.append(config_entry)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)
        return config_entry.runtime_data

    yield _setup

    for config_entry in entries:
        if config_entry.state is ConfigEntryState.LOADED:
            await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()


@pytest.fixture
async def coordinator(
    entry: MockConfigEntry, setup_integration
) -> FliprDataCoordinator:
    """Coordinator after a successful first cycle (unloaded by setup_integration)."""
    return await setup_integration(entry)


def entity_id(hass: HomeAssistant, domain: str, key: str) -> str:
    """entity_id of a Flipr entity, found by its unique_id."""
    found = er.async_get(hass).async_get_entity_id(domain, DOMAIN, f"{MAC}_{key}")
    assert found is not None, f"no {domain} entity with unique_id {MAC}_{key}"
    return found


def enable_disabled_by_default(hass: HomeAssistant, domain: str, key: str) -> None:
    """Pre-register a normally-disabled-by-default entity as enabled.

    Must be called with the config entry already added to hass but BEFORE
    the integration is set up, so the platform sees an existing, enabled
    registry entry instead of creating a fresh (disabled) one.
    """
    er.async_get(hass).async_get_or_create(
        domain,
        DOMAIN,
        f"{MAC}_{key}",
        disabled_by=None,
    )
