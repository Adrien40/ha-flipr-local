# Flipr Local - Changelog

## 1.2.1

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

### 🧰 Maintenance
- The manifest now declares the `platinum` quality scale (`quality_scale.yaml` already documented every rule). New tests keep the manifest, the quality scale file and the changelogs consistent.
- Tests: the two scheduling tests no longer depend on the time of day (they could fail at random when a slot was less than 10 seconds away); 8 more tests (508 in total), `config_flow.py` fully covered.
- Comments and docstrings in the repository are now in English.

### 📚 Documentation
- README: the CI badges now point to the real repository.

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

## 1.2.0

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

This release brings analyses scheduled on fixed time slots, a **Raw ORP** diagnostic sensor and a much more solid foundation: strict typing, a modular code base and a test suite of over 450 tests.

It also removes the estimated chlorine sensors, which could not be made reliable. See the breaking changes below.

### 🚨 Breaking changes
- **Home Assistant 2026.3.0 or newer** (`hacs.json`), the first release running on Python 3.14.
- Sensors **Estimated Free Chlorine** and **Active Chlorine (HOCl)**:
  - ORP (mV) reflects oxidising capacity, not concentration (ppm); the formula capped at 415 mV and reported false positive chlorine readings below that point.
  - Stabilizer (CyA) multipliers were arbitrary and unvalidated.
  - Monitor ORP against your **Alert Thresholds** and use a test kit for actual chlorine concentration.

### ✨ New features
- **Raw ORP (mV)** diagnostic sensor to calibrate the probe against a reference solution before offset application.
- Scheduled analyses aligned to fixed time slots (**Analysis Interval** + **Reference Time**) instead of a rolling interval.
- **Reference Time** entity (default 08:00) and updated **Analysis Interval**, both configurable from the new **Synchronization** options section.
- Enriched `DeviceInfo`: Bluetooth MAC connection and serial number from the advertisement name (e.g. `F3A12BC`, fallback to MAC).
- Automatic cleanup of the two retired chlorine entities during config entry migration (1.1 → 1.2), so they do not stay *unavailable* forever.

### 🚀 Enhancements
- Diagnostic sensors disabled by default: **Raw pH (mV)**, **Raw ORP (mV)**, **Raw Factory pH**, **Battery Voltage (mV)**, and **Raw Hex Frame** (can be enabled manually).
- Bluetooth signal sensor (**Bluetooth Signal** / RSSI): becomes *unavailable* when out of range instead of holding its last value.
- **New Analysis** button: attempts connection even without a recent advertisement and consumes the request immediately.
- Code quality: enforced strict typing (`mypy --strict`) and CI test coverage > 95%.
- Resuming **Automatic Analyses** no longer forces an immediate analysis: the next one runs at the next scheduled slot (use **New Analysis** to measure right away).

### 🐛 Bug fixes
- Added a 10s timeout (`TIMEOUT_GATT_OP`) on `start_notify`, `stop_notify`, `disconnect`, and Start Max direct read.
- BLE notification queue overflow handling moved to properly catch `QueueFull`.
- Fixed infinite retry loop on invalid frames by preserving the retry counter.
- Preserved CyA value when updating unrelated settings in options flow.
- Completed coordinator `async_shutdown` to properly cancel background tasks.
- Added missing calibration translations and removed duplicate keys in `nl.json` and `pt-br.json`.
- Handled non-numeric inputs gracefully in `validate_calibration`.
- Prevented restored startup data from reinjecting legacy chlorine values.
- Reset `is_connected` state between cycles in BLE unit tests.

### 🛡️ Hardening
- Degenerate pH calibrations (flat slope) fall back to factory defaults instead of stalling.
- Calculated pH values outside 0–14 report as *unknown*.
- Rejection of NaN and infinite inputs for **Langelier Saturation Index** and **Equilibrium pH**.

### 🧰 Maintenance
- Modular architecture: `coordinator.py`, `frame.py`, `model.py`, `validation.py`, `chemistry.py`.
- Test suite completely overhauled (> 450 unit and property-based tests).
- CI workflow: automated pytest, coverage checks, and Ruff linting for Python 3.14.

### 📚 Documentation
- `README.md` / `README.fr.md`: documented chlorine removal, **Raw ORP**, use cases, and limitations.
- `calibration_help.md` / `calibration_help.fr.md`: dual-language guide, ORP offset instructions, and diagnostic entity activation notes.

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

## 1.1.0

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

### ✨ New features
- Support for Flipr Start Max model.

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

## 1.0.0

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

### ✨ New features
- Initial official stable release.

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬
