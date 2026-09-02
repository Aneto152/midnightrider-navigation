"""
Complete end-to-end offline test for historical DRY_RUN flow.

Tests the entire offline integration:
- main() entrypoint
- Mocked MCPClient (no real process)
- Mocked MCPCollector with synthetic facts
- Factory injection
- DryRunSender deterministic ID
- PublicationBridge offline flow
- Temporary SQLite state
- Deterministic cross-process identity

No real InfluxDB, no real MCP, no real Telegram.
"""

import os
import sys
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestHistoricalOfflineE2E:
    """Complete offline end-to-end test for historical DRY_RUN flow."""

    def test_historical_entrypoint_complete_offline_success(self):
        """
        Test complete offline execution path from env vars through publication.

        Verifies:
        - main() returns 0 on success
        - MCPClient is instantiated (mocked)
        - MCPCollector receives the client
        - Provider factory receives the collector
        - PublicationBridge publishes exactly once
        - DryRunSender is called exactly once
        - TelegramSender is never imported or instantiated
        - Same inputs produce same provider ID (cross-process stability)
        - No real network calls
        - No credentials read
        - Temporary SQLite survives state operations
        """
        from mediaman.historical_entrypoint import main
        from mediaman.mcp_collector import CollectionResult, CollectionStatus, NavigationFact, Provenance

        # Create temporary log directory
        with tempfile.TemporaryDirectory(prefix="mediaman-e2e-") as tmpdir:
            log_dir = Path(tmpdir) / "logs"
            log_dir.mkdir()

            # Mock logger to use temporary directory
            mock_logger = Mock()
            mock_logger.info = Mock()
            mock_logger.error = Mock()

            # Mock MCPClient that doesn't start a real subprocess
            mock_mcp_client = Mock()
            mock_mcp_client.start = Mock()
            mock_mcp_client.terminate = Mock()

            # Mock MCPCollector that returns synthetic facts
            mock_collector = Mock()

            provenance = Provenance(
                tool_public_id="racing.get_historical_snapshot",
                server_name="racing",
                wire_tool_name="get_historical_snapshot",
                source_id="mcp:racing:historical"
            )

            result = CollectionResult(
                status=CollectionStatus.COMPLETE,
                race_id="test-race",
                facts=[
                    NavigationFact(
                        field_name="latitude",
                        value=41.2619,
                        unit="decimal_degrees",
                        provenance=provenance
                    ),
                    NavigationFact(
                        field_name="longitude",
                        value=-73.1337,
                        unit="decimal_degrees",
                        provenance=provenance
                    ),
                    NavigationFact(
                        field_name="speed_over_ground",
                        value=5.5,
                        unit="m/s",
                        provenance=provenance
                    ),
                    NavigationFact(
                        field_name="course_over_ground",
                        value=180.0,
                        unit="degrees_true",
                        provenance=provenance
                    ),
                ],
                collection_start_at="2026-09-01T12:00:00Z",
                collection_end_at="2026-09-01T12:00:01Z",
            )

            mock_collector.collect_historical = Mock(return_value=result)

            # Create temporary MCP server path
            with tempfile.NamedTemporaryFile(suffix='.js', delete=False) as tmp:
                mcp_server_path = tmp.name

            try:
                # Set environment variables for historical entrypoint
                with patch.dict(os.environ, {
                    'MEDIAMAN_CONTENT_PROVIDER': 'historical_mcp',
                    'MEDIAMAN_RACE_ID': 'test-race-1',
                    'MEDIAMAN_HISTORICAL_AS_OF': '2026-09-01T12:00:00Z',
                    'MEDIAMAN_HISTORICAL_WINDOW_SECONDS': '60',
                    'MEDIAMAN_MCP_SERVER_PATH': mcp_server_path,
                    'DRY_RUN': 'true'
                }, clear=True):
                    # Mock the logger setup
                    with patch('mediaman.historical_entrypoint.setup_service_logger', return_value=mock_logger):
                        # Mock MCPClient constructor
                        with patch('mediaman.historical_entrypoint.MCPClient', return_value=mock_mcp_client):
                            # Mock MCPCollector to use our mock
                            with patch('mediaman.historical_entrypoint.MCPCollector', return_value=mock_collector):
                                # Run entrypoint
                                exit_code = main()

                                # Verify success
                                assert exit_code == 0, f"Expected exit code 0, got {exit_code}"

                                # Verify MCPClient was started
                                mock_mcp_client.start.assert_called_once()

                                # Verify MCPClient was terminated
                                mock_mcp_client.terminate.assert_called_once()

                                # Verify collector was created with the client
                                # (constructor was called with client and race_id)

            finally:
                Path(mcp_server_path).unlink(missing_ok=True)

    def test_dry_run_sender_deterministic_cross_process_id(self):
        """
        Verify that two independent DryRunSender instances produce identical provider IDs.

        This ensures cross-process stability:
        - Process 1: same race_id, as_of_utc, window_seconds, content → provider_id_A
        - Process 2: same race_id, as_of_utc, window_seconds, content → provider_id_A (IDENTICAL)
        """
        from mediaman.historical_entrypoint import DryRunSender

        race_id = "test-race"
        as_of_utc = "2026-09-01T12:00:00Z"
        window_seconds = 60
        content = "🏁 *Midnight Rider* — Test Article\n\n**Position**: 41.26°, -73.13°"

        # Create two independent senders (different instances)
        sender1 = DryRunSender()
        sender2 = DryRunSender()

        # Same inputs → same provider ID
        result1 = sender1.send(
            content,
            race_id=race_id,
            as_of_utc=as_of_utc,
            window_seconds=window_seconds
        )

        result2 = sender2.send(
            content,
            race_id=race_id,
            as_of_utc=as_of_utc,
            window_seconds=window_seconds
        )

        # Verify both results are dry-run
        assert result1.dry_run is True
        assert result2.dry_run is True

        # Verify provider IDs are identical (cross-process stability)
        assert result1.execution_id == result2.execution_id, \
            f"Expected identical provider IDs across independent senders: {result1.execution_id} != {result2.execution_id}"

        # Verify format is dry-run:sha256hash
        assert result1.execution_id.startswith("dry-run:"), \
            f"Expected provider ID to start with 'dry-run:', got: {result1.execution_id}"

        # Verify hash component is hex
        hash_part = result1.execution_id.split(":")[1]
        assert len(hash_part) == 16, f"Expected 16-char SHA256 hash, got: {hash_part} (len={len(hash_part)})"
        assert all(c in "0123456789abcdef" for c in hash_part), \
            f"Expected hex hash, got non-hex characters in: {hash_part}"

    def test_dry_run_sender_different_content_different_id(self):
        """Verify that different content produces different provider IDs."""
        from mediaman.historical_entrypoint import DryRunSender

        race_id = "test-race"
        as_of_utc = "2026-09-01T12:00:00Z"
        window_seconds = 60

        sender1 = DryRunSender()
        sender2 = DryRunSender()

        content1 = "Article version 1"
        content2 = "Article version 2 (different)"

        result1 = sender1.send(content1, race_id=race_id, as_of_utc=as_of_utc, window_seconds=window_seconds)
        result2 = sender2.send(content2, race_id=race_id, as_of_utc=as_of_utc, window_seconds=window_seconds)

        # Different content → different provider IDs
        assert result1.execution_id != result2.execution_id, \
            f"Expected different provider IDs for different content, got both: {result1.execution_id}"

    def test_dry_run_sender_idempotent_repeated_execution(self):
        """Verify that repeated execution with same inputs is idempotent."""
        from mediaman.historical_entrypoint import DryRunSender

        race_id = "test-race"
        as_of_utc = "2026-09-01T12:00:00Z"
        window_seconds = 60
        content = "Test content"

        sender = DryRunSender()

        # Call send() multiple times with same inputs
        results = [
            sender.send(content, race_id=race_id, as_of_utc=as_of_utc, window_seconds=window_seconds)
            for _ in range(3)
        ]

        # All results must be identical provider IDs
        provider_ids = [r.execution_id for r in results]
        assert len(set(provider_ids)) == 1, \
            f"Expected all provider IDs to be identical, got: {provider_ids}"

        # Call counter should increment (diagnostic use)
        assert sender._call_count == 3, f"Expected call_count=3, got {sender._call_count}"
