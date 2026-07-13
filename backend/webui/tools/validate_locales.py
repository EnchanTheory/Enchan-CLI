#!/usr/bin/env python3
"""Validate the Web UI locale manifest and message catalogs."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


PLACEHOLDER_PATTERN = re.compile(r"\{[a-zA-Z][a-zA-Z0-9_]*\}")


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    locale_dir = Path(__file__).parents[1] / "locales"
    manifest = load_json(locale_dir / "manifest.json")
    entries = manifest.get("locales", []) if isinstance(manifest, dict) else []
    if not entries:
        print("manifest.json must define at least one locale", file=sys.stderr)
        return 1

    codes = [entry.get("code") for entry in entries]
    files = [entry.get("file") for entry in entries]
    if len(set(codes)) != len(codes) or len(set(files)) != len(files):
        print("Locale codes and files must be unique", file=sys.stderr)
        return 1
    if manifest.get("default") not in codes:
        print("The default locale must be listed in manifest.json", file=sys.stderr)
        return 1

    default_entry = next(entry for entry in entries if entry["code"] == manifest["default"])
    reference_path = locale_dir / default_entry["file"]
    reference = load_json(reference_path)
    if not isinstance(reference, dict):
        print(f"{reference_path.name} must contain a JSON object", file=sys.stderr)
        return 1
    reference_keys = set(reference)
    failed = False

    for entry in entries:
        if not all(isinstance(entry.get(key), str) and entry[key] for key in ("code", "label", "file")):
            print("Every locale needs code, label, and file strings", file=sys.stderr)
            failed = True
            continue
        path = locale_dir / entry["file"]
        if not path.is_file():
            print(f"Missing locale file: {path.name}", file=sys.stderr)
            failed = True
            continue
        locale = load_json(path)
        if not isinstance(locale, dict):
            print(f"{path.name} must contain a JSON object", file=sys.stderr)
            failed = True
            continue
        missing = sorted(reference_keys - set(locale))
        extra = sorted(set(locale) - reference_keys)
        if missing or extra:
            failed = True
            print(f"{path.name} does not match {reference_path.name}", file=sys.stderr)
            if missing:
                print("  missing: " + ", ".join(missing), file=sys.stderr)
            if extra:
                print("  extra: " + ", ".join(extra), file=sys.stderr)
        for key in sorted(reference_keys & set(locale)):
            expected = set(PLACEHOLDER_PATTERN.findall(str(reference[key])))
            actual = set(PLACEHOLDER_PATTERN.findall(str(locale[key])))
            if actual != expected:
                failed = True
                print(
                    f"{path.name}: placeholder mismatch for {key} "
                    f"(expected {sorted(expected)}, got {sorted(actual)})",
                    file=sys.stderr,
                )

    listed = {entry.get("file") for entry in entries}
    unlisted = sorted(path.name for path in locale_dir.glob("*.json") if path.name != "manifest.json" and path.name not in listed)
    if unlisted:
        failed = True
        print("Unlisted locale files: " + ", ".join(unlisted), file=sys.stderr)

    if failed:
        return 1
    print(f"Locale validation passed ({len(entries)} locales, {len(reference_keys)} keys).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
