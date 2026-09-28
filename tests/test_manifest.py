"""Consistency of the manifest, the quality scale declaration and the changelogs.

Home Assistant's hassfest does not check quality_scale.yaml for custom
integrations, so these checks keep the Platinum declaration honest.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
INTEGRATION = next((ROOT / "custom_components").iterdir())
MANIFEST = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
RULES = yaml.safe_load((INTEGRATION / "quality_scale.yaml").read_text("utf-8"))["rules"]


def test_manifest_keys_are_sorted_like_hassfest_expects():
    """domain, name, then alphabetical (script/util.py in Home Assistant core)."""
    fixed = {"domain": ".domain", "name": ".name"}
    keys = list(MANIFEST)
    assert keys == sorted(keys, key=lambda k: fixed.get(k, k))


def test_manifest_declares_the_platinum_tier():
    assert MANIFEST["quality_scale"] == "platinum"
    assert MANIFEST["codeowners"]  # required from Silver upwards


def test_every_quality_scale_rule_is_done_or_justified():
    for rule, value in RULES.items():
        status = value if isinstance(value, str) else value.get("status")
        assert status in ("done", "exempt"), f"{rule}: {status}"
        if status == "exempt":
            assert isinstance(value, dict) and value.get("comment"), (
                f"{rule}: an exemption needs a comment"
            )


def test_platinum_rules_are_present():
    for rule in ("async-dependency", "inject-websession", "strict-typing"):
        assert rule in RULES


def test_versions_agree_across_manifest_and_both_changelogs():
    for name in ("CHANGELOG.md", "CHANGELOG.fr.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        first = re.search(r"^## (\d+\.\d+\.\d+)", text, re.MULTILINE)
        assert first and first.group(1) == MANIFEST["version"], name
