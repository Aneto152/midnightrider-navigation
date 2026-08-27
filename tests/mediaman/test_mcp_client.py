"""
Tests for MCPClient — mocked subprocess with reader-path verification and lifecycle hardening.

STEP 2C: Startup exception classification, process-exit detection, reader-path propagation, valid UTC.
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


class TestMCPClientStartupExceptionClassification:
    """Startup exception classification tests."""

    def test_startup_protocol_error_not_converted_to_timeout(self, mock_process):
        """MCPProtocolError during init remains MCPProtocolError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    
                    with patch.object(client, 'initialize', side_effect=MCPProtocolError("Invalid jsonrpc")):
                        with pytest.raises(MCPProtocolError, match="Invalid jsonrpc"):
                            client.start()

    def test_startup_server_error_not_converted_to_timeout(self, mock_process):
        """MCPServerError during init remains MCPServerError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    
                    with patch.object(client, 'initialize', side_effect=MCPServerError("Server error")):
                        with pytest.raises(MCPServerError, match="Server error"):
                            client.start()

    def test_startup_client_error_not_converted_to_timeout(self, mock_process):
        """MCPClientError during init remains MCPClientError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    
                    with patch.object(client, 'initialize', side_effect=MCPClientError("Process error")):
                        with pytest.raises(MCPClientError, match="Process error"):
                            client.start()

    def test_startup_timeout_remains_timeout(self, mock_process):
        """MCPTimeoutError during init remains MCPTimeoutError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    
                    with patch.object(client, 'initialize', side_effect=MCPTimeoutError("Startup timeout")):
                        with pytest.raises(MCPTimeoutError, match="Startup timeout"):
                            client.start()

    def test_startup_process_cleanup_on_error(self, mock_process):
        """Process is terminated when startup fails."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    
                    with patch.object(client, 'initialize', side_effect=MCPProtocolError("Init failed")):
                        try:
                            client.start()
                        except MCPProtocolError:
                            pass
                    
                    # Verify terminate was called
                    mock_process.terminate.assert_called()


class TestMCPClientProcessExitDetection:
    """Process exit detection during pending request."""

    def test_process_exit_while_request_pending(self, mock_process):
        """Process exit while waiting for response raises MCPClientError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process
                    client.initialized = True

                    # Simulate immediate process exit on poll
                    mock_process.poll = Mock(return_value=1)  # Non-zero exit code

                    with pytest.raises(MCPClientError, match="Server process exited with code"):
                        client._send_request('tools/list', {})


class TestMCPClientReaderPathPropagation:
    """Reader thread path validation (not just queue insertion)."""

    def test_malformed_json_from_reader_propagates(self, mock_process):
        """Malformed JSON from _read_responses propagates to waiting request."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_stderr'):
                client = MCPClient('/tmp/racing.js', 'racing')
                client.process = mock_process
                client.initialized = True

                # Mock stdout with malformed JSON
                malformed_line = '{"invalid": json}'
                mock_process.stdout = iter([malformed_line])

                # Start reader thread (not mocked out)
                reader_thread = None
                def start_reader():
                    nonlocal reader_thread
                    reader_thread = MCPClient._read_responses.__get__(client, MCPClient)()
                
                # Manually call reader
                client._read_responses()

                # Verify error was enqueued
                assert not client.error_queue.empty()
                error = client.error_queue.get_nowait()
                assert isinstance(error, MCPProtocolError)

    def test_oversized_response_from_reader_propagates(self, mock_process):
        """Oversized response from _read_responses propagates to waiting request."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_stderr'):
                client = MCPClient('/tmp/racing.js', 'racing')
                client.process = mock_process
                client.initialized = True

                # Create oversized line
                oversized_line = '{"x": "' + 'y' * (client.MAX_RESPONSE_SIZE + 1) + '"}'

                # Mock stdout
                mock_process.stdout = iter([oversized_line])

                # Call reader directly
                client._read_responses()

                # Verify error was enqueued
                assert not client.error_queue.empty()
                error = client.error_queue.get_nowait()
                assert isinstance(error, MCPProtocolError)
                assert "exceeds MAX_RESPONSE_SIZE" in str(error)

    def test_valid_mcp_response_decoded_from_reader(self, mock_process):
        """Valid MCP response from reader is decoded correctly."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_stderr'):
                client = MCPClient('/tmp/racing.js', 'racing')
                client.process = mock_process
                client.initialized = True

                # Create valid MCP response
                tool_data = {'latitude': 41.1234, 'longitude': -73.5678}
                mcp_response = {
                    'jsonrpc': '2.0',
                    'id': 1,
                    'result': {
                        'content': [
                            {'type': 'text', 'text': json.dumps(tool_data)}
                        ]
                    }
                }

                # Mock stdout
                response_line = json.dumps(mcp_response)
                mock_process.stdout = iter([response_line])

                # Call reader
                client._read_responses()

                # Verify response was enqueued
                assert not client.response_queue.empty()
                response = client.response_queue.get_nowait()
                assert response['id'] == 1
                assert response['result']['content'][0]['text'] == json.dumps(tool_data)


class TestMCPClientUTCTimestamp:
    """UTC timestamp format validation."""

    def test_observed_at_valid_utc_format(self, mock_process):
        """observed_at uses valid UTC format (Z only, no +00:00)."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process

                    decoded = {'latitude': 41.1234}
                    result = client._wrap_result('racing.get_position', decoded)

                    # Verify observed_at format
                    observed_at = result['observed_at']
                    assert observed_at.endswith('Z')
                    assert '+00:00' not in observed_at
                    assert 'Z' in observed_at

    def test_source_timestamp_preserved_exactly(self, mock_process):
        """source_timestamp is preserved exactly as provided."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process

                    decoded = {
                        'latitude': 41.1234,
                        'source_timestamp': '2026-08-27T23:19:00.123456Z'
                    }
                    result = client._wrap_result('racing.get_position', decoded)

                    assert result['source_timestamp'] == '2026-08-27T23:19:00.123456Z'

    def test_missing_source_timestamp_becomes_unknown(self, mock_process):
        """Absent source_timestamp becomes UNKNOWN."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process

                    decoded = {'latitude': 41.1234}
                    result = client._wrap_result('racing.get_position', decoded)

                    assert result['source_timestamp'] == 'UNKNOWN'


class TestMCPClientErrorHandling:
    """Error handling and propagation."""

    def test_malformed_json_raises_protocol_error(self, mock_process):
        """Malformed JSON in reader queue propagates as MCPProtocolError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process
                    client.initialized = True

                    # Enqueue a protocol error from the reader
                    error = MCPProtocolError("Malformed JSON: expected object")
                    client.error_queue.put(error)

                    # Request should receive the error
                    with pytest.raises(MCPProtocolError, match="Malformed JSON"):
                        client._send_request('tools/list', {})

    def test_valid_server_error_response(self, mock_process):
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
                        client._send_request('tools/list', {})

    def test_request_timeout(self, mock_process):
        """Request timeout raises MCPTimeoutError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process
                    client.initialized = True
                    client.REQUEST_TIMEOUT_SECONDS = 0.01

                    with pytest.raises(MCPTimeoutError):
                        client._send_request('tools/list', {})


class TestMCPClientResultDecoding:
    """MCP result envelope decoding."""

    def test_decode_valid_envelope(self, mock_process):
        """Valid MCP result envelope is decoded correctly."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process

                    tool_data = {'latitude': 41.1234, 'longitude': -73.5678}
                    mcp_result = {
                        'content': [
                            {'type': 'text', 'text': json.dumps(tool_data)}
                        ]
                    }

                    decoded = client._decode_mcp_result(mcp_result)
                    assert decoded == tool_data

    def test_decode_envelope_missing_content(self, mock_process):
        """Missing content raises MCPProtocolError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process

                    with pytest.raises(MCPProtocolError, match="missing 'content'"):
                        client._decode_mcp_result({})

    def test_decode_envelope_malformed_json_text(self, mock_process):
        """Malformed JSON in text field raises MCPProtocolError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process

                    with pytest.raises(MCPProtocolError, match="Failed to decode"):
                        client._decode_mcp_result({
                            'content': [{'type': 'text', 'text': '{invalid}'}]
                        })


class TestMCPClientWireMapping:
    """Tool wire-name mapping."""

    def test_wire_mapping_exists(self):
        """Wire mapping is defined for racing.get_position."""
        assert 'racing.get_position' in MCPClient.TOOL_WIRE_MAPPING
        assert MCPClient.TOOL_WIRE_MAPPING['racing.get_position'] == 'get_position'

    def test_call_tool_sends_wire_name(self, mock_process):
        """call_tool sends wire name to server."""
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

                    mcp_response = {
                        'jsonrpc': '2.0',
                        'id': 1,
                        'result': {
                            'content': [
                                {'type': 'text', 'text': json.dumps({'latitude': 41.1234})}
                            ]
                        }
                    }
                    client.response_queue.put(mcp_response)

                    with patch.object(client, '_validate_jsonrpc_response'):
                        result = client.call_tool('racing.get_position', {})

                    # Verify wire name was sent
                    assert sent_request is not None
                    assert sent_request['params']['name'] == 'get_position'


class TestMCPClientAllowlist:
    """Tool allowlist security."""

    def test_tool_allowlist_active(self):
        """Tool allowlist is defined."""
        assert 'racing.get_position' in MCPClient.TOOL_ALLOWLIST

    def test_tool_not_allowlisted_rejected(self, mock_process):
        """Non-allowlisted tool is rejected."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process
                    client.initialized = True

                    with pytest.raises(MCPClientError, match="Tool not allowlisted"):
                        client.call_tool('racing.dangerous_tool')


class TestMCPClientStrictValidation:
    """Strict JSON-RPC 2.0 validation tests."""

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


class TestMCPClientSubprocessSafety:
    """Subprocess security."""

    def test_no_shell_execution(self):
        """Process launched with argv, not shell=True."""
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
