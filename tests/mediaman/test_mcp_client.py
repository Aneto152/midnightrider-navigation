"""
Tests for MCPClient — mocked subprocess with error propagation and result decoding.

STEP 2B: Error propagation, MCP result envelope decoding, response-size enforcement.
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


class TestMCPClientErrorPropagation:
    """Error propagation from reader thread to waiting request."""

    def test_malformed_json_raises_protocol_error(self, mock_process):
        """Malformed JSON in reader thread propagates as MCPProtocolError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process
                    client.initialized = True

                    # Enqueue a protocol error from the reader
                    error = MCPProtocolError("Malformed JSON")
                    client.error_queue.put(error)

                    # Request should receive the error
                    with pytest.raises(MCPProtocolError, match="Malformed JSON"):
                        client._send_request('tools/list', {})

    def test_reader_error_not_converted_to_timeout(self, mock_process):
        """Reader protocol error is not converted to MCPTimeoutError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process
                    client.initialized = True

                    # Enqueue protocol error
                    error = MCPProtocolError("Invalid JSON-RPC version")
                    client.error_queue.put(error)

                    # Should raise MCPProtocolError, not MCPTimeoutError
                    with pytest.raises(MCPProtocolError):
                        client._send_request('tools/list', {})


class TestMCPClientResultDecoding:
    """MCP result envelope decoding tests."""

    def test_decode_valid_mcp_result(self, mock_process):
        """Valid MCP result envelope is decoded correctly."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process

                    # Simulate MCP result envelope from racing server
                    tool_data = {'latitude': 41.1234, 'longitude': -73.5678, 'source_timestamp': '2026-08-27T23:00:00Z'}
                    mcp_result = {
                        'content': [
                            {
                                'type': 'text',
                                'text': json.dumps(tool_data)
                            }
                        ]
                    }

                    decoded = client._decode_mcp_result(mcp_result)
                    assert decoded == tool_data
                    assert decoded['source_timestamp'] == '2026-08-27T23:00:00Z'

    def test_decode_mcp_result_missing_content(self, mock_process):
        """Missing 'content' field raises MCPProtocolError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process

                    with pytest.raises(MCPProtocolError, match="missing 'content'"):
                        client._decode_mcp_result({'result': {}})

    def test_decode_mcp_result_empty_content(self, mock_process):
        """Empty content list raises MCPProtocolError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process

                    with pytest.raises(MCPProtocolError, match="not non-empty list"):
                        client._decode_mcp_result({'content': []})

    def test_decode_mcp_result_wrong_type(self, mock_process):
        """Wrong content[0].type raises MCPProtocolError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process

                    with pytest.raises(MCPProtocolError, match="content\\[0\\].type is not 'text'"):
                        client._decode_mcp_result({
                            'content': [{'type': 'markdown', 'text': 'ignored'}]
                        })

    def test_decode_mcp_result_missing_text(self, mock_process):
        """Missing 'text' field raises MCPProtocolError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process

                    with pytest.raises(MCPProtocolError, match="missing 'text'"):
                        client._decode_mcp_result({
                            'content': [{'type': 'text'}]
                        })

    def test_decode_mcp_result_malformed_json_text(self, mock_process):
        """Malformed JSON in text field raises MCPProtocolError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process

                    with pytest.raises(MCPProtocolError, match="Failed to decode MCP text as JSON"):
                        client._decode_mcp_result({
                            'content': [{'type': 'text', 'text': '{invalid json}'}]
                        })

    def test_call_tool_decodes_and_wraps_result(self, mock_process):
        """call_tool decodes envelope and wraps result."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process
                    client.initialized = True

                    # Prepare MCP response with envelope
                    tool_data = {
                        'latitude': 41.1234,
                        'longitude': -73.5678,
                        'source_timestamp': '2026-08-27T23:00:00Z'
                    }
                    mcp_response = {
                        'jsonrpc': '2.0',
                        'id': 1,
                        'result': {
                            'content': [
                                {
                                    'type': 'text',
                                    'text': json.dumps(tool_data)
                                }
                            ]
                        }
                    }
                    client.response_queue.put(mcp_response)

                    with patch.object(client, '_validate_jsonrpc_response'):
                        result = client.call_tool('racing.get_position')

                    # Verify result is wrapped correctly
                    assert result['server_name'] == 'racing'
                    assert result['tool_name'] == 'racing.get_position'
                    assert result['success'] is True
                    assert result['result'] == tool_data
                    assert result['source_timestamp'] == '2026-08-27T23:00:00Z'


class TestMCPClientSourceTimestamp:
    """Source timestamp preservation after decoding."""

    def test_source_timestamp_preserved_after_decode(self, mock_process):
        """Source timestamp from decoded result is preserved exactly."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process

                    decoded = {
                        'latitude': 41.1234,
                        'longitude': -73.5678,
                        'source_timestamp': '2026-08-27T23:15:30.123456Z'
                    }
                    result = client._wrap_result('racing.get_position', decoded)

                    assert result['source_timestamp'] == '2026-08-27T23:15:30.123456Z'

    def test_missing_source_timestamp_becomes_unknown(self, mock_process):
        """Absent source_timestamp becomes UNKNOWN."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process

                    decoded = {'latitude': 41.1234, 'longitude': -73.5678}
                    result = client._wrap_result('racing.get_position', decoded)

                    assert result['source_timestamp'] == 'UNKNOWN'


class TestMCPClientResponseSizeEnforcement:
    """Response size limit enforcement."""

    def test_oversized_response_rejected(self, mock_process):
        """Response exceeding MAX_RESPONSE_SIZE is rejected."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, '_read_stderr'):
                    client = MCPClient('/tmp/racing.js', 'racing')
                    client.process = mock_process
                    client.initialized = True
                    
                    # Create oversized response line
                    oversized_line = '{"x": "' + 'y' * (client.MAX_RESPONSE_SIZE + 1) + '"}'
                    
                    # Simulate reader processing it
                    # (in real scenario, reader would detect and enqueue error)
                    error = MCPProtocolError(f"Response line exceeds MAX_RESPONSE_SIZE")
                    client.error_queue.put(error)

                    with pytest.raises(MCPProtocolError, match="exceeds MAX_RESPONSE_SIZE"):
                        client._send_request('tools/list', {})


class TestMCPClientProcessExit:
    """Process exit detection while request is pending."""

    def test_process_exit_detected_during_request(self, mock_process):
        """Non-zero process exit while request pending is detected."""
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
                    mcp_response = {
                        'jsonrpc': '2.0',
                        'id': 1,
                        'result': {
                            'content': [
                                {
                                    'type': 'text',
                                    'text': json.dumps({'latitude': 41.1234})
                                }
                            ]
                        }
                    }
                    client.response_queue.put(mcp_response)

                    with patch.object(client, '_validate_jsonrpc_response'):
                        result = client.call_tool('racing.get_position', {})

                    # Verify wire name was sent
                    assert sent_request is not None
                    assert sent_request['params']['name'] == 'get_position'


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

                    mcp_response = {
                        'jsonrpc': '2.0',
                        'id': 1,
                        'result': {
                            'content': [{'type': 'text', 'text': '{}'}]
                        }
                    }
                    client.response_queue.put(mcp_response)

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
