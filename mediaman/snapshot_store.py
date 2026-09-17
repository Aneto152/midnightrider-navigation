"""
SnapshotStore - persist the last CollectionResult across one-shot runs.

WHY THIS EXISTS
---------------
EventDetector.detect_events(current, previous, observed_at) compares two
collection runs. MediaMan is designed to run one-shot under a systemd timer,
so `previous` does not survive in memory between executions.

Without persistence the detector receives previous=None on every run and, by
its own documented contract, emits no transition events at all. The whole
event pipeline would stay silent for ever while every component reported
itself healthy - a green system that measures nothing, which is exactly the
failure mode this project has been correcting all week.

GUARANTEES
----------
- No environment variables are read: the database path is injected.
- Serialization delegates to CollectionResult.to_dict(), the collector's own
  contract, so this module never invents a format.
- Rehydration is a strict inverse: unknown or missing keys raise instead of
  being silently dropped. A snapshot that cannot be trusted is not returned.
- Exactly one row is kept. Storage is bounded whatever the run count.
- No network, no credentials. Only counts and field names are logged.
"""

import json
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from .mcp_collector import (
    CollectionResult,
    CollectionStatus,
    NavigationFact,
    Provenance,
)

SNAPSHOT_SCHEMA_VERSION = 1

_PROVENANCE_KEYS = {
    "tool_public_id", "server_name", "wire_tool_name", "source_id",
    "source_timestamp", "observed_at", "freshness_limit_seconds",
    "validation_status", "warnings",
}
_FACT_KEYS = {"field_name", "value", "unit", "provenance"}
_RESULT_KEYS = {
    "status", "race_id", "facts", "tools_attempted", "tools_succeeded",
    "tools_failed", "collection_start_at", "collection_end_at",
    "errors", "warnings",
}


class SnapshotDecodeError(ValueError):
    """A stored snapshot does not match the CollectionResult contract."""


def _require_exact_keys(data: Dict[str, Any], expected: set, what: str) -> None:
    if not isinstance(data, dict):
        raise SnapshotDecodeError(f"{what}: expected an object, got {type(data).__name__}")
    unknown = set(data) - expected
    missing = expected - set(data)
    if unknown:
        raise SnapshotDecodeError(f"{what}: unknown key(s) {sorted(unknown)}")
    if missing:
        raise SnapshotDecodeError(f"{what}: missing key(s) {sorted(missing)}")


def deserialize_collection_result(data: Dict[str, Any]) -> CollectionResult:
    """
    Exact inverse of CollectionResult.to_dict().

    Raises SnapshotDecodeError on any shape mismatch. Refusing a doubtful
    snapshot is safer than feeding the detector a half-built object: a
    missing previous state produces no events, a wrong one produces false
    events.
    """
    _require_exact_keys(data, _RESULT_KEYS, "snapshot")

    try:
        status = CollectionStatus(data["status"])
    except ValueError as exc:
        raise SnapshotDecodeError(f"snapshot: unknown status {data['status']!r}") from exc

    facts: List[NavigationFact] = []
    for index, raw_fact in enumerate(data["facts"]):
        _require_exact_keys(raw_fact, _FACT_KEYS, f"snapshot.facts[{index}]")
        raw_prov = raw_fact["provenance"]
        _require_exact_keys(raw_prov, _PROVENANCE_KEYS, f"snapshot.facts[{index}].provenance")
        facts.append(
            NavigationFact(
                field_name=raw_fact["field_name"],
                value=raw_fact["value"],
                unit=raw_fact["unit"],
                provenance=Provenance(**raw_prov),
            )
        )

    return CollectionResult(
        status=status,
        race_id=data["race_id"],
        facts=facts,
        tools_attempted=list(data["tools_attempted"]),
        tools_succeeded=list(data["tools_succeeded"]),
        tools_failed=list(data["tools_failed"]),
        collection_start_at=data["collection_start_at"],
        collection_end_at=data["collection_end_at"],
        errors=list(data["errors"]),
        warnings=list(data["warnings"]),
    )


class SnapshotStore:
    """Single-row SQLite store holding the most recent CollectionResult."""

    def __init__(self, db_path: str):
        """db_path is injected; this module never reads the environment."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def initialize(self) -> None:
        """Create the schema. Idempotent."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshot (
                id              INTEGER PRIMARY KEY CHECK (id = 1),
                schema_version  INTEGER NOT NULL,
                observed_at     TEXT    NOT NULL,
                payload_json    TEXT    NOT NULL
            )
        """)
        self.conn.commit()

    def save(self, result: CollectionResult, observed_at: str) -> None:
        """Replace the stored snapshot with this one."""
        payload = json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True)
        self.conn.execute(
            "INSERT INTO snapshot (id, schema_version, observed_at, payload_json) "
            "VALUES (1, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET schema_version=excluded.schema_version, "
            "observed_at=excluded.observed_at, payload_json=excluded.payload_json",
            (SNAPSHOT_SCHEMA_VERSION, observed_at, payload),
        )
        self.conn.commit()

    def load_latest(self) -> Optional[Tuple[CollectionResult, str]]:
        """
        Return (result, observed_at), or None when there is no usable snapshot.

        Returns None on a first run and on a schema version this build does
        not understand. Raises SnapshotDecodeError only when a snapshot of the
        right version is corrupt, because that is a defect worth surfacing.
        """
        row = self.conn.execute(
            "SELECT schema_version, observed_at, payload_json FROM snapshot WHERE id = 1"
        ).fetchone()
        if row is None:
            return None
        if row["schema_version"] != SNAPSHOT_SCHEMA_VERSION:
            return None
        try:
            data = json.loads(row["payload_json"])
        except json.JSONDecodeError as exc:
            raise SnapshotDecodeError("snapshot: payload is not valid JSON") from exc
        return deserialize_collection_result(data), row["observed_at"]

    def clear(self) -> None:
        """Forget the stored snapshot."""
        self.conn.execute("DELETE FROM snapshot WHERE id = 1")
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
