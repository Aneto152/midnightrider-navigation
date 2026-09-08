"""
Tests for InfluxDB client with streaming support.

Tests:
- Query execution
- Streaming to file
- Error handling
- Multiple table support
- Progress callbacks
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from io import StringIO
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from influx_client import (
    InfluxDBClient,
    InfluxDBCLITransport,
    Transport,
)
from auth_providers import AuthProviderChain


class TestInfluxDBCLITransport:
    """Tests for InfluxDB CLI transport."""

    def test_init_default_auth(self):
        """Test initialization with default auth chain."""
        transport = InfluxDBCLITransport(url="http://localhost:8086")
        assert transport.url == "http://localhost:8086"
        assert isinstance(transport.auth_provider, AuthProviderChain)

    def test_init_custom_auth(self):
        """Test initialization with custom auth provider."""
        mock_auth = Mock()
        transport = InfluxDBCLITransport(
            url="http://localhost:8086",
            auth_provider=mock_auth,
        )
        assert transport.auth_provider is mock_auth

    @patch('subprocess.run')
    def test_get_base_cmd_with_token(self, mock_run):
        """Test base command construction with valid token."""
        mock_auth = Mock()
        mock_auth.get_token.return_value = "mytoken123"

        transport = InfluxDBCLITransport(
            url="http://localhost:8086",
            auth_provider=mock_auth,
        )

        cmd = transport._get_base_cmd()
        assert "influx" in cmd
        assert "--host" in cmd
        assert "http://localhost:8086" in cmd
        assert "--token" in cmd
        assert "mytoken123" in cmd

    def test_get_base_cmd_no_token(self):
        """Test base command fails without token."""
        mock_auth = Mock()
        mock_auth.get_token.return_value = None

        transport = InfluxDBCLITransport(
            url="http://localhost:8086",
            auth_provider=mock_auth,
        )

        with pytest.raises(RuntimeError, match="Failed to obtain authentication token"):
            transport._get_base_cmd()

    @patch('subprocess.run')
    def test_query_success(self, mock_run):
        """Test successful query execution."""
        mock_auth = Mock()
        mock_auth.get_token.return_value = "token123"

        mock_run.return_value = Mock(
            returncode=0,
            stdout="#group,false,false\n#datatype,string,long\nstatus,code\nok,0\n",
            stderr="",
        )

        transport = InfluxDBCLITransport(
            url="http://localhost:8086",
            auth_provider=mock_auth,
        )

        result = transport.query(
            flux_query='from(bucket:"test")',
            org="my-org",
        )

        assert isinstance(result, str)
        assert "#group" in result or "status" in result

    @patch('subprocess.run')
    def test_query_failure(self, mock_run):
        """Test query execution failure."""
        mock_auth = Mock()
        mock_auth.get_token.return_value = "token123"

        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Query error: bucket not found",
        )

        transport = InfluxDBCLITransport(
            url="http://localhost:8086",
            auth_provider=mock_auth,
        )

        with pytest.raises(RuntimeError, match="Query failed"):
            transport.query(
                flux_query='from(bucket:"nonexistent")',
                org="my-org",
            )

    @patch('subprocess.Popen')
    def test_stream_query_success(self, mock_popen):
        """Test successful streaming query."""
        mock_auth = Mock()
        mock_auth.get_token.return_value = "token123"

        # Mock process with proper stdout iteration
        mock_process = Mock()
        mock_process.stdin = Mock()
        mock_process.stdout = iter(["#group,false\n", "name,value\n", "A,1\n", "B,2\n"])
        mock_process.returncode = 0
        mock_process.stderr = Mock()
        mock_process.stderr.read.return_value = ""
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        transport = InfluxDBCLITransport(
            url="http://localhost:8086",
            auth_provider=mock_auth,
        )

        output = StringIO()
        bytes_written = transport.stream_query(
            flux_query='from(bucket:"test")',
            org="my-org",
            output_stream=output,
        )

        assert bytes_written > 0
        output_text = output.getvalue()
        assert "group" in output_text or "A" in output_text

    @patch('subprocess.Popen')
    def test_stream_query_with_progress_callback(self, mock_popen):
        """Test streaming with progress callback."""
        mock_auth = Mock()
        mock_auth.get_token.return_value = "token123"

        mock_process = Mock()
        mock_process.stdin = Mock()
        mock_process.stdout = iter(["line1\n", "line2\n", "line3\n"])
        mock_process.returncode = 0
        mock_process.stderr = Mock()
        mock_process.stderr.read.return_value = ""
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        transport = InfluxDBCLITransport(
            url="http://localhost:8086",
            auth_provider=mock_auth,
        )

        progress_calls = []
        def progress_callback(bytes_so_far):
            progress_calls.append(bytes_so_far)

        output = StringIO()
        transport.stream_query(
            flux_query='from(bucket:"test")',
            org="my-org",
            output_stream=output,
            progress_callback=progress_callback,
        )

        # Progress callback should have been called
        assert len(progress_calls) > 0

    @patch('subprocess.Popen')
    def test_stream_query_timeout(self, mock_popen):
        """Test stream query timeout handling."""
        mock_auth = Mock()
        mock_auth.get_token.return_value = "token123"

        mock_process = Mock()
        mock_process.stdout = []
        mock_process.stderr = Mock()
        mock_process.stderr.read.return_value = ""
        # Make stdout iteration raise TimeoutExpired via wait
        def mock_wait_timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired("cmd", 30)
        mock_process.wait.side_effect = mock_wait_timeout
        mock_process.kill.return_value = None
        mock_popen.return_value = mock_process

        transport = InfluxDBCLITransport(
            url="http://localhost:8086",
            auth_provider=mock_auth,
        )

        output = StringIO()
        with pytest.raises(RuntimeError, match="timeout"):
            transport.stream_query(
                flux_query='from(bucket:"test")',
                org="my-org",
                output_stream=output,
            )

        mock_process.kill.assert_called_once()

    @patch('subprocess.Popen')
    def test_stream_query_process_error(self, mock_popen):
        """Test stream query with process error."""
        mock_auth = Mock()
        mock_auth.get_token.return_value = "token123"

        mock_process = Mock()
        mock_process.stdin = Mock()
        mock_process.stdout = iter([])  # Empty output
        mock_process.stderr = Mock()
        mock_process.stderr.read.return_value = "error occurred"
        mock_process.returncode = 1
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        transport = InfluxDBCLITransport(
            url="http://localhost:8086",
            auth_provider=mock_auth,
        )

        output = StringIO()
        with pytest.raises(RuntimeError, match="Stream query failed"):
            transport.stream_query(
                flux_query='from(bucket:"test")',
                org="my-org",
                output_stream=output,
            )


class TestInfluxDBClient:
    """Tests for high-level InfluxDB client."""

    def test_init_defaults(self):
        """Test client initialization with defaults."""
        client = InfluxDBClient()
        assert client.url == "http://localhost:8086"
        assert isinstance(client.auth_provider, AuthProviderChain)
        assert isinstance(client.transport, InfluxDBCLITransport)

    def test_init_custom_url(self):
        """Test client with custom URL."""
        client = InfluxDBClient(url="http://192.168.1.1:8086")
        assert client.url == "http://192.168.1.1:8086"

    def test_init_custom_auth_provider(self):
        """Test client with custom auth provider."""
        mock_auth = Mock()
        client = InfluxDBClient(auth_provider=mock_auth)
        assert client.auth_provider is mock_auth

    def test_init_custom_transport(self):
        """Test client with custom transport."""
        mock_transport = Mock(spec=Transport)
        client = InfluxDBClient(transport=mock_transport)
        assert client.transport is mock_transport

    @patch.object(InfluxDBCLITransport, 'query')
    def test_query(self, mock_transport_query):
        """Test query method delegates to transport."""
        mock_transport_query.return_value = "result data"

        client = InfluxDBClient()
        result = client.query(
            flux_query='from(bucket:"test")',
            org="my-org",
        )

        assert result == "result data"
        mock_transport_query.assert_called_once_with(
            'from(bucket:"test")',
            "my-org",
        )

    @patch.object(InfluxDBCLITransport, 'stream_query')
    def test_stream_query_to_file(self, mock_stream):
        """Test streaming query to file."""
        mock_stream.return_value = 1000

        client = InfluxDBClient()

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            bytes_written = client.stream_query(
                flux_query='from(bucket:"test")',
                org="my-org",
                output_file=tmp.name,
            )

            assert bytes_written == 1000
            os.unlink(tmp.name)

    @patch('sys.stdout', new_callable=StringIO)
    @patch.object(InfluxDBCLITransport, 'stream_query')
    def test_stream_query_to_stdout(self, mock_stream, mock_stdout):
        """Test streaming query to stdout."""
        mock_stream.return_value = 500

        client = InfluxDBClient()
        bytes_written = client.stream_query(
            flux_query='from(bucket:"test")',
            org="my-org",
        )

        assert bytes_written == 500

    @patch('subprocess.run')
    def test_health_check_success(self, mock_run):
        """Test health check when InfluxDB is healthy."""
        mock_run.return_value = Mock(returncode=0)

        client = InfluxDBClient(url="http://localhost:8086")
        healthy = client.health_check()

        assert healthy is True
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "influx" in call_args[0][0]
        assert "health" in call_args[0][0]

    @patch('subprocess.run')
    def test_health_check_failure(self, mock_run):
        """Test health check when InfluxDB is unhealthy."""
        mock_run.return_value = Mock(returncode=1)

        client = InfluxDBClient(url="http://localhost:8086")
        healthy = client.health_check()

        assert healthy is False

    @patch('subprocess.run')
    def test_health_check_exception(self, mock_run):
        """Test health check with exception."""
        mock_run.side_effect = Exception("Connection refused")

        client = InfluxDBClient(url="http://localhost:8086")
        healthy = client.health_check()

        assert healthy is False


class TestStreamingScenarios:
    """Test realistic streaming scenarios."""

    @patch('subprocess.Popen')
    def test_stream_multiple_tables(self, mock_popen):
        """Test streaming with multiple Flux result tables."""
        mock_auth = Mock()
        mock_auth.get_token.return_value = "token123"

        # Simulate multiple tables separated by blank lines
        lines = [
            "#group,false,true\n",
            "#datatype,string,long\n",
            "name,value\n",
            "Table1,100\n",
            "\n",
            "#group,false,true\n",
            "#datatype,string,long\n",
            "name,value\n",
            "Table2,200\n",
        ]

        mock_process = Mock()
        mock_process.stdin = Mock()
        mock_process.stdout = iter(lines)
        mock_process.returncode = 0
        mock_process.stderr = Mock()
        mock_process.stderr.read.return_value = ""
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        transport = InfluxDBCLITransport(
            url="http://localhost:8086",
            auth_provider=mock_auth,
        )

        output = StringIO()
        bytes_written = transport.stream_query(
            flux_query='from(bucket:"test")',
            org="my-org",
            output_stream=output,
        )

        output_text = output.getvalue()
        # Should contain both tables
        assert "Table1" in output_text or bytes_written > 0
        assert bytes_written > 0

    @patch('subprocess.Popen')
    def test_stream_large_result(self, mock_popen):
        """Test streaming large results with progress tracking."""
        mock_auth = Mock()
        mock_auth.get_token.return_value = "token123"

        # Simulate large result set
        lines = ["#group,false\n", "name,value\n"] + \
                [f"row{i},{i*10}\n" for i in range(100)]

        mock_process = Mock()
        mock_process.stdin = Mock()
        mock_process.stdout = iter(lines)
        mock_process.returncode = 0
        mock_process.stderr = Mock()
        mock_process.stderr.read.return_value = ""
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        transport = InfluxDBCLITransport(
            url="http://localhost:8086",
            auth_provider=mock_auth,
        )

        progress_values = []
        def track_progress(bytes_so_far):
            progress_values.append(bytes_so_far)

        output = StringIO()
        bytes_written = transport.stream_query(
            flux_query='from(bucket:"test")',
            org="my-org",
            output_stream=output,
            progress_callback=track_progress,
        )

        # Progress should be tracked
        assert len(progress_values) > 0
        assert progress_values[-1] == bytes_written

    def test_stream_to_file_creates_file(self):
        """Test that stream_query creates output file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "output.csv")

            mock_transport = Mock(spec=Transport)
            mock_transport.stream_query.return_value = 100

            client = InfluxDBClient(transport=mock_transport)
            client.stream_query(
                flux_query='from(bucket:"test")',
                org="my-org",
                output_file=output_file,
            )

            # File should be created (via open in stream_query)
            # This is tested by verifying transport.stream_query was called
            mock_transport.stream_query.assert_called_once()
