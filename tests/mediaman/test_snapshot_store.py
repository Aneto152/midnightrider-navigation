"""Tests for SnapshotStore - persistence of the previous CollectionResult."""

import json
import os
import sqlite3
import tempfile
import unittest

from mediaman.mcp_collector import (
    CollectionResult, CollectionStatus, NavigationFact, Provenance,
)
from mediaman.snapshot_store import (
    SNAPSHOT_SCHEMA_VERSION, SnapshotDecodeError, SnapshotStore,
    deserialize_collection_result,
)


def make_result(status=CollectionStatus.COMPLETE, race_id="race-1"):
    prov = Provenance(
        tool_public_id="nav.position", server_name="signalk",
        wire_tool_name="get_position", source_id="vessels.self",
        source_timestamp="2026-09-17T00:00:00Z", observed_at="2026-09-17T00:00:05Z",
        freshness_limit_seconds=30, validation_status="valid", warnings=["late"],
    )
    return CollectionResult(
        status=status, race_id=race_id,
        facts=[NavigationFact(field_name="sog", value=6.4, unit="kn", provenance=prov)],
        tools_attempted=["get_position"], tools_succeeded=["get_position"],
        tools_failed=[], collection_start_at="2026-09-17T00:00:00Z",
        collection_end_at="2026-09-17T00:00:06Z", errors=[], warnings=["late"],
    )


class TestRoundTrip(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = SnapshotStore(os.path.join(self.tmp, "s.db"))
        self.store.initialize()

    def tearDown(self):
        self.store.close()

    def test_no_snapshot_on_first_run(self):
        self.assertIsNone(self.store.load_latest())

    def test_save_then_load_is_lossless(self):
        original = make_result()
        self.store.save(original, "2026-09-17T00:00:06Z")
        loaded, observed_at = self.store.load_latest()
        self.assertEqual(observed_at, "2026-09-17T00:00:06Z")
        self.assertEqual(loaded.to_dict(), original.to_dict())

    def test_rehydrated_objects_are_real_types(self):
        self.store.save(make_result(), "2026-09-17T00:00:06Z")
        loaded, _ = self.store.load_latest()
        self.assertIsInstance(loaded, CollectionResult)
        self.assertIsInstance(loaded.status, CollectionStatus)
        self.assertIsInstance(loaded.facts[0], NavigationFact)
        self.assertIsInstance(loaded.facts[0].provenance, Provenance)

    def test_only_one_row_is_kept(self):
        for i in range(5):
            self.store.save(make_result(race_id=f"race-{i}"), f"2026-09-17T00:0{i}:00Z")
        count = self.store.conn.execute("SELECT COUNT(*) FROM snapshot").fetchone()[0]
        self.assertEqual(count, 1)
        loaded, _ = self.store.load_latest()
        self.assertEqual(loaded.race_id, "race-4")

    def test_initialize_is_idempotent(self):
        self.store.initialize()
        self.store.save(make_result(), "2026-09-17T00:00:06Z")
        self.store.initialize()
        self.assertIsNotNone(self.store.load_latest())

    def test_clear_forgets_the_snapshot(self):
        self.store.save(make_result(), "2026-09-17T00:00:06Z")
        self.store.clear()
        self.assertIsNone(self.store.load_latest())

    def test_every_status_survives_the_round_trip(self):
        for status in CollectionStatus:
            self.store.save(make_result(status=status), "2026-09-17T00:00:06Z")
            loaded, _ = self.store.load_latest()
            self.assertEqual(loaded.status, status)


class TestStrictDecoding(unittest.TestCase):
    def test_unknown_key_is_refused(self):
        data = make_result().to_dict()
        data["surprise"] = 1
        with self.assertRaises(SnapshotDecodeError):
            deserialize_collection_result(data)

    def test_missing_key_is_refused(self):
        data = make_result().to_dict()
        del data["warnings"]
        with self.assertRaises(SnapshotDecodeError):
            deserialize_collection_result(data)

    def test_unknown_nested_provenance_key_is_refused(self):
        data = make_result().to_dict()
        data["facts"][0]["provenance"]["leaked_token"] = "x"
        with self.assertRaises(SnapshotDecodeError):
            deserialize_collection_result(data)

    def test_unknown_status_is_refused(self):
        data = make_result().to_dict()
        data["status"] = "sideways"
        with self.assertRaises(SnapshotDecodeError):
            deserialize_collection_result(data)

    def test_non_object_is_refused(self):
        with self.assertRaises(SnapshotDecodeError):
            deserialize_collection_result(["not", "a", "dict"])


class TestCorruption(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "s.db")
        self.store = SnapshotStore(self.path)
        self.store.initialize()
        self.store.save(make_result(), "2026-09-17T00:00:06Z")

    def tearDown(self):
        self.store.close()

    def test_future_schema_version_is_ignored_not_crashed(self):
        self.store.conn.execute("UPDATE snapshot SET schema_version = ? WHERE id = 1",
                                (SNAPSHOT_SCHEMA_VERSION + 1,))
        self.store.conn.commit()
        self.assertIsNone(self.store.load_latest())

    def test_invalid_json_raises_rather_than_returning_half_a_state(self):
        self.store.conn.execute("UPDATE snapshot SET payload_json = '{oops' WHERE id = 1")
        self.store.conn.commit()
        with self.assertRaises(SnapshotDecodeError):
            self.store.load_latest()

    def test_truncated_payload_raises(self):
        data = make_result().to_dict()
        del data["facts"]
        self.store.conn.execute("UPDATE snapshot SET payload_json = ? WHERE id = 1",
                                (json.dumps(data),))
        self.store.conn.commit()
        with self.assertRaises(SnapshotDecodeError):
            self.store.load_latest()


class TestNoSecrets(unittest.TestCase):
    def test_stored_payload_holds_no_credential_shaped_key(self):
        tmp = tempfile.mkdtemp()
        store = SnapshotStore(os.path.join(tmp, "s.db"))
        store.initialize()
        store.save(make_result(), "2026-09-17T00:00:06Z")
        raw = store.conn.execute("SELECT payload_json FROM snapshot").fetchone()[0]
        for banned in ("token", "password", "secret", "credential", "api_key"):
            self.assertNotIn(banned, raw.lower())
        store.close()


if __name__ == "__main__":
    unittest.main()
