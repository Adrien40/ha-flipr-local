# Blue Connect Local - Changelog

## 1.2.0

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

This release is all about robustness: Bluetooth retry, shutdown and re-authentication issues are fixed, a **Raw ORP** diagnostic sensor joins the raw pH one, and the test suite grew from 40 to ~400 tests.

### 🚨 Breaking changes
- **Home Assistant 2026.3.0 or newer** (`hacs.json`), the first release shipped with Python 3.14. Tests pass on 2026.3.0 and 2026.9.4.

### ✨ New features
- **Raw ORP** diagnostic sensor (mV), next to the existing raw pH: the probe value *before* any
  offset, to calibrate on a reference solution.

### 🧂 Note on chlorine
- No chlorine estimate, on purpose: ORP is an oxidising strength, not a concentration, so a chlorine value derived from it would look precise but be wrong. The **CyA** entity and the **treatment type** are kept, but no calculated value depends on them yet.

### 🐛 Bug fixes
- **Re-authentication and reconfiguration ignored the new access code**: the options (which take priority) and a copy in local storage kept the old one, so the repair prompt came back. The new code is now used, is no longer stored in local storage, and re-authentication validates its format (9 alphanumeric characters).
- The **Analysis Interval** and **CyA (Stabilizer)** entities kept showing their old value after a change in **Configure**, although the new value was already in use; they now follow the value actually used.
- Invalid BLE frames were retried forever: the retry counter was reset before decoding, so the "unreachable" state was never reached.
- Coordinator shutdown: `async_shutdown` now calls the parent implementation and is idempotent, and the first analysis timer (2 s after startup) is cancelled on unload.
- `validate_calibration` no longer raises on a non-numeric ORP, offset, CyA or interval value.
- A degenerate pH calibration (points too close together) no longer returns a silently wrong value: the pH falls back to the raw pH with a logged warning.
- A device seen only by a scanner that cannot connect to it (`connectable=False`) is no longer treated as missing.
- The **New Analysis** button handles any unexpected error cleanly instead of leaving an unhandled background-task traceback.
- Dropped notifications (queue full) and BLE signal lost/found events are now logged at debug level.

### 🛡️ Hardening
- A computed pH outside 0-14 becomes *unknown* instead of being displayed.
- Langelier index and equilibrium pH reject NaN/inf inputs.

### 🧰 Maintenance
- The coordinator receives its `config_entry` explicitly; BLE pauses are named constants; a compatibility helper replaces the deprecated `device_registry.async_get_device`, so the code works on both 2026.3.0 and 2026.9.4.
- Test suite grown from 40 to ~400 tests, with 100 % coverage: simulated Bluetooth, coordinator, config/options flow, migration chain 1.1 → 1.4, entities, translations, property-based tests.
- CI: pytest + coverage workflow (Python 3.14, 95 % minimum), `mypy --strict` as its own *Typing* workflow, explicit ruff / pytest configuration in `pyproject.toml`, `requirements_test.txt`.
- Code style (ruff) and Python 3.14 syntax: `TimeoutError`, `except A, B:`.
- The manifest declares the `platinum` quality scale, with tests keeping it consistent.

### 📚 Documentation
- `README.md` / `README.fr.md`: minimum Home Assistant version, raw ORP, new *Scheduled Analyses* section, missing entities in the table, and license / CI / quality scale badges.
- `calibration_help.md` / `calibration_help.fr.md`: proper English version of the guide, language links, and link from the README.

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

## 1.1.1

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

### ✨ New features
- **Instant invalid access code detection**: the auth status is read directly from the probe, so *Invalid access code* is reported within seconds instead of after the ~2×60 s timeout (with a 0.5 s confirmation re-read to avoid false positives on high-latency BLE proxies). New `auth_failed` state on the Bluetooth Status sensor.
- **Blue Connect Silver**: the Conductivity/Salinity entities are automatically disabled (once) when the Silver model is detected, instead of staying enabled and showing *Unknown*.
- Model detection as early as Bluetooth discovery: conductivity detected during discovery is persisted, so the Conductivity/Salinity entities get the right enabled-by-default state from their creation.

### 🐛 Bug fixes
- Editing an existing access code in the Options menu (e.g. fixing a typo) now triggers an immediate analysis; before, only going from an empty field to a code did.
- The legacy `hw_version` is explicitly cleared from the device registry when upgrading from 1.1.0, which removes the redundant "Hardware: WA000100" line from the device page.

### 🧰 Maintenance
- Device registry: the SKU is now exposed as `model_id` (*Model ID*) instead of `hw_version`; the `sw_version` diagnostic sensor, which reported the device's Cloud ID and not a firmware version, is renamed `cloud_id` (registry migration keeps the entity history).
- Orphaned *Serial Number* / *Model (SKU)* sensor entities (already folded into the device header in 1.1.0) are cleaned up from the entity registry (config entry migration 2 → 4).
- English strings harmonised to the singular (*Automatic Analysis*, *Analysis paused*).
- Removed 3 dead constants and an unused import.

### 🙏 Acknowledgements
- Thanks to @alexdelprete for his help, suggestions and testing.

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

## 1.1.0

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

### ✨ New features
- Automatic model detection (Blue Connect **Gold** or **Silver**): in active mode from the hardware SKU and in fully passive mode by analysing the BLE frame. The detected model is shown from the setup screen, right at Bluetooth discovery.
- Conductivity and Salinity entities are disabled by default on Blue Connect Silver.
- Enriched device info in the device header: detected model, model number (SKU), serial number and Bluetooth MAC address.

### 🐛 Bug fixes
- Serial number and SKU restored from local storage are injected as soon as the entities are created, with no wait for the first BLE reading.
- The `0xFFFF` hardware marker is now handled when decoding frames, which removes wrong salinity values on devices without a conductivity probe.

### 🧰 Maintenance
- Centralised raw BLE frame extraction (`extract_raw_payload`), removed the redundant *Model Number (SKU)* and *Serial Number* sensors and dead code, and strengthened the unit tests.

### 📋 Upgrade notes
- After updating from 1.0.3, the former *Model Number (SKU)* and *Serial Number* sensors appear as unavailable: open the entity > gear icon > **Delete** (1.1.1 cleans them up automatically).
- Blue Connect Silver: a Conductivity entity that was already active stays visible and shows *Unknown*; disable or hide it under **Settings** > **Devices & Services** > **Entities** (1.1.1 does it automatically).

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

## 1.0.3

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

### ✨ New features
- Automatic **Blue Connect Silver** detection, based on the BLE name prefix `BC3-QX25001952`.

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

## 1.0.2

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

### 🐛 Bug fixes
- Hotfix: the version number in `manifest.json` had been overlooked in 1.0.1; HACS and Home Assistant now display the right version. No other code change.

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

## 1.0.1

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

### 🧰 Maintenance
- Under-the-hood release, no visible feature.
- Architecture refactoring: pure logic extracted from the coordinator into dedicated modules (`protocol.py`, `model.py`, `validation.py`).
- Added a pytest suite with no Home Assistant dependency: water chemistry (LSI, equilibrium pH), BLE frame decoding (18 and 19 bytes) and config flow validation.
- CI: a GitHub Actions workflow (`tests.yaml`) runs the tests on every change.
- Removed dead code (unreachable conditions) in the calibration validation.

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

## 1.0.0

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

### ✨ New features
- First stable release.

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬
