#!/usr/bin/env python3
"""Fleet starred boats backend handler — persistent global store"""
import json
import os
from pathlib import Path
from threading import Lock
from typing import List, Dict, Set

STORE_PATH = Path(__file__).parent / "fleet_stars.json"
STORE_LOCK = Lock()

def _ensure_store_exists():
    """Ensure store file exists with proper initial structure"""
    if not STORE_PATH.exists():
        initial = {"version": "1.0", "starred": [], "metadata": {"created": "2026-09-13T22:56:00Z"}}
        with open(STORE_PATH, 'w') as f:
            json.dump(initial, f, indent=2)

def _read_store() -> Dict:
    """Thread-safe read of starred boats store"""
    _ensure_store_exists()
    with STORE_LOCK:
        with open(STORE_PATH, 'r') as f:
            return json.load(f)

def _write_store(data: Dict) -> None:
    """Thread-safe atomic write of starred boats store"""
    _ensure_store_exists()
    with STORE_LOCK:
        # Write to temp, then atomic rename
        temp_path = STORE_PATH.with_suffix('.json.tmp')
        with open(temp_path, 'w') as f:
            json.dump(data, f, indent=2)
        temp_path.replace(STORE_PATH)

def get_starred() -> List[str]:
    """Get all currently starred boat keys"""
    store = _read_store()
    return sorted(store.get("starred", []))

def add_starred(boat_key: str) -> bool:
    """Add a boat to starred, return True if added (not duplicate)"""
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
    """Remove a boat from starred, return True if removed (was present)"""
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
    """Toggle starred state, return new state (True = now starred)"""
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
    """
    Merge local browser state with server state by union.
    Returns canonical merged list (server state after merge).
    
    Args:
        local_keys: List of starred boat keys from browser localStorage
    
    Returns:
        Merged canonical list from server after merge operation
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
    """Check if a boat is currently starred"""
    if not boat_key or not str(boat_key).strip():
        return False
    
    boat_key = str(boat_key).strip()
    store = _read_store()
    return boat_key in store.get("starred", [])
