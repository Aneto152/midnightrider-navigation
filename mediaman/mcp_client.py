"""
MCP Client for MediaMan — Python subprocess-based JSON-RPC interface.

Communicates with Node MCP servers using JSON-RPC 2.0 over stdin/stdout.
Implements bounded timeouts, error handling, and allowlist security.

STEP 2 Scaffold: Mocked vertical slice only. No live InfluxDB, Signal K, Regatta, AIS.
"""

import json
import subprocess
import threading
import queue
import time
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone


class MCPClientError(Exception):
    """Base error for MCP communication failures."""
    pass


class MCPProtocolError(MCPClientError):
    """JSON-RPC protocol violation."""
    pass


class MCPServerError(MCPClientError):
    """MCP server returned error."""
    pass


class MCPTimeoutError(MCPClientError):
    """Request or startup timeout."""
    pass


class MCPClient:
    """
    Python MCP client communicating with Node MCP servers via JSON-RPC 2.0.

    Protocol:
    - JSON line-based requests/responses
    - JSON-RPC 2.0 framing
    - Subprocess launched with argv (no shell=True)
    - Bounded timeouts on startup and request
    - Separated stdout/stderr
    - Clean process termination

    Allowlist: Only safe, approved tools (START with racing.get_position only)
    """

    # SAFE TOOL ALLOWLIST
    TOOL_ALLOWLIST = {
        'racing.get_position': {
            'server': 'racing',
            'description': 'Current boat position (lat/lon from Signal K)',
            'safe': True,
            'requires_live_data': False  # For testing: will be mocked
        },
        # Additional tools to be added in future phases after audit
    }

    STARTUP_TIMEOUT_SECONDS = 10
    REQUEST_TIMEOUT_SECONDS = 5
    MAX_RESPONSE_SIZE = 1024 * 1024  # 1 MB

    def __init__(self, server_path: str, server_name: str):
        """
        Initialize MCP client.

        Args:
            server_path: Full path to Node MCP server executable
            server_name: Server identifier (e.g., 'racing')
        """
        self.server_path = server_path
        self.server_name = server_name
        self.process: Optional[subprocess.Popen] = None
        self.response_queue: queue.Queue = queue.Queue()
        self.reader_thread: Optional[threading.Thread] = None
        self.request_id = 0
        self.initialized = False

    def start(self) -> None:
        """
        Launch the MCP server process with bounded startup timeout.

        Raises:
            MCPClientError: if process fails to start
            MCPTimeoutError: if startup exceeds timeout
        """
        try:
            # Launch with argv list (no shell=True)
            self.process = subprocess.Popen(
                [self.server_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
        except FileNotFoundError as e:
            raise MCPClientError(f"Server not found: {self.server_path}") from e
        except OSError as e:
            raise MCPClientError(f"Failed to launch server: {e}") from e

        # Start reader thread for stdout
        self.reader_thread = threading.Thread(
            target=self._read_responses,
            daemon=True
        )
        self.reader_thread.start()

        # Initialize handshake with timeout
        try:
            self.initialize()
            self.initialized = True
        except Exception as e:
            self.terminate()
            raise MCPTimeoutError(f"Startup timeout or init failed: {e}") from e

    def initialize(self) -> Dict[str, Any]:
        """
        Send initialize request to MCP server.

        Returns:
            Server info response
        """
        response = self._send_request('initialize', {})
        return response

    def list_tools(self) -> Dict[str, Any]:
        """
        Request available tools from server.

        Returns:
            tools/list response
        """
        response = self._send_request('tools/list', {})
        return response

    def call_tool(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Call a tool on the MCP server.

        Args:
            tool_name: Fully qualified tool name (e.g., 'racing.get_position')
            arguments: Tool arguments

        Returns:
            Structured MCP result with source tracking

        Raises:
            MCPClientError: if tool not in allowlist or server error occurs
        """
        # Allowlist check
        if tool_name not in self.TOOL_ALLOWLIST:
            raise MCPClientError(f"Tool not allowlisted: {tool_name}")

        if arguments is None:
            arguments = {}

        # Call tool
        response = self._send_request(
            'tools/call',
            {'name': tool_name, 'arguments': arguments}
        )

        # Wrap in structured result
        return self._wrap_result(tool_name, response)

    def _send_request(
        self,
        method: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send JSON-RPC request and wait for response with timeout.

        Args:
            method: JSON-RPC method
            params: Method parameters

        Returns:
            Response (result or error)

        Raises:
            MCPProtocolError: if malformed JSON-RPC
            MCPServerError: if server returned error
            MCPTimeoutError: if response timeout
        """
        if not self.process or not self.process.stdin:
            raise MCPClientError("Server not started")

        self.request_id += 1
        request_id = self.request_id

        request = {
            'jsonrpc': '2.0',
            'id': request_id,
            'method': method,
            'params': params
        }

        try:
            # Send request
            self.process.stdin.write(json.dumps(request) + '\n')
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            raise MCPClientError(f"Failed to send request: {e}") from e

        # Wait for response with timeout
        start_time = time.time()
        while True:
            elapsed = time.time() - start_time
            if elapsed > self.REQUEST_TIMEOUT_SECONDS:
                raise MCPTimeoutError(
                    f"Request timeout after {self.REQUEST_TIMEOUT_SECONDS}s"
                )

            try:
                response = self.response_queue.get(
                    timeout=self.REQUEST_TIMEOUT_SECONDS - elapsed
                )
                if response.get('id') == request_id:
                    # Check for error
                    if 'error' in response:
                        error = response['error']
                        raise MCPServerError(
                            f"Server error: {error.get('message', 'unknown')}"
                        )
                    return response.get('result', {})
                # Wrong response ID, put back and wait
                self.response_queue.put(response)
            except queue.Empty:
                raise MCPTimeoutError(
                    f"Request timeout after {self.REQUEST_TIMEOUT_SECONDS}s"
                )

    def _read_responses(self) -> None:
        """
        Background thread: read JSON-RPC responses from stdout.
        """
        if not self.process or not self.process.stdout:
            return

        for line in self.process.stdout:
            if not line.strip():
                continue
            try:
                response = json.loads(line)
                self.response_queue.put(response)
            except json.JSONDecodeError:
                # Malformed JSON, skip
                pass

    def _wrap_result(
        self,
        tool_name: str,
        raw_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Wrap raw MCP response in structured result contract.

        Returns:
            {
                server_name,
                tool_name,
                success,
                result,
                error_code,
                error_message,
                source,
                source_timestamp (UNKNOWN if not provided),
                observed_at,
                warnings
            }
        """
        result = {
            'server_name': self.server_name,
            'tool_name': tool_name,
            'success': True,
            'result': raw_response,
            'error_code': None,
            'error_message': None,
            'source': f'mcp:{self.server_name}',
            'source_timestamp': 'UNKNOWN',  # MCP servers don't return this yet
            'observed_at': datetime.now(timezone.utc).isoformat() + 'Z',
            'warnings': []
        }

        # Preserve missing values
        if raw_response is None:
            result['warnings'].append('Result is None (data unavailable)')

        return result

    def terminate(self) -> None:
        """
        Cleanly terminate the MCP server process.
        """
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            finally:
                self.process = None
                self.initialized = False

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.terminate()
        return False
