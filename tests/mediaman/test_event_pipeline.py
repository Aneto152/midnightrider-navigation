"""
Tests for EventPipeline - the step 4E.1 joint between detector, queue and
orchestrator.

Two layers on purpose:
  - contract tests with injected doubles, to pin the ordering guarantees;
  - one end-to-end test with the REAL EventDetector, EventQueue and
    EventOrchestrator, because the defect this module fixes was precisely
    that each part passed its own tests while nothing connected them.
"""

import os
import tempfile
import unittest
from dataclasses import dataclass
from typing import Any, List, Optional

from mediaman.event_detector import DetectedEvent, EventDetector
from mediaman.event_orchestrator import EventOrchestrator
from mediaman.event_pipeline import IDLE_SENTINEL, EventPipeline, PipelineResult
from mediaman.event_queue import EventQueue
from mediaman.mcp_collector import (
    CollectionResult, CollectionStatus, NavigationFact, Provenance,
)
from mediaman.snapshot_store import SnapshotStore


# --------------------------------------------------------------------------
# doubles
# --------------------------------------------------------------------------
@dataclass
class FakeCycle:
    success: bool = True
    error: Optional[str] = None


class FakeOrchestrator:
    def __init__(self, cycles: List[FakeCycle]):
        self.cycles = list(cycles)
        self.calls = 0

    def process_one_cycle(self):
        self.calls += 1
        if self.cycles:
            return self.cycles.pop(0)
        return FakeCycle(success=False, error=IDLE_SENTINEL)


class FakeDetector:
    def __init__(self, events):
        self.events = events
        self.seen_previous = "not-called"

    def detect_events(self, current, previous, observed_at):
        self.seen_previous = previous
        return list(self.events)


class FakeQueue:
    def __init__(self, duplicates=(), released=0):
        self.enqueued = []
        self.duplicates = set(duplicates)
        self.released = released

    def enqueue(self, event):
        self.enqueued.append(event)
        return event.event_id not in self.duplicates

    def release_expired_leases(self):
        return self.released


class FakeSnapshotStore:
    def __init__(self, previous=None):
        self.previous = previous
        self.saved = []
        self.order = []

    def load_latest(self):
        self.order.append("load")
        return self.previous

    def save(self, result, observed_at):
        self.order.append("save")
        self.saved.append((result, observed_at))


class RecordingOrchestrator(FakeOrchestrator):
    def __init__(self, cycles, store):
        super().__init__(cycles)
        self.store = store

    def process_one_cycle(self):
        self.store.order.append("cycle")
        return super().process_one_cycle()


def ev(event_id, event_type="NAVIGATION_DATA_LOST"):
    return DetectedEvent(event_id=event_id, event_type=event_type,
                         observed_at="2026-09-17T00:00:00Z", severity="WARNING")


def build(detector=None, queue=None, orch=None, store=None, **kw):
    return EventPipeline(
        detector or FakeDetector([]), queue or FakeQueue(),
        orch or FakeOrchestrator([]), store or FakeSnapshotStore(),
        dry_run=kw.pop("dry_run", True), **kw,
    )


# --------------------------------------------------------------------------
class TestSafetyGate(unittest.TestCase):
    def test_dry_run_must_be_true(self):
        with self.assertRaises(ValueError):
            build(dry_run=False)

    def test_truthy_string_is_not_accepted(self):
        for value in ("true", "false", 1, [1]):
            with self.assertRaises(ValueError):
                build(dry_run=value)

    def test_max_cycles_must_be_a_positive_int(self):
        for value in (0, -1, "3", 2.0):
            with self.assertRaises(ValueError):
                build(max_cycles=value)


class TestDetectionAndEnqueue(unittest.TestCase):
    def test_every_detected_event_is_enqueued(self):
        q = FakeQueue()
        r = build(detector=FakeDetector([ev("a"), ev("b")]), queue=q).run_once(object())
        self.assertEqual(r.events_detected, 2)
        self.assertEqual(r.events_enqueued, 2)
        self.assertEqual(len(q.enqueued), 2)

    def test_duplicates_are_counted_separately(self):
        q = FakeQueue(duplicates={"b"})
        r = build(detector=FakeDetector([ev("a"), ev("b")]), queue=q).run_once(object())
        self.assertEqual((r.events_enqueued, r.events_duplicate), (1, 1))

    def test_previous_snapshot_is_handed_to_the_detector(self):
        marker = object()
        d = FakeDetector([])
        r = build(detector=d, store=FakeSnapshotStore(previous=(marker, "t0"))).run_once(object())
        self.assertIs(d.seen_previous, marker)
        self.assertTrue(r.had_previous_snapshot)

    def test_first_run_passes_none_as_previous(self):
        d = FakeDetector([])
        r = build(detector=d, store=FakeSnapshotStore(previous=None)).run_once(object())
        self.assertIsNone(d.seen_previous)
        self.assertFalse(r.had_previous_snapshot)

    def test_released_leases_are_reported(self):
        r = build(queue=FakeQueue(released=3)).run_once(object())
        self.assertEqual(r.leases_released, 3)


class TestOrderingGuarantee(unittest.TestCase):
    def test_snapshot_is_saved_before_any_orchestration(self):
        store = FakeSnapshotStore()
        orch = RecordingOrchestrator([FakeCycle(True)], store)
        build(detector=FakeDetector([ev("a")]), orch=orch, store=store).run_once(object())
        self.assertEqual(store.order[:2], ["load", "save"])
        self.assertIn("cycle", store.order)
        self.assertLess(store.order.index("save"), store.order.index("cycle"))

    def test_snapshot_still_saved_when_a_cycle_fails(self):
        store = FakeSnapshotStore()
        orch = FakeOrchestrator([FakeCycle(False, "adapter_timeout")])
        r = build(detector=FakeDetector([ev("a")]), orch=orch, store=store).run_once(object())
        self.assertTrue(r.snapshot_saved)
        self.assertEqual(len(store.saved), 1)
        self.assertEqual(r.cycles_failed, 1)
        self.assertIn("adapter_timeout", r.errors)

    def test_enqueue_failure_does_not_advance_the_snapshot(self):
        class Exploding(FakeQueue):
            def enqueue(self, event):
                raise RuntimeError("disk full")
        store = FakeSnapshotStore()
        with self.assertRaises(RuntimeError):
            build(detector=FakeDetector([ev("a")]), queue=Exploding(), store=store).run_once(object())
        self.assertEqual(store.saved, [])


class TestDraining(unittest.TestCase):
    def test_stops_on_the_idle_sentinel(self):
        orch = FakeOrchestrator([FakeCycle(True), FakeCycle(False, IDLE_SENTINEL), FakeCycle(True)])
        r = build(orch=orch).run_once(object())
        self.assertEqual(r.cycles_run, 1)
        self.assertEqual(orch.calls, 2)

    def test_never_exceeds_max_cycles(self):
        orch = FakeOrchestrator([FakeCycle(True) for _ in range(20)])
        r = build(orch=orch, max_cycles=3).run_once(object())
        self.assertEqual((r.cycles_run, orch.calls), (3, 3))

    def test_idle_queue_runs_no_cycle(self):
        r = build(orch=FakeOrchestrator([])).run_once(object())
        self.assertEqual(r.cycles_run, 0)

    def test_result_serialises_to_counts_only(self):
        d = build().run_once(object()).to_dict()
        self.assertEqual(set(d), {
            "events_detected", "events_enqueued", "events_duplicate", "leases_released",
            "cycles_run", "cycles_succeeded", "cycles_failed", "snapshot_saved",
            "had_previous_snapshot", "errors"})
        for key, value in d.items():
            if key != "errors":
                self.assertIsInstance(value, (int, bool), key)


# --------------------------------------------------------------------------
class FakeAdapter:
    """Minimal stand-in for OpenClawAdapter.generate_article(prompt=...)."""

    def __init__(self):
        self.prompts = []

    def generate_article(self, prompt):
        self.prompts.append(prompt)
        return type("R", (), {"success": True, "content": "Article de test.",
                              "error": None, "duration_seconds": 0.0})()


def result_with(status, race_id="race-1", validation="valid"):
    prov = Provenance(
        tool_public_id="nav.position", server_name="signalk",
        wire_tool_name="get_snapshot", source_id="vessels.self",
        source_timestamp="2026-09-17T00:00:00Z", observed_at="2026-09-17T00:00:05Z",
        freshness_limit_seconds=30, validation_status=validation, warnings=[],
    )
    return CollectionResult(
        status=status, race_id=race_id,
        facts=[NavigationFact("sog", 6.4, "kn", prov)],
        tools_attempted=["get_snapshot"],
        tools_succeeded=["get_snapshot"] if status != CollectionStatus.FAILED else [],
        tools_failed=[] if status != CollectionStatus.FAILED else ["get_snapshot"],
        collection_start_at="2026-09-17T00:00:00Z",
        collection_end_at="2026-09-17T00:00:06Z", errors=[], warnings=[],
    )


class TestRealComponentsEndToEnd(unittest.TestCase):
    """The joint, exercised with the genuine 4A / 4B / 4D components."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.queue = EventQueue(os.path.join(self.tmp, "q.db"))
        self.queue.initialize()
        self.store = SnapshotStore(os.path.join(self.tmp, "s.db"))
        self.store.initialize()
        self.adapter = FakeAdapter()
        self.pipeline = EventPipeline(
            EventDetector(), self.queue,
            EventOrchestrator(self.queue, self.adapter), self.store,
            dry_run=True, max_cycles=5,
        )

    def test_first_run_is_silent_then_a_real_transition_is_carried_through(self):
        first = self.pipeline.run_once(result_with(CollectionStatus.COMPLETE),
                                       "2026-09-17T00:00:10Z")
        self.assertFalse(first.had_previous_snapshot)
        self.assertTrue(first.snapshot_saved)

        second = self.pipeline.run_once(result_with(CollectionStatus.FAILED),
                                        "2026-09-17T00:15:10Z")
        self.assertTrue(second.had_previous_snapshot)
        self.assertGreater(second.events_detected, 0)
        self.assertEqual(second.events_enqueued, second.events_detected)
        self.assertGreater(second.cycles_run, 0)
        self.assertEqual(second.cycles_failed, 0)
        self.assertTrue(self.adapter.prompts, "the adapter was never reached")

    def test_a_repeated_identical_run_detects_nothing_new(self):
        self.pipeline.run_once(result_with(CollectionStatus.COMPLETE), "2026-09-17T00:00:10Z")
        again = self.pipeline.run_once(result_with(CollectionStatus.COMPLETE),
                                       "2026-09-17T00:15:10Z")
        self.assertEqual(again.events_enqueued, 0)

    def test_prompt_carries_no_raw_payload(self):
        self.pipeline.run_once(result_with(CollectionStatus.COMPLETE), "2026-09-17T00:00:10Z")
        self.pipeline.run_once(result_with(CollectionStatus.FAILED), "2026-09-17T00:15:10Z")
        for prompt in self.adapter.prompts:
            self.assertNotIn("payload_json", str(prompt))
            self.assertNotIn("token", str(prompt).lower())


if __name__ == "__main__":
    unittest.main()
