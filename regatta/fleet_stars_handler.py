#!/usr/bin/env python3
"""Fleet starred boats backend handler — persistent global store.

Runtime store lifecycle:
  - production path: regatta/fleet_stars.json (ignored by .gitignore)
  - template path: regatta/fleet_stars.example.json (tracked by git, safe empty template)
  - test override: via set_store_path() for test isolation
  - init strategy: if runtime store missing, create from safe empty template
  - preservation: existing runtime store never overwritten or deleted by handler
  - atomic writes: all updates use temp-file + atomic rename
"""
import json
import os
from pathlib import Path
from threading import Lock
from typing import List, Dict, Set

_STORE_PATH_OVERRIDE = None  # For test isolation via set_store_path()
STORE_LOCK = Lock()

def _get_store_path():
    """Get the active store path (production or test override).

    Returns:
        Path: Active store path (test override if set, else production path)
    """
    global _STORE_PATH_OVERRIDE
    if _STORE_PATH_OVERRIDE:
        return Path(_STORE_PATH_OVERRIDE)
    return Path(__file__).parent / "fleet_stars.json"

def _get_template_path():
    """Get the safe empty template path.

    Returns:
        Path: Path to tracked safe empty template
    """
    return Path(__file__).parent / "fleet_stars.example.json"

def set_store_path(path):
    """Override store path for testing (call with None to reset).

    Args:
        path: Test store path as string, or None to reset to production path
    """
    global _STORE_PATH_OVERRIDE
    _STORE_PATH_OVERRIDE = path

def _ensure_store_exists():
    """Ensure runtime store file exists with proper initial structure.

    Lifecycle:
      1. If runtime store exists: preserve it (never overwrite)
      2. If runtime store missing: create it from safe empty template
      3. Template is validated before use (version, starred, metadata)
      4. Existing runtime state is never deleted or rewritten
      5. Test fixtures are never copied into runtime store

    Raises:
        IOError: If template is missing or invalid
        json.JSONDecodeError: If template is not valid JSON
    """
    store_path = _get_store_path()

    # Preserve existing runtime store (never overwrite)
    if store_path.exists():
        return

    # Runtime store missing: create from safe empty template
    template_path = _get_template_path()
    if not template_path.exists():
        raise IOError(f"Template missing: {template_path}")

    # Read and validate template
    with open(template_path, 'r', encoding='utf-8') as f:
        template_data = json.load(f)

    # Validate template structure
    if 'version' not in template_data:
        raise ValueError("Template missing required 'version' field")
    if 'starred' not in template_data:
        raise ValueError("Template missing required 'starred' field")
    if 'metadata' not in template_data:
        raise ValueError("Template missing required 'metadata' field")
    if not isinstance(template_data['starred'], list):
        raise ValueError("Template 'starred' must be a list")

    # Create parent directory if needed
    store_path.parent.mkdir(parents=True, exist_ok=True)

    # Write template to runtime store atomically
    temp_path = store_path.with_suffix('.json.tmp')
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(template_data, f, indent=2)
    temp_path.replace(store_path)

def _read_store() -> Dict:
    """Thread-safe read of starred boats store.

    Returns:
        Dict: Loaded store JSON (version, starred list, metadata)

    Raises:
        json.JSONDecodeError: If store file is corrupted
        IOError: If store file cannot be read
    """
    _ensure_store_exists()
    store_path = _get_store_path()
    with STORE_LOCK:
        with open(store_path, 'r', encoding='utf-8') as f:
            return json.load(f)

def _write_store(data: Dict) -> None:
    """Thread-safe atomic write of starred boats store.

    Uses atomic rename to prevent partial writes:
      1. Write new data to temp file
      2. Atomic rename temp to production store
      3. Lock held throughout to prevent corruption

    Args:
        data: Store JSON to write (version, starred list, metadata)

    Raises:
        json.JSONEncodeError: If data cannot be serialized
        IOError: If write/rename fails
    """
    _ensure_store_exists()
    store_path = _get_store_path()
    with STORE_LOCK:
        # Write to temp, then atomic rename
        temp_path = store_path.with_suffix('.json.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        temp_path.replace(store_path)

def get_starred() -> List[str]:
    """Get all currently starred boat keys.

    Returns:
        List[str]: Sorted list of all currently starred boat identifiers
    """
    store = _read_store()
    return sorted(store.get("starred", []))

def add_starred(boat_key: str) -> bool:
    """Add a boat to starred, return True if added (not duplicate).

    Args:
        boat_key: Boat identifier to star (will be trimmed of whitespace)

    Returns:
        bool: True if boat was added (was not already starred), False if duplicate or invalid
    """
    if not boat_key or not str(boat_key).strip():
        return False

    boat_key = str(boat_key).strip()
    store = _read_store()
    starred = set(store.get("starred", []))

    was_present = boat_key in starred
    starred.add(boat_key)

    store["starred"] = sorted(list(starred))
    _write_store(store)

    return not was_present

def remove_starred(boat_key: str) -> bool:
    """Remove a boat from starred, return True if removed (was present).

    Args:
        boat_key: Boat identifier to unstar (will be trimmed of whitespace)

    Returns:
        bool: True if boat was removed (was starred), False if not starred or invalid
    """
    if not boat_key or not str(boat_key).strip():
        return False

    boat_key = str(boat_key).strip()
    store = _read_store()
    starred = set(store.get("starred", []))

    was_present = boat_key in starred
    starred.discard(boat_key)

    store["starred"] = sorted(list(starred))
    _write_store(store)

    return was_present

def toggle_starred(boat_key: str) -> bool:
    """Toggle starred state, return new state (True = now starred).

    Args:
        boat_key: Boat identifier to toggle (will be trimmed of whitespace)

    Returns:
        bool: New starred state (True = now starred, False = now unstarred)
    """
    if not boat_key or not str(boat_key).strip():
        return False

    boat_key = str(boat_key).strip()
    store = _read_store()
    starred = set(store.get("starred", []))

    if boat_key in starred:
        starred.discard(boat_key)
        result = False
    else:
        starred.add(boat_key)
        result = True

    store["starred"] = sorted(list(starred))
    _write_store(store)

    return result

def merge_starred(local_keys: List[str]) -> List[str]:
    """Merge local browser state with server state by union.

    Called when device comes online with local localStorage favorites.
    Performs union merge: keeps anything starred on server OR local device.
    This ensures no favorites are lost across devices.

    Args:
        local_keys: List of starred boat keys from browser localStorage (may be from offline device)

    Returns:
        List[str]: Merged canonical list from server after merge operation (sorted, deduplicated)
    """
    if not local_keys:
        local_keys = []

    store = _read_store()
    server_set = set(store.get("starred", []))
    local_set = set(str(k).strip() for k in local_keys if k and str(k).strip())

    # Merge by union: keep anything that was starred on server OR client
    merged = server_set | local_set

    store["starred"] = sorted(list(merged))
    _write_store(store)

    return store["starred"]

def is_starred(boat_key: str) -> bool:
    """Check if a boat is currently starred.

    Args:
        boat_key: Boat identifier to check (will be trimmed of whitespace)

    Returns:
        bool: True if boat is currently starred, False otherwise
    """
    if not boat_key or not str(boat_key).strip():
        return False

    boat_key = str(boat_key).strip()
    store = _read_store()
    return boat_key in store.get("starred", [])
