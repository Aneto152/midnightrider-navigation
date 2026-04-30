#!/usr/bin/env python3
"""
json_utils.py — Midnight Rider Navigation

Utility for safe JSON file manipulation.

ABSOLUTE RULE: Never use sed/awk/grep for JSON modifications.
Always use this script or equivalent Python code.

Why Python and not sed/bash?
 - Python validates JSON structure before and after modification
 - Correct handling of special characters and escaping
 - No silent corruption (script fails rather than corrupts)
 - Readable and maintainable

Usage:
 python3 scripts/json_utils.py get FILE KEY
 python3 scripts/json_utils.py set FILE KEY VALUE
 python3 scripts/json_utils.py delete FILE KEY
 python3 scripts/json_utils.py validate FILE
 python3 scripts/json_utils.py pretty FILE
 python3 scripts/json_utils.py patch FILE PATCH_FILE
 python3 scripts/json_utils.py count FILE KEY

Examples:
 python3 scripts/json_utils.py validate grafana-dashboards/cockpit.json
 python3 scripts/json_utils.py get grafana-dashboards/cockpit.json title
 python3 scripts/json_utils.py set grafana-dashboards/cockpit.json title "COCKPIT v2"
 python3 scripts/json_utils.py count grafana-dashboards/cockpit.json panels

Author: OC (Open Claw) — Midnight Rider Navigation
License: MIT
"""

import json
import sys
import os
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Union


# ─── Core helpers ─────────────────────────────────────────────────────────────

def load_json(filepath: str) -> Union[Dict, List]:
    """Load and validate a JSON file. Raises ValueError if invalid."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {filepath}: {e}")


def save_json(filepath: str, data: Union[Dict, List], indent: int = 2) -> None:
    """Save JSON with automatic backup of original file."""
    path = Path(filepath)

    # Create backup before overwriting
    if path.exists():
        backup = path.with_suffix(f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        shutil.copy2(path, backup)
        backup_path = backup
    else:
        backup_path = None

    # Write new content
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.write("\n")

        # Validate what was written
        with open(path, "r", encoding="utf-8") as f:
            json.load(f)

        # Cleanup: remove backup if write was successful
        if backup_path and backup_path.exists():
            backup_path.unlink()

        print(f"✅ Saved: {filepath}")

    except Exception as e:
        # Restore backup if write failed
        if backup_path and backup_path.exists():
            shutil.copy2(backup_path, path)
            print(f"⚠️  Write failed, restored backup: {backup_path}", file=sys.stderr)
        raise ValueError(f"Failed to save {filepath}: {e}")


def get_nested(data: Union[Dict, List], key_path: str) -> Any:
    """Get a value using dot notation. e.g. 'dashboard.panels' or 'panels[0].title'"""
    keys = key_path.split(".")
    current = data

    for key in keys:
        if "[" in key and "]" in key:
            # Handle array index notation: panels[0]
            base_key = key.split("[")[0]
            index_str = key.split("[")[1].rstrip("]")
            try:
                index = int(index_str)
                if isinstance(current, dict) and base_key in current:
                    current = current[base_key]
                    if isinstance(current, (list, tuple)) and 0 <= index < len(current):
                        current = current[index]
                    else:
                        return None
                else:
                    return None
            except (ValueError, IndexError, TypeError):
                return None
        else:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None

    return current


def set_nested(data: Dict, key_path: str, value: Any) -> Dict:
    """Set a value using dot notation. Creates intermediate dicts if needed."""
    keys = key_path.split(".")
    current = data

    # Navigate to the parent of the target key
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
        if not isinstance(current, dict):
            raise ValueError(f"Cannot navigate through non-dict at key: {key}")

    # Set the final key
    current[keys[-1]] = value
    return data


def delete_nested(data: Dict, key_path: str) -> Dict:
    """Delete a value using dot notation."""
    keys = key_path.split(".")
    current = data

    # Navigate to parent
    for key in keys[:-1]:
        if key in current:
            current = current[key]
        else:
            return data  # Path doesn't exist, nothing to delete

    # Delete final key
    if isinstance(current, dict) and keys[-1] in current:
        del current[keys[-1]]

    return data


def count_items(data: Union[Dict, List], key: str) -> int:
    """Count items in a list at given key path."""
    value = get_nested(data, key)
    if isinstance(value, (list, tuple)):
        return len(value)
    elif isinstance(value, dict):
        return len(value)
    else:
        return 0 if value is None else 1


# ─── Commands ──────────────────────────────────────────────────────────────────

def cmd_get(args):
    """Get a value from JSON file."""
    data = load_json(args.file)
    value = get_nested(data, args.key)

    if value is None:
        print(f"⚠️  Key not found: {args.key}", file=sys.stderr)
        sys.exit(1)

    if isinstance(value, (dict, list)):
        print(json.dumps(value, indent=2, ensure_ascii=False))
    else:
        print(value)


def cmd_set(args):
    """Set a value in JSON file."""
    data = load_json(args.file)

    # Try to parse value as JSON first, otherwise treat as string
    try:
        value = json.loads(args.value)
    except json.JSONDecodeError:
        value = args.value

    set_nested(data, args.key, value)
    save_json(args.file, data)


def cmd_delete(args):
    """Delete a key from JSON file."""
    data = load_json(args.file)
    delete_nested(data, args.key)
    save_json(args.file, data)


def cmd_validate(args):
    """Validate JSON file syntax."""
    try:
        load_json(args.file)
        print(f"✅ Valid JSON: {args.file}")
    except Exception as e:
        print(f"❌ Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_pretty(args):
    """Pretty-print JSON file with formatting."""
    data = load_json(args.file)
    indent = args.indent if hasattr(args, 'indent') else 2
    save_json(args.file, data, indent=indent)
    print(f"✅ Formatted: {args.file}")


def cmd_patch(args):
    """Apply JSON patch file to target."""
    target = load_json(args.file)
    patch = load_json(args.patch_file)

    if not isinstance(patch, dict):
        raise ValueError("Patch file must contain JSON object")

    # Simple merge: patch overwrites target values
    def merge(base: dict, updates: dict) -> dict:
        for key, value in updates.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                merge(base[key], value)
            else:
                base[key] = value
        return base

    merge(target, patch)
    save_json(args.file, target)


def cmd_count(args):
    """Count items in a list at given key."""
    data = load_json(args.file)
    count = count_items(data, args.key)
    print(f"{args.key}: {count} items")


def cmd_list_keys(args):
    """List all top-level keys in JSON file."""
    data = load_json(args.file)

    if isinstance(data, dict):
        for key in sorted(data.keys()):
            print(f"  {key}")
    elif isinstance(data, list):
        print(f"  (array with {len(data)} items)")
    else:
        print(f"  (scalar value)")


def cmd_info(args):
    """Show info about JSON file."""
    data = load_json(args.file)
    path = Path(args.file)

    print(f"File: {path}")
    print(f"Size: {path.stat().st_size} bytes")
    print(f"Type: {'object' if isinstance(data, dict) else 'array' if isinstance(data, list) else 'scalar'}")

    if isinstance(data, dict):
        print(f"Keys: {len(data)}")
        for key in sorted(data.keys())[:10]:
            val = data[key]
            val_type = type(val).__name__
            if isinstance(val, (dict, list)):
                size = len(val)
                print(f"  - {key}: {val_type} ({size} items)")
            else:
                print(f"  - {key}: {val_type}")
    elif isinstance(data, list):
        print(f"Items: {len(data)}")
        if data and isinstance(data[0], dict):
            print(f"  First item keys: {', '.join(sorted(data[0].keys())[:5])}")


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Safe JSON file manipulation utility for Midnight Rider",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/json_utils.py validate grafana-dashboards/cockpit.json
  python3 scripts/json_utils.py get grafana-dashboards/cockpit.json title
  python3 scripts/json_utils.py set grafana-dashboards/cockpit.json title "COCKPIT v2"
  python3 scripts/json_utils.py delete grafana-dashboards/cockpit.json temp_key
  python3 scripts/json_utils.py count grafana-dashboards/cockpit.json panels
  python3 scripts/json_utils.py pretty grafana-dashboards/cockpit.json
  python3 scripts/json_utils.py patch config.json patch.json
  python3 scripts/json_utils.py info grafana-dashboards/cockpit.json
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # get
    get_parser = subparsers.add_parser("get", help="Get a value from JSON")
    get_parser.add_argument("file", help="JSON file path")
    get_parser.add_argument("key", help="Key path (dot notation: dashboard.panels[0].title)")
    get_parser.set_defaults(func=cmd_get)

    # set
    set_parser = subparsers.add_parser("set", help="Set a value in JSON")
    set_parser.add_argument("file", help="JSON file path")
    set_parser.add_argument("key", help="Key path (dot notation)")
    set_parser.add_argument("value", help="New value (JSON or string)")
    set_parser.set_defaults(func=cmd_set)

    # delete
    delete_parser = subparsers.add_parser("delete", help="Delete a key from JSON")
    delete_parser.add_argument("file", help="JSON file path")
    delete_parser.add_argument("key", help="Key path (dot notation)")
    delete_parser.set_defaults(func=cmd_delete)

    # validate
    validate_parser = subparsers.add_parser("validate", help="Validate JSON syntax")
    validate_parser.add_argument("file", help="JSON file path")
    validate_parser.set_defaults(func=cmd_validate)

    # pretty
    pretty_parser = subparsers.add_parser("pretty", help="Pretty-print JSON")
    pretty_parser.add_argument("file", help="JSON file path")
    pretty_parser.add_argument("--indent", type=int, default=2, help="Indentation level (default: 2)")
    pretty_parser.set_defaults(func=cmd_pretty)

    # patch
    patch_parser = subparsers.add_parser("patch", help="Apply JSON patch")
    patch_parser.add_argument("file", help="Target JSON file")
    patch_parser.add_argument("patch_file", help="Patch JSON file")
    patch_parser.set_defaults(func=cmd_patch)

    # count
    count_parser = subparsers.add_parser("count", help="Count items in array")
    count_parser.add_argument("file", help="JSON file path")
    count_parser.add_argument("key", help="Key path to array")
    count_parser.set_defaults(func=cmd_count)

    # list
    list_parser = subparsers.add_parser("list", help="List top-level keys")
    list_parser.add_argument("file", help="JSON file path")
    list_parser.set_defaults(func=cmd_list_keys)

    # info
    info_parser = subparsers.add_parser("info", help="Show JSON file info")
    info_parser.add_argument("file", help="JSON file path")
    info_parser.set_defaults(func=cmd_info)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    try:
        args.func(args)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
