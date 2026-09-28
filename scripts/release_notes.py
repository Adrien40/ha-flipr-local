#!/usr/bin/env python3
"""Build the GitHub release notes of a version from the changelogs.

Usage:
    python3 scripts/release_notes.py 1.2.0 \
        --manifest custom_components/<domain>/manifest.json > release_notes.md

Takes the "## <version>" section of CHANGELOG.md (English) and, when present,
the same section of CHANGELOG.fr.md, folded in a <details> block. Fails (exit
code 1) if the English section is missing or if the version does not match
the one in manifest.json, so a release cannot be published with notes or a
tag that disagree with the code.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def extract_section(changelog: Path, version: str) -> str | None:
    """Return the body of the "## <version>" section, or None if absent."""
    if not changelog.is_file():
        return None
    text = changelog.read_text(encoding="utf-8")
    pattern = rf"(?ms)^##[ \t]+{re.escape(version)}[ \t]*$(.*?)(?=^## |\Z)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("version", help="version without the leading 'v', e.g. 1.2.0")
    parser.add_argument("--changelog", type=Path, default=Path("CHANGELOG.md"))
    parser.add_argument("--changelog-fr", type=Path, default=Path("CHANGELOG.fr.md"))
    parser.add_argument(
        "--manifest",
        type=Path,
        help="manifest.json whose 'version' must equal the released version",
    )
    args = parser.parse_args()
    version = args.version.removeprefix("v")

    if args.manifest is not None:
        manifest_version = json.loads(args.manifest.read_text(encoding="utf-8")).get(
            "version"
        )
        if manifest_version != version:
            print(
                f"Version mismatch: tag is {version} but {args.manifest} "
                f"says {manifest_version}.",
                file=sys.stderr,
            )
            return 1

    english = extract_section(args.changelog, version)
    if not english:
        print(f"No '## {version}' section in {args.changelog}.", file=sys.stderr)
        return 1

    notes = english
    french = extract_section(args.changelog_fr, version)
    if french:
        notes += (
            f"\n\n<details>\n<summary>🇫🇷 Français</summary>\n\n{french}\n\n</details>"
        )
    else:
        print(
            f"Warning: no '## {version}' section in {args.changelog_fr}; "
            "release notes will be English only.",
            file=sys.stderr,
        )

    print(notes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
