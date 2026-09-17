"""
EventPipeline - Step 4E.1 composition root.

WHAT THIS SOLVES
----------------
EventDetector, EventQueue and EventOrchestrator were built and tested during
steps 4A, 4B and 4D - roughly 1150 lines and 106 tests - but an audit on
2026-09-17 found that EventOrchestrator was imported by no module outside its
own test file. Three complete subsystems were reachable from nothing.

This module is the missing joint, and only the joint:

    CollectionResult -> EventDetector -> EventQueue -> EventOrchestrator

DELIBERATELY OUT OF SCOPE (step 4E.2 and beyond)
------------------------------------------------
- No scheduler, no timer, no systemd unit is modified by this module.
- No Telegram, no network, no real sending. dry_run must be True.
- No environment variables: every dependency is injected by the caller.
- No change to mediaman.py, which still runs the August foundation path.

ORDERING GUARANTEE
------------------
The snapshot of the current collection is saved as soon as the detected
events are durably enqueued, and before orchestration runs. A crash during
orchestration therefore cannot cause the same transitions to be detected
again on the next run: the events are already in the queue, which owns retry.
Conversely, if detection or enqueueing fails, the snapshot is NOT advanced,
so nothing is silently lost.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional

DEFAULT_MAX_CYCLES = 5
IDLE_SENTINEL = "no_events_available"


@dataclass
class PipelineResult:
    """Outcome of one pipeline pass. Counts only - never event payloads."""

    events_detected: int = 0
    events_enqueued: int = 0
    events_duplicate: int = 0
    leases_released: int = 0
    cycles_run: int = 0
    cycles_succeeded: int = 0
    cycles_failed: int = 0
    snapshot_saved: bool = False
    had_previous_snapshot: bool = False
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "events_detected": self.events_detected,
            "events_enqueued": self.events_enqueued,
            "events_duplicate": self.events_duplicate,
            "leases_released": self.leases_released,
            "cycles_run": self.cycles_run,
            "cycles_succeeded": self.cycles_succeeded,
            "cycles_failed": self.cycles_failed,
            "snapshot_saved": self.snapshot_saved,
            "had_previous_snapshot": self.had_previous_snapshot,
            "errors": list(self.errors),
        }


class EventPipeline:
    """Wire the event subsystems together for exactly one pass."""

    def __init__(
        self,
        detector: Any,
        event_queue: Any,
        orchestrator: Any,
        snapshot_store: Any,
        *,
        dry_run: bool,
        max_cycles: int = DEFAULT_MAX_CYCLES,
    ):
        """
        Every collaborator is injected. dry_run must be exactly True:
        a truthy value such as "false" or 1 is refused, because a string is
        the classic way an environment variable turns a safety flag into an
        always-on switch.
        """
        if dry_run is not True:
            raise ValueError("dry_run_required: EventPipeline runs in dry-run only at step 4E.1")
        if not isinstance(max_cycles, int) or max_cycles < 1:
            raise ValueError("max_cycles must be a positive integer")

        self.detector = detector
        self.event_queue = event_queue
        self.orchestrator = orchestrator
        self.snapshot_store = snapshot_store
        self.dry_run = True
        self.max_cycles = max_cycles

    def run_once(self, current: Any, observed_at: Optional[str] = None) -> PipelineResult:
        """
        Detect, enqueue, persist the snapshot, then drain up to max_cycles.

        Never raises for an orchestration failure: a failed cycle is recorded
        in the result and the queue keeps ownership of retry. Detection and
        enqueueing failures do propagate, because advancing past them would
        lose a transition for good.
        """
        result = PipelineResult()
        if observed_at is None:
            observed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        previous = None
        loaded = self.snapshot_store.load_latest()
        if loaded is not None:
            previous, _previous_observed_at = loaded
            result.had_previous_snapshot = True

        events = self.detector.detect_events(current, previous, observed_at)
        result.events_detected = len(events)

        for event in events:
            if self.event_queue.enqueue(event):
                result.events_enqueued += 1
            else:
                result.events_duplicate += 1

        # Ordering guarantee: the snapshot advances only once the events are
        # durably enqueued, and before any orchestration is attempted.
        self.snapshot_store.save(current, observed_at)
        result.snapshot_saved = True

        result.leases_released = self.event_queue.release_expired_leases()

        for _ in range(self.max_cycles):
            cycle = self.orchestrator.process_one_cycle()
            if getattr(cycle, "error", None) == IDLE_SENTINEL:
                break
            result.cycles_run += 1
            if getattr(cycle, "success", False):
                result.cycles_succeeded += 1
            else:
                result.cycles_failed += 1
                error = getattr(cycle, "error", None)
                if error:
                    result.errors.append(str(error))

        return result
