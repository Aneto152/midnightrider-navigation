"""
Event pipeline entrypoint - Step 4E.2.

WHAT THIS IS
------------
The process entrypoint that step 4E.1 was missing. EventPipeline wires the
event subsystems together, but nothing invoked it: the joint itself was
unreachable. This module is what a systemd unit executes.

It is additive by design. mediaman.service and mediaman/mediaman.py are NOT
touched: the August foundation keeps its own path, and the decision about its
future stays open. This entrypoint is driven by its own unit,
mediaman-events.service, which ships DISABLED.

WHY A SEPARATE FILE AND NOT historical_entrypoint.py
----------------------------------------------------
historical_entrypoint.py answers "describe race X as it stood at instant T".
It requires MEDIAMAN_HISTORICAL_AS_OF and a fixed window, so a repeating timer
would replay the same past window forever. Event detection needs the opposite:
successive observations of the present, compared against the previous one.

SAFETY POSTURE
--------------
- DRY_RUN must be exactly the string "true". Anything else aborts.
- The real OpenClaw adapter is NEVER built unless MEDIAMAN_ALLOW_LLM=true.
  Its constructor shells out to the openclaw CLI, so merely instantiating it
  reaches outside the process. The default is DryRunArticleAdapter below.
- No Telegram, no sending, no network beyond the MCP server it is told to use.
- Not one credential is read, logged or passed anywhere.

EXIT CODES (systemd reads these)
--------------------------------
0  one pass completed
2  configuration refused (fail-closed; nothing was touched)
3  collection failed - the snapshot was deliberately NOT advanced
4  unexpected internal error
"""

import os
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path

from mediaman.event_detector import EventDetector
from mediaman.event_queue import EventQueue
from mediaman.event_orchestrator import EventOrchestrator
from mediaman.event_pipeline import EventPipeline
from mediaman.snapshot_store import SnapshotStore
from mediaman.logging_utils import setup_service_logger

SERVICE_NAME = "mediaman-events"
DEFAULT_MAX_CYCLES = 5
QUEUE_DB_FILENAME = "events-queue.db"
SNAPSHOT_DB_FILENAME = "events-snapshot.db"


class DryRunArticleAdapter:
    """
    Stand-in for OpenClawAdapter that never leaves the process.

    Duck-typed on purpose: EventOrchestrator.__init__ performs no isinstance
    check, it only calls generate_article(prompt=...). Verified by reading
    mediaman/event_orchestrator.py at step 4E.2, not assumed.

    Returns a deterministic marker rather than a plausible article, so that a
    dry-run result can never be mistaken for real generated content.
    """

    DRY_RUN_MARKER = "[DRY-RUN] no article generated: MEDIAMAN_ALLOW_LLM is not true"

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.available = True
        self.calls = 0

    def is_available(self) -> bool:
        return True

    def generate_article(self, prompt: str, agent_id: str = "main",
                         thinking_level: str = "low"):
        """Accept the prompt, return a marker. The prompt is never logged."""
        self.calls += 1
        self.logger.info(
            "DATA_OUT dry-run adapter invoked: prompt_length=%d call=%d",
            len(prompt), self.calls
        )
        # Local import: keeps the module importable even if the real adapter's
        # dependencies are unavailable, and avoids constructing OpenClawAdapter.
        from mediaman.openclaw_adapter import OpenClawResult
        return OpenClawResult(
            success=True,
            content=self.DRY_RUN_MARKER,
            provider_status="dry_run",
        )


class ConfigError(ValueError):
    """Configuration refused. Carries no value from the environment."""


def _attach_module_logs(service_logger: logging.Logger) -> bool:
    """
    Route mediaman.* module logs into the service log file. Closes defect 46.

    event_orchestrator.py already logs through logging.getLogger(__name__),
    i.e. "mediaman.event_orchestrator", but no handler was ever attached to
    that hierarchy, so every one of those lines went nowhere. Attaching the
    service handler to the "mediaman" parent captures them with no edit to
    event_detector.py, event_queue.py or event_orchestrator.py.

    "mediaman-events" is not a child of "mediaman", so nothing is logged twice.

    Returns True when a handler was attached.
    """
    if not service_logger.handlers:
        return False
    parent = logging.getLogger("mediaman")
    parent.setLevel(logging.DEBUG)
    handler = service_logger.handlers[0]
    if handler in parent.handlers:
        return False
    parent.addHandler(handler)
    return True


def _require(name: str, env: dict) -> str:
    value = (env.get(name) or "").strip()
    if not value:
        raise ConfigError(f"missing_or_empty:{name}")
    return value


def _resolve_state_dir(env: dict) -> Path:
    """
    Where the two SQLite files live.

    STATE_DIRECTORY is set by systemd when StateDirectory= is declared and is
    preferred. MEDIAMAN_EVENT_STATE_DIR overrides it for manual runs. Falling
    back to the repository keeps a bare `python3 -m` invocation working.
    """
    explicit = (env.get("MEDIAMAN_EVENT_STATE_DIR") or "").strip()
    if explicit:
        return Path(explicit)
    systemd_state = (env.get("STATE_DIRECTORY") or "").strip()
    if systemd_state:
        return Path(systemd_state.split(":")[0])
    return Path(__file__).resolve().parent.parent / "var" / "mediaman-events"


def parse_config(env: dict) -> dict:
    """
    Validate the environment. Fail closed, and never echo a value back.

    Raises ConfigError with a stable machine-readable reason.
    """
    dry_run = (env.get("DRY_RUN") or "").strip()
    if dry_run != "true":
        raise ConfigError("dry_run_must_be_exactly_true")

    allow_llm = (env.get("MEDIAMAN_ALLOW_LLM") or "").strip()
    if allow_llm not in ("", "true", "false"):
        raise ConfigError("invalid:MEDIAMAN_ALLOW_LLM")

    source = (env.get("MEDIAMAN_EVENT_SOURCE") or "mcp").strip().lower()
    if source not in ("mcp", "selftest"):
        raise ConfigError("invalid:MEDIAMAN_EVENT_SOURCE")

    raw_cycles = (env.get("MEDIAMAN_MAX_CYCLES") or "").strip()
    if raw_cycles == "":
        max_cycles = DEFAULT_MAX_CYCLES
    else:
        if not raw_cycles.isdigit() or int(raw_cycles) < 1:
            raise ConfigError("invalid:MEDIAMAN_MAX_CYCLES")
        max_cycles = int(raw_cycles)

    config = {
        "race_id": _require("MEDIAMAN_RACE_ID", env),
        "source": source,
        "allow_llm": allow_llm == "true",
        "max_cycles": max_cycles,
        "state_dir": _resolve_state_dir(env),
        "mcp_server_path": (env.get("MEDIAMAN_MCP_SERVER_PATH") or "").strip(),
        # Test-only injection. Empty means the production default inside
        # logging_utils: the logs/services directory of this repository.
        "log_dir": (env.get("MEDIAMAN_EVENT_LOG_DIR") or "").strip() or None,
    }
    if source == "mcp" and not config["mcp_server_path"]:
        raise ConfigError("missing_or_empty:MEDIAMAN_MCP_SERVER_PATH")

    # Synthetic runs get their own state directory. Found in rehearsal: a
    # selftest pass stored a synthetic FAILED snapshot, and the next real
    # collection compared live data against invented data - which would have
    # emitted a phantom NAVIGATION_DATA_RECOVERED. Live state is never mixed
    # with fabricated state.
    if source == "selftest":
        config["state_dir"] = config["state_dir"] / "selftest"
    return config


def build_adapter(config: dict, logger: logging.Logger):
    """
    Return the article adapter. The real one is opt-in only.

    OpenClawAdapter.__init__ runs `openclaw --version` through subprocess, so
    building it is itself an outbound action. It is therefore constructed only
    on an explicit MEDIAMAN_ALLOW_LLM=true.
    """
    if not config["allow_llm"]:
        logger.info("STARTUP adapter=dry-run (MEDIAMAN_ALLOW_LLM not true)")
        return DryRunArticleAdapter(logger=logger)
    from mediaman.openclaw_adapter import OpenClawAdapter
    adapter = OpenClawAdapter()
    logger.info("STARTUP adapter=openclaw available=%s", adapter.is_available())
    return adapter


def collect_selftest_result(config: dict):
    """
    Build a synthetic CollectionResult to exercise the wiring without MCP.

    This exists because Midnight Rider's Pi is routinely off the boat, where no
    MCP server answers. It proves the unit runs end to end; it proves nothing
    about live data, and says so in the log.
    """
    from mediaman.mcp_collector import CollectionResult, CollectionStatus
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return CollectionResult(
        status=CollectionStatus.FAILED,
        race_id=config["race_id"],
        collection_start_at=now,
        collection_end_at=now,
        errors=["selftest_source: no MCP collection attempted"],
        warnings=["synthetic result - carries no navigation data"],
    )


def collect_mcp_result(config: dict, logger: logging.Logger):
    """Collect the present state through the real MCP chain."""
    from mediaman.mcp_client import MCPClient
    from mediaman.mcp_collector import MCPCollector
    client = MCPClient(server_path=config["mcp_server_path"])
    collector = MCPCollector(client=client, race_id=config["race_id"])
    result = collector.collect()
    logger.info(
        "DATA_IN collection status=%s facts=%d tools_ok=%d tools_failed=%d",
        getattr(result.status, "value", result.status),
        len(result.facts), len(result.tools_succeeded), len(result.tools_failed),
    )
    return result


def main(argv=None) -> int:
    env = os.environ
    try:
        config = parse_config(env)
    except ConfigError as exc:
        # No logger yet: configuration is refused before any file is created.
        print(f"CONFIG_REFUSED {exc}", file=sys.stderr)
        return 2

    try:
        logger = setup_service_logger(SERVICE_NAME, log_dir=config["log_dir"])
        _attach_module_logs(logger)
    except Exception as exc:
        # A logger that cannot be created is not a reason to run blind.
        print(f"LOGGER_SETUP_FAILED {type(exc).__name__}", file=sys.stderr)
        return 4

    logger.info(
        "STARTUP service=%s dry_run=true source=%s max_cycles=%d race_id=%s",
        SERVICE_NAME, config["source"], config["max_cycles"], config["race_id"],
    )

    state_dir = config["state_dir"]
    snapshot_store = None
    event_queue = None
    try:
        state_dir.mkdir(parents=True, exist_ok=True)

        snapshot_store = SnapshotStore(str(state_dir / SNAPSHOT_DB_FILENAME))
        snapshot_store.initialize()
        event_queue = EventQueue(db_path=str(state_dir / QUEUE_DB_FILENAME))
        event_queue.initialize()

        detector = EventDetector(logger=logger)
        orchestrator = EventOrchestrator(
            event_queue=event_queue,
            adapter=build_adapter(config, logger),
        )
        pipeline = EventPipeline(
            detector=detector,
            event_queue=event_queue,
            orchestrator=orchestrator,
            snapshot_store=snapshot_store,
            dry_run=True,
            max_cycles=config["max_cycles"],
            logger=logger,
        )

        if config["source"] == "selftest":
            logger.warning("DATA_IN selftest source: synthetic result, no live data")
            current = collect_selftest_result(config)
        else:
            try:
                current = collect_mcp_result(config, logger)
            except Exception as exc:
                logger.error(
                    "ERROR collection failed: %s - snapshot NOT advanced",
                    type(exc).__name__,
                )
                return 3

        result = pipeline.run_once(current)
        logger.info("DATA_OUT pass complete: %s", result.to_dict())
        logger.info("HEARTBEAT service=%s source=%s", SERVICE_NAME, config["source"])
        return 0
    except Exception as exc:
        logger.error("ERROR unexpected: %s", type(exc).__name__, exc_info=True)
        return 4
    finally:
        for store in (event_queue, snapshot_store):
            try:
                if store is not None:
                    store.close()
            except Exception:
                logger.warning("SHUTDOWN close failed for %s", type(store).__name__)
        logger.info("SHUTDOWN service=%s", SERVICE_NAME)
        # Flush rather than close: a closed handler would break the parent
        # logger for any later call in the same process, and this guards
        # against losing the last lines if the process is killed abruptly.
        for handler in logger.handlers:
            try:
                handler.flush()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
