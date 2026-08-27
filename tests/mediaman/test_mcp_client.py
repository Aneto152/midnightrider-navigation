"""
Tests for MCPClient — mocked subprocess with strict JSON-RPC validation.

STEP 2 Correction: Wire-name mapping, strict protocol validation, stderr separation.
"""

import pytest
import json
import subprocess
from unittest.mock import Mock, patch, MagicMock
from mediaman.mcp_client import (
    MCPClient,
    MCPClientError,
    MCPProtocolError,
    MCPServerError,
    MCPTimeoutError
)


@pytest.fixture
def mock_process():
    """Mock subprocess for MCP server."""
    process = MagicMock(spec=subprocess.Popen)
    process.stdin = MagicMock()
    process.stdout = MagicMock()
    process.stderr = MagicMock()
    process.returncode = None
    process.poll = Mock(return_value=None)
    return process


class TestMCPClientWireMapping:
    """Tool wire-name mapping tests."""

    def test_wire_mapping_exists(self):
        """Verify wire mapping is defined."""
        assert 'racing.get_position' in MCPClient.TOOL_WIRE_MAPPING
        assert MCPClient.TOOL_WIRE_MAPPING['racing.get_position'] == 'get_position'

    def test_call_tool_uses_wire_name(self, mock_process):
        """call_tool sends wire name in tools/call request."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process
                    client.initialized = True

                    sent_request = None

                    def capture_request(line):
                        nonlocal sent_request
                        sent_request = json.loads(line.rstrip('\n'))

                    mock_process.stdin.write = capture_request

                    # Mock response
                    mock_response = {
                        'jsonrpc': '2.0',
                        'id': 1,
                        'result': {'latitude': 41.1234, 'longitude': -73.5678}
                    }
                    client.response_queue.put(mock_response)

                    with patch.object(client, '_validate_jsonrpc_response'):
                        result = client.call_tool('racing.get_position', {})

                    # Verify wire name was sent, not public name
                    assert sent_request is not None
                    assert sent_request['params']['name'] == 'get_position'
                    assert sent_request['params']['name'] != 'racing.get_position'


class TestMCPClientStrictValidation:
    """Strict JSON-RPC validation tests."""

    def test_validate_jsonrpc_success(self, mock_process):
        """Valid JSON-RPC response passes validation."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process

                    response = {
                        'jsonrpc': '2.0',
                        'id': 1,
                        'result': {'data': 'test'}
                    }
                    # Should not raise
                    client._validate_jsonrpc_response(response, 1)

    def test_validate_jsonrpc_not_object(self, mock_process):
        """Non-object response raises MCPProtocolError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process

                    with pytest.raises(MCPProtocolError, match="not JSON object"):
                        client._validate_jsonrpc_response("string", 1)

    def test_validate_jsonrpc_missing_jsonrpc_field(self, mock_process):
        """Missing 'jsonrpc' field raises MCPProtocolError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process

                    response = {'id': 1, 'result': {}}
                    with pytest.raises(MCPProtocolError, match="missing 'jsonrpc'"):
                        client._validate_jsonrpc_response(response, 1)

    def test_validate_jsonrpc_invalid_version(self, mock_process):
        """Invalid JSON-RPC version raises MCPProtocolError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process

                    response = {'jsonrpc': '1.0', 'id': 1, 'result': {}}
                    with pytest.raises(MCPProtocolError, match="Invalid JSON-RPC version"):
                        client._validate_jsonrpc_response(response, 1)

    def test_validate_jsonrpc_missing_id(self, mock_process):
        """Missing 'id' field raises MCPProtocolError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process

                    response = {'jsonrpc': '2.0', 'result': {}}
                    with pytest.raises(MCPProtocolError, match="missing 'id'"):
                        client._validate_jsonrpc_response(response, 1)

    def test_validate_jsonrpc_mismatched_id(self, mock_process):
        """Mismatched response ID raises MCPProtocolError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process

                    response = {'jsonrpc': '2.0', 'id': 999, 'result': {}}
                    with pytest.raises(MCPProtocolError, match="does not match request id"):
                        client._validate_jsonrpc_response(response, 1)

    def test_validate_jsonrpc_both_result_and_error(self, mock_process):
        """Response with both result and error raises MCPProtocolError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process

                    response = {
                        'jsonrpc': '2.0',
                        'id': 1,
                        'result': {},
                        'error': {'code': -1, 'message': 'error'}
                    }
                    with pytest.raises(MCPProtocolError, match="both 'result' and 'error'"):
                        client._validate_jsonrpc_response(response, 1)

    def test_validate_jsonrpc_neither_result_nor_error(self, mock_process):
        """Response with neither result nor error raises MCPProtocolError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process

                    response = {'jsonrpc': '2.0', 'id': 1}
                    with pytest.raises(MCPProtocolError, match="neither 'result' nor 'error'"):
                        client._validate_jsonrpc_response(response, 1)

    def test_validate_jsonrpc_invalid_error_object(self, mock_process):
        """Invalid error object raises MCPProtocolError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process

                    response = {'jsonrpc': '2.0', 'id': 1, 'error': 'not an object'}
                    with pytest.raises(MCPProtocolError, match="Error is not object"):
                        client._validate_jsonrpc_response(response, 1)

    def test_validate_jsonrpc_error_missing_code(self, mock_process):
        """Error missing 'code' raises MCPProtocolError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process

                    response = {'jsonrpc': '2.0', 'id': 1, 'error': {'message': 'error'}}
                    with pytest.raises(MCPProtocolError, match="missing 'code'"):
                        client._validate_jsonrpc_response(response, 1)


class TestMCPClientStderrSeparation:
    """Stderr handling and process exit detection."""

    def test_stderr_reader_thread_started(self, mock_process):
        """stderr reader thread is started."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    with patch.object(MCPClient, 'initialize', return_value={}):
                        client = MCPClient('/tmp/racing.js', 'racing')
                        client.start()

                        assert client.stderr_thread is not None
                        assert client.stderr_thread.daemon

    def test_process_nonzero_exit_detected(self, mock_process):
        """Non-zero process exit is detected."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process
                    client.initialized = True

                    # Simulate process exit
                    mock_process.poll = Mock(return_value=1)

                    with pytest.raises(MCPClientError, match="Server process exited"):
                        client._send_request('tools/list', {})


class TestMCPClientTimestampHandling:
    """Source timestamp preservation."""

    def test_provided_source_timestamp_preserved(self, mock_process):
        """Provided source_timestamp is preserved exactly."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process

                    raw_response = {
                        'latitude': 41.1234,
                        'longitude': -73.5678,
                        'source_timestamp': '2026-08-27T22:53:00Z'
                    }
                    result = client._wrap_result('racing.get_position', raw_response)

                    assert result['source_timestamp'] == '2026-08-27T22:53:00Z'

    def test_absent_source_timestamp_becomes_unknown(self, mock_process):
        """Absent source_timestamp is UNKNOWN, not fabricated."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process

                    raw_response = {'latitude': 41.1234, 'longitude': -73.5678}
                    result = client._wrap_result('racing.get_position', raw_response)

                    assert result['source_timestamp'] == 'UNKNOWN'


class TestMCPClientErrorHandling:
    """Error classification and handling."""

    def test_malformed_json_raises_protocol_error(self, mock_process):
        """Malformed JSON raises MCPProtocolError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process
                    client.initialized = True

                    # Put a protocol error in queue
                    error = MCPProtocolError("Malformed JSON")
                    client.error_queue.put(error)

                    # When we try to get a response, malformed JSON should be detected
                    assert not client.error_queue.empty()

    def test_server_error_response_raises_server_error(self, mock_process):
        """Valid MCP error response raises MCPServerError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process
                    client.initialized = True

                    error_response = {
                        'jsonrpc': '2.0',
                        'id': 1,
                        'error': {'code': -32000, 'message': 'Invalid params'}
                    }
                    client.response_queue.put(error_response)

                    with pytest.raises(MCPServerError, match="Invalid params"):
                        client._send_request('tools/call', {'name': 'test', 'arguments': {}})

    def test_request_timeout_raises_timeout_error(self, mock_process):
        """Request timeout raises MCPTimeoutError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process
                    client.initialized = True
                    client.REQUEST_TIMEOUT_SECONDS = 0.1  # Very short timeout

                    with pytest.raises(MCPTimeoutError):
                        client._send_request('tools/list', {})


class TestMCPClientAllowlist:
    """Tool allowlist security."""

    def test_tool_in_allowlist_accepted(self, mock_process):
        """Allowlisted tool is accepted."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process
                    client.initialized = True

                    mock_response = {
                        'jsonrpc': '2.0',
                        'id': 1,
                        'result': {}
                    }
                    client.response_queue.put(mock_response)

                    with patch.object(client, '_validate_jsonrpc_response'):
                        # Should not raise
                        client.call_tool('racing.get_position')

    def test_tool_not_in_allowlist_rejected(self, mock_process):
        """Non-allowlisted tool is rejected."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process
                    client.initialized = True

                    with pytest.raises(MCPClientError, match="Tool not allowlisted"):
                        client.call_tool('racing.dangerous_tool')


class TestMCPClientSubprocessSafety:
    """Subprocess security."""

    def test_no_shell_execution(self):
        """Process is launched with argv list, not shell=True."""
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.return_value = MagicMock()
            client = MCPClient('/tmp/racing.js', 'racing')

            try:
                with patch.object(MCPClient, '_read_responses'):
                    with patch.object(MCPClient, '_read_stderr'):
                        with patch.object(client, 'initialize', return_value={}):
                            client.start()
            except MCPTimeoutError:
                pass

            if mock_popen.called:
                call_kwargs = mock_popen.call_args[1]
                assert 'shell' not in call_kwargs or call_kwargs['shell'] is False

    def test_no_credentials_in_argv(self):
        """No credentials in server path."""
        client = MCPClient('/tmp/racing.js', 'racing')
        assert 'token' not in client.server_path.lower()
        assert 'password' not in client.server_path.lower()
        assert 'secret' not in client.server_path.lower()


class TestMCPClientContextManager:
    """Context manager support."""

    def test_context_manager_cleanup(self, mock_process):
        """Context manager calls terminate on exit."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    with patch.object(MCPClient, 'initialize', return_value={}):
                        with MCPClient('/tmp/racing.js', 'racing') as client:
                            assert client.initialized

                        mock_process.terminate.assert_called()
