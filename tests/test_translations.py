"""Consistency of translation files (no missing or duplicate key)."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

COMPONENT = Path(__file__).parent.parent / "custom_components" / "flipr_local"
STRINGS = COMPONENT / "strings.json"
TRANSLATIONS = sorted((COMPONENT / "translations").glob("*.json"))
ALL_FILES = [STRINGS, *TRANSLATIONS]


def _no_duplicates(pairs):
    keys = [k for k, _ in pairs]
    dupes = {k for k in keys if keys.count(k) > 1}
    if dupes:
        raise ValueError(f"duplicate JSON keys: {sorted(dupes)}")
    return dict(pairs)


def _load(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicates
    )


def _keys(d: dict, prefix: str = "") -> set[str]:
    out: set[str] = set()
    for k, v in d.items():
        out.add(f"{prefix}/{k}")
        if isinstance(v, dict):
            out |= _keys(v, f"{prefix}/{k}")
    return out


def _error_codes_returned_by_validation() -> set[str]:
    """Error codes `return (field, "code")` from validate_calibration (via the AST)."""
    tree = ast.parse((COMPONENT / "validation.py").read_text(encoding="utf-8"))
    func = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "validate_calibration"
    )
    codes = set()
    for node in ast.walk(func):
        if (
            isinstance(node, ast.Return)
            and isinstance(node.value, ast.Tuple)
            and len(node.value.elts) == 2
            and isinstance(node.value.elts[1], ast.Constant)
        ):
            codes.add(node.value.elts[1].value)
    return codes


def test_translation_files_exist():
    assert len(TRANSLATIONS) >= 19
    assert (COMPONENT / "translations" / "en.json").exists()
    assert (COMPONENT / "translations" / "fr.json").exists()


@pytest.mark.parametrize("path", ALL_FILES, ids=lambda p: p.name)
def test_valid_json_without_duplicate_keys(path):
    """A duplicate key silently overwrites the first one (real case: nl, pt-br)."""
    _load(path)


@pytest.mark.parametrize("path", TRANSLATIONS, ids=lambda p: p.name)
def test_same_keys_as_strings_json(path):
    reference = _keys(_load(STRINGS))
    keys = _keys(_load(path))
    assert not reference - keys, f"missing in {path.name}: {sorted(reference - keys)}"
    assert not keys - reference, (
        f"unexpected in {path.name}: {sorted(keys - reference)}"
    )


@pytest.mark.parametrize("path", ALL_FILES, ids=lambda p: p.name)
def test_every_validation_error_is_translated_in_both_flows(path):
    """The options flow had no text for calibration errors."""
    data = _load(path)
    codes = _error_codes_returned_by_validation()
    assert codes, "no error codes found: AST extraction is broken"
    for flow in ("config", "options"):
        missing = codes - set(data[flow]["error"])
        assert not missing, f"{path.name}: {flow}.error lacks {sorted(missing)}"


@pytest.mark.parametrize("path", ALL_FILES, ids=lambda p: p.name)
def test_no_empty_strings(path):
    def walk(node, trail=""):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{trail}/{k}")
        else:
            assert str(node).strip(), f"empty string at {trail}"

    walk(_load(path))


@pytest.mark.parametrize("path", ALL_FILES, ids=lambda p: p.name)
def test_removed_chlorine_sensors_have_no_leftover_strings(path):
    sensors = _load(path)["entity"]["sensor"]
    assert "estimated_free_chlorine" not in sensors
    assert "active_chlorine_hocl" not in sensors


def test_manifest_is_consistent():
    manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["domain"] == COMPONENT.name
    assert manifest["config_flow"] is True
    assert "bluetooth" in manifest["dependencies"]
    parts = manifest["version"].split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_hacs_declares_minimum_home_assistant_version():
    hacs = json.loads(
        (COMPONENT.parent.parent / "hacs.json").read_text(encoding="utf-8")
    )
    assert hacs["homeassistant"] == "2026.3.0"
    assert hacs["render_readme"] is True
