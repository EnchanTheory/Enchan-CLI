#!/usr/bin/env python3
"""Validate that every Web UI locale has the same keys as en.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def load_json(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def main() -> int:
    locale_dir = Path(__file__).with_name("locales")
    reference_path = locale_dir / "en.json"
    reference = load_json(reference_path)
    reference_keys = set(reference)
    failed = False

    for path in sorted(locale_dir.glob("*.json")):
        if path == reference_path:
            continue
        locale = load_json(path)
        keys = set(locale)
        missing = sorted(reference_keys - keys)
        extra = sorted(keys - reference_keys)
        if missing or extra:
            failed = True
            print(f"{path.name} does not match en.json", file=sys.stderr)
            if missing:
                print("  missing: " + ", ".join(missing), file=sys.stderr)
            if extra:
                print("  extra: " + ", ".join(extra), file=sys.stderr)

    if failed:
        return 1
    print(f"Locale key validation passed ({len(reference_keys)} keys).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
