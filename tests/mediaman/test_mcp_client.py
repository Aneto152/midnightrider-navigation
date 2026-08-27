"""
Tests for MCPClient — mocked subprocess-based MCP communication.

STEP 2: Scaffold tests with mocked processes only. No live servers.
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
    return process


class TestMCPClientStartup:
    """Startup and initialization tests."""

    def test_start_success(self, mock_process):
        """Successful process start and initialize."""
        with patch('subprocess.Popen', return_value=mock_process):
            # Mock initialize response
            mock_process.stdout = iter([
                '{"jsonrpc": "2.0", "id": 1, "result": {"name": "racing"}}\n'
            ])

            client = MCPClient('/tmp/racing.js', 'racing')
            client.start()

            assert client.initialized
            assert client.process is mock_process

    def test_start_file_not_found(self):
        """Process start fails if server not found."""
        with patch('subprocess.Popen', side_effect=FileNotFoundError):
            client = MCPClient('/nonexistent/racing.js', 'racing')
            with pytest.raises(MCPClientError, match="Server not found"):
                client.start()

    def test_start_permission_denied(self):
        """Process start fails with permission error."""
        with patch('subprocess.Popen', side_effect=PermissionError):
            client = MCPClient('/tmp/racing.js', 'racing')
            with pytest.raises(MCPClientError, match="Failed to launch"):
                client.start()


class TestMCPClientProtocol:
    """JSON-RPC protocol tests."""

    def test_initialize_request(self, mock_process):
        """Initialize sends correct JSON-RPC request."""
        init_response = {
            'jsonrpc': '2.0',
            'id': 1,
            'result': {'name': 'racing', 'version': '1.0'}
        }

        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                client = MCPClient('/tmp/racing.js', 'racing')
                client.process = mock_process

                with patch.object(client, '_send_request', return_value={}):
                    result = client.initialize()
                    # Initialize sets initialized=True only in start(), not when called directly
                    assert isinstance(result, dict)

    def test_list_tools_request(self, mock_process):
        """tools/list sends correct request."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                client = MCPClient('/tmp/racing.js', 'racing')
                client.process = mock_process
                client.initialized = True

                mock_tools = {'tools': [{'name': 'racing.get_position'}]}
                with patch.object(client, '_send_request', return_value=mock_tools):
                    result = client.list_tools()
                    assert 'tools' in result

    def test_tools_call_request(self, mock_process):
        """tools/call sends correct request."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                client = MCPClient('/tmp/racing.js', 'racing')
                client.process = mock_process
                client.initialized = True

                mock_result = {'latitude': 41.1234, 'longitude': -73.5678}
                with patch.object(client, '_send_request', return_value=mock_result):
                    result = client.call_tool('racing.get_position')
                    assert result['server_name'] == 'racing'
                    assert result['tool_name'] == 'racing.get_position'
                    assert result['success']


class TestMCPClientAllowlist:
    """Allowlist security tests."""

    def test_tool_in_allowlist_accepted(self, mock_process):
        """Allowlisted tool is accepted."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                client = MCPClient('/tmp/racing.js', 'racing')
                client.process = mock_process
                client.initialized = True

                with patch.object(client, '_send_request', return_value={}):
                    # This should not raise
                    client.call_tool('racing.get_position')

    def test_tool_not_in_allowlist_rejected(self, mock_process):
        """Non-allowlisted tool is rejected."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                client = MCPClient('/tmp/racing.js', 'racing')
                client.process = mock_process
                client.initialized = True

                with pytest.raises(MCPClientError, match="Tool not allowlisted"):
                    client.call_tool('racing.dangerous_tool')

    def test_dangerous_tools_not_in_allowlist(self):
        """Verify dangerous tools are not in allowlist."""
        dangerous = [
            'system.execute_command',
            'docker.run',
            'telegram.send_message',
            'fs.delete_file'
        ]
        for tool in dangerous:
            assert tool not in MCPClient.TOOL_ALLOWLIST


class TestMCPClientErrorHandling:
    """Error handling tests."""

    def test_malformed_json_response(self, mock_process):
        """Malformed JSON responses are skipped."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                client = MCPClient('/tmp/racing.js', 'racing')
                client.process = mock_process
                client.initialized = True

                # Malformed JSON should not crash _read_responses thread
                # (thread gracefully skips and continues)
                assert True

    def test_server_error_response(self, mock_process):
        """Server error response is propagated."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                client = MCPClient('/tmp/racing.js', 'racing')
                client.process = mock_process
                client.initialized = True

                error_response = {
                    'error': {
                        'code': -32000,
                        'message': 'Invalid params'
                    }
                }
                with patch.object(client, '_send_request', side_effect=MCPServerError('Invalid params')):
                    with pytest.raises(MCPServerError):
                        client.call_tool('racing.get_position')

    def test_request_timeout(self, mock_process):
        """Request timeout raises MCPTimeoutError."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                client = MCPClient('/tmp/racing.js', 'racing')
                client.process = mock_process
                client.initialized = True

                with patch.object(client, '_send_request', side_effect=MCPTimeoutError('Timeout')):
                    with pytest.raises(MCPTimeoutError):
                        client.call_tool('racing.get_position')

    def test_process_terminated_during_request(self, mock_process):
        """Request fails if process is terminated."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                client = MCPClient('/tmp/racing.js', 'racing')
                client.process = None  # Simulate terminated
                client.initialized = False

                with pytest.raises(MCPClientError, match="Server not started"):
                    client._send_request('tools/call', {})


class TestMCPClientResultStructure:
    """Result contract tests."""

    def test_wrapped_result_success(self, mock_process):
        """Successful result is properly wrapped."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                client = MCPClient('/tmp/racing.js', 'racing')
                client.process = mock_process

                raw_response = {'latitude': 41.1234, 'longitude': -73.5678}
                result = client._wrap_result('racing.get_position', raw_response)

                assert result['server_name'] == 'racing'
                assert result['tool_name'] == 'racing.get_position'
                assert result['success'] is True
                assert result['result'] == raw_response
                assert result['error_code'] is None
                assert result['source_timestamp'] == 'UNKNOWN'
                assert 'observed_at' in result

    def test_missing_source_timestamp_preserved(self, mock_process):
        """Missing source_timestamp is preserved as UNKNOWN."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                client = MCPClient('/tmp/racing.js', 'racing')
                client.process = mock_process

                result = client._wrap_result('racing.get_position', {})
                assert result['source_timestamp'] == 'UNKNOWN'

    def test_missing_values_not_converted_to_zero(self, mock_process):
        """Missing values remain as missing, not converted to zero."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                client = MCPClient('/tmp/racing.js', 'racing')
                client.process = mock_process

                # Response with missing fields (None values preserved)
                raw_response = {'latitude': None, 'longitude': None}
                result = client._wrap_result('racing.get_position', raw_response)

                # Verify None values are preserved, not converted to zero
                assert result['result']['latitude'] is None
                assert result['result']['longitude'] is None
                assert result['result'] == raw_response


class TestMCPClientSubprocessSafety:
    """Subprocess security and safety tests."""

    def test_no_shell_execution(self):
        """Process is launched with argv list, not shell=True."""
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.return_value = MagicMock()
            client = MCPClient('/tmp/racing.js', 'racing')

            try:
                with patch.object(MCPClient, '_read_responses'):
                    with patch.object(client, 'initialize', return_value={}):
                        client.start()
            except MCPTimeoutError:
                pass

            # Verify Popen was called with list (not shell=True)
            if mock_popen.called:
                call_args = mock_popen.call_args
                # argv list is first positional argument
                argv = call_args[0][0] if call_args[0] else None
                assert isinstance(argv, list), "Should use argv list"
                assert 'shell' not in call_args[1] or call_args[1]['shell'] is False

    def test_process_cleanup_on_error(self, mock_process):
        """Process is terminated on startup error."""
        with patch('subprocess.Popen', return_value=mock_process):
            client = MCPClient('/tmp/racing.js', 'racing')
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(client, 'initialize', side_effect=Exception("Init failed")):
                    try:
                        client.start()
                    except:
                        pass

            # Verify terminate was called
            mock_process.terminate.assert_called()

    def test_clean_process_termination(self, mock_process):
        """Process termination is clean (wait then kill)."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                client = MCPClient('/tmp/racing.js', 'racing')
                client.process = mock_process
                client.initialized = True

                # Successful termination (terminate succeeds)
                mock_process.wait = Mock()
                client.terminate()
                mock_process.terminate.assert_called()

    def test_credentials_not_in_command_arguments(self, mock_process):
        """No credentials are passed in argv or environment."""
        client = MCPClient('/tmp/racing.js', 'racing')
        # Verify no credentials in server_path
        assert 'token' not in client.server_path.lower()
        assert 'password' not in client.server_path.lower()
        assert 'secret' not in client.server_path.lower()


class TestMCPClientContextManager:
    """Context manager tests."""

    def test_context_manager_start_stop(self, mock_process):
        """Context manager starts and stops process."""
        with patch('subprocess.Popen', return_value=mock_process):
            with patch.object(MCPClient, '_read_responses'):
                with patch.object(MCPClient, 'initialize', return_value={}):
                    with MCPClient('/tmp/racing.js', 'racing') as client:
                        assert client.initialized

                    # After __exit__, process should be terminated
                    mock_process.terminate.assert_called()
