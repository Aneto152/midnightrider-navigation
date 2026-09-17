"""
Tests for mediaman/event_entrypoint.py - step 4E.2.

Written with unittest rather than bare pytest functions so that the whole file
can be executed with the standard library alone. pytest collects
unittest.TestCase classes unchanged.

WHAT THESE TESTS REFUSE TO DO
-----------------------------
They never construct OpenClawAdapter, whose __init__ shells out to the
openclaw CLI, and they never let a test write into the repository's real
logs/services directory: the log directory is injected on every run.
"""

import logging
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from mediaman.event_entrypoint import (
    ConfigError,
    DryRunArticleAdapter,
    SERVICE_NAME,
    SNAPSHOT_DB_FILENAME,
    _attach_module_logs,
    build_adapter,
    collect_selftest_result,
    main,
    parse_config,
)


def base_env(tmp: str, **overrides) -> dict:
    env = {
        "DRY_RUN": "true",
        "MEDIAMAN_RACE_ID": "test-race",
        "MEDIAMAN_EVENT_SOURCE": "selftest",
        "MEDIAMAN_EVENT_STATE_DIR": str(Path(tmp) / "state"),
        "MEDIAMAN_EVENT_LOG_DIR": str(Path(tmp) / "logs"),
    }
    env.update(overrides)
    return {k: v for k, v in env.items() if v is not None}


class TestConfigIsRefusedClosed(unittest.TestCase):
    """Every rejection must be explicit, and must name no value."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def assert_refused(self, reason_fragment, **overrides):
        with self.assertRaises(ConfigError) as ctx:
            parse_config(base_env(self.tmp, **overrides))
        self.assertIn(reason_fragment, str(ctx.exception))

    def test_dry_run_absent_is_refused(self):
        self.assert_refused("dry_run_must_be_exactly_true", DRY_RUN=None)

    def test_dry_run_capitalised_is_refused(self):
        self.assert_refused("dry_run_must_be_exactly_true", DRY_RUN="True")

    def test_dry_run_one_is_refused(self):
        """A truthy value is the classic way a safety flag becomes always-on."""
        self.assert_refused("dry_run_must_be_exactly_true", DRY_RUN="1")

    def test_dry_run_false_is_refused(self):
        self.assert_refused("dry_run_must_be_exactly_true", DRY_RUN="false")

    def test_blank_race_id_is_refused(self):
        self.assert_refused("MEDIAMAN_RACE_ID", MEDIAMAN_RACE_ID="   ")

    def test_unknown_source_is_refused(self):
        self.assert_refused("MEDIAMAN_EVENT_SOURCE", MEDIAMAN_EVENT_SOURCE="live")

    def test_zero_max_cycles_is_refused(self):
        self.assert_refused("MEDIAMAN_MAX_CYCLES", MEDIAMAN_MAX_CYCLES="0")

    def test_non_numeric_max_cycles_is_refused(self):
        self.assert_refused("MEDIAMAN_MAX_CYCLES", MEDIAMAN_MAX_CYCLES="abc")

    def test_negative_max_cycles_is_refused(self):
        self.assert_refused("MEDIAMAN_MAX_CYCLES", MEDIAMAN_MAX_CYCLES="-2")

    def test_mcp_source_without_server_path_is_refused(self):
        self.assert_refused("MEDIAMAN_MCP_SERVER_PATH", MEDIAMAN_EVENT_SOURCE="mcp")

    def test_unrecognised_allow_llm_is_refused(self):
        """Neither empty, "true" nor "false" - refuse rather than guess."""
        self.assert_refused("MEDIAMAN_ALLOW_LLM", MEDIAMAN_ALLOW_LLM="yes")

    def test_refusal_never_echoes_the_offending_value(self):
        with self.assertRaises(ConfigError) as ctx:
            parse_config(base_env(self.tmp, MEDIAMAN_ALLOW_LLM="hunter2"))
        self.assertNotIn("hunter2", str(ctx.exception))


class TestConfigAccepted(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_defaults(self):
        config = parse_config(base_env(self.tmp))
        self.assertEqual(config["max_cycles"], 5)
        self.assertFalse(config["allow_llm"])
        self.assertEqual(config["source"], "selftest")

    def test_explicit_max_cycles(self):
        config = parse_config(base_env(self.tmp, MEDIAMAN_MAX_CYCLES="3"))
        self.assertEqual(config["max_cycles"], 3)

    def test_allow_llm_false_is_accepted_and_stays_false(self):
        config = parse_config(base_env(self.tmp, MEDIAMAN_ALLOW_LLM="false"))
        self.assertFalse(config["allow_llm"])

    def test_allow_llm_true_is_the_only_way_to_enable_the_real_adapter(self):
        config = parse_config(base_env(self.tmp, MEDIAMAN_ALLOW_LLM="true"))
        self.assertTrue(config["allow_llm"])

    def test_source_is_case_insensitive(self):
        config = parse_config(base_env(self.tmp, MEDIAMAN_EVENT_SOURCE="SelfTest"))
        self.assertEqual(config["source"], "selftest")


class TestStateDirectoryResolution(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_explicit_override_wins_over_systemd(self):
        env = base_env(self.tmp, MEDIAMAN_EVENT_SOURCE="mcp",
                       MEDIAMAN_MCP_SERVER_PATH="/srv/x.py")
        env["STATE_DIRECTORY"] = "/var/lib/should-be-ignored"
        self.assertEqual(parse_config(env)["state_dir"],
                         Path(self.tmp) / "state")

    def test_systemd_state_directory_is_used_when_no_override(self):
        env = base_env(self.tmp, MEDIAMAN_EVENT_SOURCE="mcp",
                       MEDIAMAN_MCP_SERVER_PATH="/srv/x.py",
                       MEDIAMAN_EVENT_STATE_DIR=None)
        env["STATE_DIRECTORY"] = "/var/lib/mediaman-events"
        self.assertEqual(parse_config(env)["state_dir"],
                         Path("/var/lib/mediaman-events"))

    def test_only_the_first_systemd_state_directory_is_taken(self):
        """systemd separates multiple StateDirectory entries with a colon."""
        env = base_env(self.tmp, MEDIAMAN_EVENT_SOURCE="mcp",
                       MEDIAMAN_MCP_SERVER_PATH="/srv/x.py",
                       MEDIAMAN_EVENT_STATE_DIR=None)
        env["STATE_DIRECTORY"] = "/var/lib/a:/var/lib/b"
        self.assertEqual(parse_config(env)["state_dir"], Path("/var/lib/a"))

    def test_selftest_state_is_isolated_from_live_state(self):
        """
        Found in rehearsal: a synthetic snapshot in the live directory would
        make the next real collection compare live data against invented data.
        """
        live = parse_config(base_env(self.tmp, MEDIAMAN_EVENT_SOURCE="mcp",
                                    MEDIAMAN_MCP_SERVER_PATH="/srv/x.py"))
        fake = parse_config(base_env(self.tmp, MEDIAMAN_EVENT_SOURCE="selftest"))
        self.assertNotEqual(live["state_dir"], fake["state_dir"])
        self.assertEqual(fake["state_dir"], live["state_dir"] / "selftest")


class TestDryRunAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = DryRunArticleAdapter(logger=logging.getLogger("test-quiet"))

    def test_it_reports_available(self):
        self.assertTrue(self.adapter.is_available())

    def test_it_returns_a_marker_and_not_a_plausible_article(self):
        result = self.adapter.generate_article(prompt="anything")
        self.assertTrue(result.success)
        self.assertIn("DRY-RUN", result.content)
        self.assertEqual(result.provider_status, "dry_run")

    def test_it_counts_its_invocations(self):
        for _ in range(3):
            self.adapter.generate_article(prompt="p")
        self.assertEqual(self.adapter.calls, 3)

    def test_it_satisfies_the_call_shape_the_orchestrator_uses(self):
        """
        EventOrchestrator performs no isinstance check and calls
        generate_article(prompt=...). Verified by reading the orchestrator,
        pinned here so a future signature change breaks a test, not the boat.
        """
        import inspect
        params = inspect.signature(self.adapter.generate_article).parameters
        self.assertIn("prompt", params)

    def test_build_adapter_returns_the_dry_run_one_by_default(self):
        tmp = tempfile.mkdtemp()
        config = parse_config(base_env(tmp))
        adapter = build_adapter(config, logging.getLogger("test-quiet"))
        self.assertIsInstance(adapter, DryRunArticleAdapter)


class TestModuleLogRouting(unittest.TestCase):
    """Defect 46: mediaman.* module logs used to go nowhere."""

    def tearDown(self):
        parent = logging.getLogger("mediaman")
        for handler in list(parent.handlers):
            parent.removeHandler(handler)

    def _service_logger(self):
        tmp = tempfile.mkdtemp()
        from mediaman.logging_utils import setup_service_logger
        return setup_service_logger("test-routing", log_dir=tmp)

    def test_attaching_reports_success_then_refuses_to_duplicate(self):
        logger = self._service_logger()
        self.assertTrue(_attach_module_logs(logger))
        self.assertFalse(_attach_module_logs(logger))

    def test_the_parent_logger_receives_the_handler(self):
        logger = self._service_logger()
        _attach_module_logs(logger)
        self.assertIn(logger.handlers[0], logging.getLogger("mediaman").handlers)

    def test_a_logger_without_handlers_is_reported_as_not_attached(self):
        bare = logging.getLogger("test-bare-no-handlers")
        for handler in list(bare.handlers):
            bare.removeHandler(handler)
        self.assertFalse(_attach_module_logs(bare))


class TestSelftestSource(unittest.TestCase):
    def test_the_synthetic_result_declares_itself_synthetic(self):
        tmp = tempfile.mkdtemp()
        config = parse_config(base_env(tmp))
        result = collect_selftest_result(config)
        joined = " ".join(result.warnings + result.errors).lower()
        self.assertIn("synthetic", joined)

    def test_it_carries_no_navigation_facts(self):
        tmp = tempfile.mkdtemp()
        result = collect_selftest_result(parse_config(base_env(tmp)))
        self.assertEqual(result.facts, [])


class TestMainExitCodes(unittest.TestCase):
    """systemd reads these numbers, so they are part of the contract."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._saved = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._saved)
        parent = logging.getLogger("mediaman")
        for handler in list(parent.handlers):
            parent.removeHandler(handler)

    def _run(self, **overrides):
        os.environ.clear()
        os.environ.update({"PATH": "/usr/bin:/bin"})
        os.environ.update(base_env(self.tmp, **overrides))
        return main()

    def test_bad_configuration_returns_two(self):
        self.assertEqual(self._run(DRY_RUN="True"), 2)

    def test_a_selftest_pass_returns_zero(self):
        self.assertEqual(self._run(), 0)

    def test_a_failed_collection_returns_three(self):
        self.assertEqual(
            self._run(MEDIAMAN_EVENT_SOURCE="mcp",
                      MEDIAMAN_MCP_SERVER_PATH="/nonexistent/server.py"),
            3,
        )

    def test_a_failed_collection_does_not_advance_the_snapshot(self):
        """
        The guarantee is about rows, not files. The database file is created
        by initialize(); what must stay empty is the snapshot table.
        """
        self._run(MEDIAMAN_EVENT_SOURCE="mcp",
                  MEDIAMAN_MCP_SERVER_PATH="/nonexistent/server.py")
        db = Path(self.tmp) / "state" / SNAPSHOT_DB_FILENAME
        self.assertTrue(db.exists())
        conn = sqlite3.connect(str(db))
        try:
            rows = conn.execute("SELECT COUNT(*) FROM snapshot").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(rows, 0)

    def test_a_selftest_pass_does_advance_its_own_snapshot(self):
        self._run()
        db = Path(self.tmp) / "state" / "selftest" / SNAPSHOT_DB_FILENAME
        conn = sqlite3.connect(str(db))
        try:
            rows = conn.execute("SELECT COUNT(*) FROM snapshot").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(rows, 1)

    def test_the_run_writes_the_mandatory_probes(self):
        self._run()
        log = Path(self.tmp) / "logs" / f"{SERVICE_NAME}.log"
        content = log.read_text()
        for probe in ("STARTUP", "DATA_IN", "DATA_OUT", "HEARTBEAT", "SHUTDOWN"):
            self.assertIn(probe, content, f"probe {probe} missing from service log")

    def test_the_log_carries_no_credential_vocabulary(self):
        self._run()
        log = (Path(self.tmp) / "logs" / f"{SERVICE_NAME}.log").read_text().lower()
        for forbidden in ("bearer ", "password=", "token=", "secret="):
            self.assertNotIn(forbidden, log)


class TestRealChainThroughTheEntrypoint(unittest.TestCase):
    """
    Two successive real passes, driven by the real components, asserting the
    behaviour that matters: a repeated identical state must stay silent.
    """

    def tearDown(self):
        parent = logging.getLogger("mediaman")
        for handler in list(parent.handlers):
            parent.removeHandler(handler)

    def test_a_real_transition_is_detected_and_a_repeat_is_not(self):
        from mediaman.event_detector import EventDetector
        from mediaman.event_orchestrator import EventOrchestrator
        from mediaman.event_pipeline import EventPipeline
        from mediaman.event_queue import EventQueue
        from mediaman.mcp_collector import CollectionResult, CollectionStatus
        from mediaman.snapshot_store import SnapshotStore

        tmp = tempfile.mkdtemp()
        quiet = logging.getLogger("test-quiet")
        snapshots = SnapshotStore(str(Path(tmp) / "s.db"))
        snapshots.initialize()
        queue = EventQueue(db_path=str(Path(tmp) / "q.db"))
        queue.initialize()
        adapter = DryRunArticleAdapter(logger=quiet)
        pipeline = EventPipeline(
            detector=EventDetector(logger=quiet),
            event_queue=queue,
            orchestrator=EventOrchestrator(event_queue=queue, adapter=adapter),
            snapshot_store=snapshots,
            dry_run=True,
            logger=quiet,
        )

        def collection(status):
            return CollectionResult(
                status=status, race_id="r1",
                collection_start_at="2026-09-17T01:00:00Z",
                collection_end_at="2026-09-17T01:00:05Z",
            )

        first = pipeline.run_once(collection(CollectionStatus.COMPLETE),
                                  "2026-09-17T01:00:05Z")
        self.assertFalse(first.had_previous_snapshot)
        self.assertEqual(first.events_detected, 0)

        lost = pipeline.run_once(collection(CollectionStatus.FAILED),
                                 "2026-09-17T01:15:05Z")
        self.assertEqual(lost.events_detected, 1)
        self.assertEqual(lost.events_enqueued, 1)
        self.assertEqual(lost.cycles_succeeded, 1)

        repeat = pipeline.run_once(collection(CollectionStatus.FAILED),
                                   "2026-09-17T01:30:05Z")
        self.assertEqual(repeat.events_detected, 0)
        self.assertEqual(repeat.cycles_run, 0)

        self.assertEqual(adapter.calls, 1)
        queue.close()
        snapshots.close()

    def test_the_pipeline_still_accepts_no_logger_at_all(self):
        """Backwards compatibility: every 4E.1 caller passed no logger."""
        from mediaman.event_pipeline import EventPipeline
        pipeline = EventPipeline(detector=None, event_queue=None,
                                 orchestrator=None, snapshot_store=None,
                                 dry_run=True)
        self.assertIsNotNone(pipeline.logger)


if __name__ == "__main__":
    unittest.main(verbosity=2)
