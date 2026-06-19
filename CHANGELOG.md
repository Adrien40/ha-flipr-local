# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Continuous-integration workflow running the test suite with pytest on every
  push and pull request (`.github/workflows/test.yaml`).
- `requirements_test.txt` declaring the test dependencies, including the
  Home Assistant Bluetooth/USB stack pulled in when importing the integration.
- `pytest.ini` with the test path and asyncio configuration.
- `.gitignore` covering Python, pytest, ruff, virtualenv and editor artifacts.

### Fixed
- Repaired the chemistry test suite, which referenced functions removed during
  an earlier refactor (`compute_active_chlorine`, `compute_flipr_active_chlorine`,
  `compute_flipr_theoretical_orp`) and failed to import. Tests now cover the
  current API (`estimate_free_chlorine`, `compute_active_chlorine_from_fc`,
  `compute_isl`, `compute_ph_equilibrium`, `get_mv_from_input`).
- Synchronised `manifest.json` version with the latest release tag (was still
  `1.0.0` after the 1.1.0 release).

## [1.1.0] - 2026-05-12

### Added
- Bluetooth discovery matchers for additional Flipr local names
  (`F2B*` and `F30*`–`F3F*`), broadening automatic device detection.

### Changed
- Refactored inline comments and improved code clarity.
- Documentation updates (`README.md`, `README.fr.md`).

## [1.0.0] - 2026-04-19

### Added
- Initial release: local (BLE) integration for Flipr pool analysers, with
  temperature, pH, ORP, estimated free chlorine, active chlorine (HOCl),
  Langelier saturation index, battery and Bluetooth diagnostics.
- Configurable pH/ORP calibration, temperature offset, water parameters
  (TAC, TH, TDS, CyA) and alert thresholds via the options flow.
- Chlorine/bromine model selection, sync-mode control and gateway mode.

[Unreleased]: https://github.com/Adrien40/ha-flipr-local/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/Adrien40/ha-flipr-local/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Adrien40/ha-flipr-local/releases/tag/v1.0.0
