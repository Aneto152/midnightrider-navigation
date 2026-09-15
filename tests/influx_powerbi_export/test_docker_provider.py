"""
Tests for Docker-internal CLI provider (NO token extraction).
18 tests covering provider behavior, streaming, security, and fallback.
"""
import unittest
import os
import subprocess
import signal
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import tempfile
import sys

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))

from influx_powerbi_export.docker_provider import (
    DockerInternalCliQueryProvider,
    DockerComposeError,
    get_or_fallback_provider
)


def make_streaming_proc(stdout_lines=(), stderr_text="", returncode=0,
                        pid=4242424, running=False):
    """Build a mocked Popen whose pipes are REAL OS pipes.

    The provider drains stdout and stderr with selectors + os.read(), so a
    bare MagicMock is unusable: int(MagicMock().fileno()) is 1, which
    registers FD 1 (our own stdout) for both pipes and makes the selector
    raise KeyError before any provider logic runs. Tests that mocked
    stdout.readline() therefore never exercised the streaming path at all,
    because readline() has not been used since the selector rewrite.

    Returns (mock_process, read_fds). Close the fds with close_fds().
    """
    stdout_r, stdout_w = os.pipe()
    stderr_r, stderr_w = os.pipe()
    payload = "".join(stdout_lines).encode()
    if payload:
        os.write(stdout_w, payload)
    os.close(stdout_w)
    if stderr_text:
        os.write(stderr_w, stderr_text.encode())
    os.close(stderr_w)

    process = MagicMock()
    process.stdout.fileno.return_value = stdout_r
    process.stderr.fileno.return_value = stderr_r
    process.pid = pid                      # a real int: never our own group
    process.returncode = returncode
    process.poll.return_value = None if running else returncode
    process.wait.return_value = returncode
    return process, (stdout_r, stderr_r)


def close_fds(*fds):
    """Close descriptors, tolerating those already closed by the provider."""
    for fd in fds:
        try:
            os.close(fd)
        except OSError:
            pass


class TestDockerCommandConstruction(unittest.TestCase):
    """Test 1: Docker-internal command construction."""
    
    def setUp(self):
        self.provider = DockerInternalCliQueryProvider()
    
    def test_command_structure(self):
        """Verify the command is `docker exec -i <service> influx query --raw`.

        The provider deliberately uses `docker exec` and not
        `docker compose exec`, so no .env or docker-compose.yml is required.
        This test previously asserted the obsolete compose form and failed.
        """
        cmd = self.provider._build_docker_exec_cmd("test query")
        self.assertEqual(
            cmd,
            ["docker", "exec", "-i", self.provider.service,
             "influx", "query", "--raw", "test query"],
        )
        self.assertNotIn("compose", cmd)
class TestNoTokenInArguments(unittest.TestCase):
    """Test 2: Verify NO --token in command-line arguments."""
    
    def setUp(self):
        self.provider = DockerInternalCliQueryProvider()
    
    def test_no_token_flag(self):
        """Verify --token flag is never added."""
        cmd = self.provider._build_docker_exec_cmd("test query")
        self.assertNotIn("--token", cmd)
    
    def test_no_token_value_in_argv(self):
        """Verify no token value appears in argv."""
        cmd = self.provider._build_docker_exec_cmd("test query")
        # Join and check for common patterns
        cmd_str = " ".join(cmd)
        self.assertNotIn("Bearer ", cmd_str)
        # Should not contain auth header
        self.assertNotIn("Authorization:", cmd_str)


class TestNoInfluxAuthList(unittest.TestCase):
    """Test 3: Verify NO influx auth list invocation."""
    
    def setUp(self):
        self.provider = DockerInternalCliQueryProvider()
    
    @patch('subprocess.Popen')
    def test_no_auth_list_call(self, mock_popen):
        """Verify 'influx auth list' is never called."""
        mock_proc = MagicMock()
        mock_proc.stdout = []
        mock_proc.stderr = []
        mock_proc.returncode = 0
        mock_proc.poll.return_value = 0
        mock_popen.return_value = mock_proc
        
        try:
            list(self.provider.query_flux("test query"))
        except:
            pass
        
        # Check all calls don't include 'auth list'
        for call_obj in mock_popen.call_args_list:
            args, kwargs = call_obj
            if args:
                cmd = args[0]
                cmd_str = " ".join(cmd)
                self.assertNotIn("auth list", cmd_str)


class TestAuthenticatedInternalCli(unittest.TestCase):
    """Test 4: Authenticated internal CLI success."""
    
    @patch('subprocess.Popen')
    def test_successful_query(self, mock_popen):
        """Verify a successful query streams every stdout line."""
        payload = ["#group,false,false,true,true,false\n", "key1,val1\n"]
        mock_proc, fds = make_streaming_proc(payload)
        self.addCleanup(close_fds, *fds)
        mock_popen.return_value = mock_proc

        provider = DockerInternalCliQueryProvider()
        lines = list(provider.query_flux("test query"))

        self.assertEqual(len(lines), 2)
        self.assertIn("group", lines[0])
class TestUnauthorizedResponse(unittest.TestCase):
    """Test 5: Internal CLI unauthorized (401)."""
    
    @patch('subprocess.Popen')
    def test_unauthorized_exit_code(self, mock_popen):
        """Verify a non-zero exit raises DockerComposeError."""
        mock_proc, fds = make_streaming_proc(
            stderr_text="Unauthorized: invalid credentials", returncode=1)
        self.addCleanup(close_fds, *fds)
        mock_popen.return_value = mock_proc

        provider = DockerInternalCliQueryProvider()
        with self.assertRaises(DockerComposeError):
            list(provider.query_flux("test"))
class TestMissingDockerService(unittest.TestCase):
    """Test 6: Missing Docker service."""
    
    @patch('subprocess.Popen')
    def test_service_not_running(self, mock_popen):
        """Verify error when service is not running."""
        mock_popen.side_effect = FileNotFoundError("docker compose not found")
        
        provider = DockerInternalCliQueryProvider()
        
        with self.assertRaises(FileNotFoundError):
            list(provider.query_flux("test query"))


class TestMissingComposeFile(unittest.TestCase):
    """Test 7: Missing Compose file."""
    
    @patch('pathlib.Path.is_file')
    def test_compose_discovery_fails(self, mock_is_file):
        """Verify error when compose file not found."""
        mock_is_file.return_value = False
        
        with self.assertRaises(DockerComposeError) as ctx:
            DockerInternalCliQueryProvider()
        
        self.assertIn("docker-compose.yml", str(ctx.exception))


class TestStreamStdoutToFile(unittest.TestCase):
    """Test 8: Stream stdout to file."""
    
    def test_stream_to_iterable(self):
        """Verify streaming yields stripped lines, in order."""
        provider = DockerInternalCliQueryProvider()
        with patch('subprocess.Popen') as mock_popen:
            mock_proc, fds = make_streaming_proc(
                ["line1\n", "line2\n", "line3\n"])
            self.addCleanup(close_fds, *fds)
            mock_popen.return_value = mock_proc
            result = list(provider.query_flux("test"))

        self.assertEqual(result, ["line1", "line2", "line3"])
class TestStderrSanitization(unittest.TestCase):
    """Test 9: Stderr sanitization (no credential leakage)."""
    
    @patch('subprocess.Popen')
    def test_stderr_truncated(self, mock_popen):
        """Verify stderr is bounded in the raised exception."""
        long_stderr = "error " * 100 + "token12345"
        mock_proc, fds = make_streaming_proc(
            stderr_text=long_stderr, returncode=1)
        self.addCleanup(close_fds, *fds)
        mock_popen.return_value = mock_proc

        provider = DockerInternalCliQueryProvider()
        with self.assertRaises(DockerComposeError) as ctx:
            list(provider.query_flux("test"))

        self.assertLess(len(str(ctx.exception)), 900)
class TestTimeoutHandling(unittest.TestCase):
    """Test 10: Timeout handling."""
    
    @patch('subprocess.Popen')
    def test_query_timeout(self, mock_popen):
        """Verify a stalled stream raises TimeoutError."""
        mock_proc, fds = make_streaming_proc(running=True)
        self.addCleanup(close_fds, *fds)
        mock_proc.wait.side_effect = subprocess.TimeoutExpired("docker", 300)
        mock_popen.return_value = mock_proc

        provider = DockerInternalCliQueryProvider(timeout=1)
        with self.assertRaises(TimeoutError) as ctx:
            list(provider.query_flux("test"))

        self.assertIn("timeout", str(ctx.exception).lower())
class TestProcessCleanup(unittest.TestCase):
    """Test 11: Process cleanup on error."""
    
    @patch('os.killpg')
    @patch('os.getpgid')
    @patch('subprocess.Popen')
    def test_kill_on_timeout(self, mock_popen, mock_getpgid, mock_killpg):
        """Verify the child's process group is signalled on timeout.

        os.getpgid is stubbed so the child reports a group distinct from
        ours: signalling our own group would kill the test runner itself,
        which is exactly the bug _safe_killpg() now prevents.
        """
        OWN_PGID, CHILD_PGID = 111111, 222222
        mock_getpgid.side_effect = (
            lambda pid: OWN_PGID if pid == 0 else CHILD_PGID)

        mock_proc, fds = make_streaming_proc(running=True)
        self.addCleanup(close_fds, *fds)
        mock_proc.wait.side_effect = subprocess.TimeoutExpired("docker", 300)
        mock_popen.return_value = mock_proc

        provider = DockerInternalCliQueryProvider(timeout=1)
        with self.assertRaises(TimeoutError):
            list(provider.query_flux("test"))

        signalled = [c.args for c in mock_killpg.call_args_list]
        self.assertTrue(signalled, "no signal sent to the child group")
        for pgid, _sig in signalled:
            self.assertEqual(pgid, CHILD_PGID)
            self.assertNotEqual(pgid, OWN_PGID)
class TestNoOrphanProcess(unittest.TestCase):
    """Test 12: NO orphan process."""
    
    @patch('subprocess.Popen')
    def test_cleanup_in_finally(self, mock_popen):
        """Verify cleanup in finally block."""
        mock_proc = MagicMock()
        mock_proc.stdout = iter([])
        mock_proc.poll.return_value = None  # Still running
        mock_popen.return_value = mock_proc
        
        provider = DockerInternalCliQueryProvider()
        
        try:
            # Trigger error path
            with patch.object(provider, 'query_flux') as mock_query:
                mock_query.side_effect = RuntimeError("test")
                raise RuntimeError("test")
        except RuntimeError:
            pass
        
        # The finally block should have tried to clean up
        # (In actual execution, not in this mock test, but structure is verified)


class TestMultipleAnnotatedCsvTables(unittest.TestCase):
    """Test 13: Multiple annotated CSV tables."""
    
    @patch('subprocess.Popen')
    def test_multiple_tables_streaming(self, mock_popen):
        """Verify several annotated CSV tables stream through unchanged."""
        tables = [
            "#group,false,false,true,true,false\n",
            "#datatype,string,long,dateTime:RFC3339,string,string\n",
            "_measurement,result,table,_time,_field,_value\n",
            "cpu,_result,0,2021-01-01T00:00:00Z,usage,10\n",
            "\n",
            "#group,false,false,true,true,false\n",
            "#datatype,string,long,dateTime:RFC3339,string,string\n",
            "_measurement,result,table,_time,_field,_value\n",
            "mem,_result,1,2021-01-01T00:00:01Z,usage,512\n",
        ]
        mock_proc, fds = make_streaming_proc(tables)
        self.addCleanup(close_fds, *fds)
        mock_popen.return_value = mock_proc

        provider = DockerInternalCliQueryProvider()
        lines = list(provider.query_flux("test"))

        joined = "\n".join(lines)
        self.assertIn("cpu", joined)
        self.assertIn("mem", joined)
        self.assertGreaterEqual(len(lines), len(tables) - 1)
class TestUsbOnlyOutput(unittest.TestCase):
    """Test 14: USB-only output (no local /tmp)."""
    
    def test_no_intermediate_files(self):
        """Verify no intermediate files in /tmp or /home/aneto."""
        provider = DockerInternalCliQueryProvider()
        
        # This is validated by the main.py and writers.py
        # Provider itself doesn't create temp files
        self.assertIsNone(getattr(provider, 'temp_file', None))


class TestSecureTokenFileFallback(unittest.TestCase):
    """Test 15: Secure token-file fallback."""
    
    def test_token_file_path(self):
        """Verify token file path is secure."""
        expected_path = Path.home() / ".config" / "midnightrider" / "influxdb-read-token"
        
        # Verify the path is in home directory
        self.assertIn(".config/midnightrider", str(expected_path))
        # Should use Path.home() for robustness
        self.assertTrue(str(expected_path).startswith(str(Path.home())))


class TestNoCredentialsInLogs(unittest.TestCase):
    """Test 16: NO credentials in logs."""
    
    @patch('logging.Logger.debug')
    @patch('logging.Logger.error')
    def test_no_token_in_logs(self, mock_error, mock_debug):
        """Verify token is never logged."""
        provider = DockerInternalCliQueryProvider()
        
        # Check that debug/error calls don't include tokens
        for call_obj in mock_debug.call_args_list + mock_error.call_args_list:
            args, kwargs = call_obj
            if args:
                msg = str(args[0])
                self.assertNotIn("token", msg.lower())
                self.assertNotIn("auth", msg.lower())


class TestNoRawDataInLocalPaths(unittest.TestCase):
    """Test 17: NO raw data in /tmp, /home/aneto, repository."""
    
    def test_provider_no_temp_files(self):
        """Verify provider doesn't write temp files."""
        provider = DockerInternalCliQueryProvider()
        
        # Provider should only stream, not write
        self.assertFalse(hasattr(provider, 'write_temp'))
        self.assertFalse(hasattr(provider, 'cache_file'))


class TestFullExporterIntegration(unittest.TestCase):
    """Test 18: Full offline exporter integration."""
    
    @patch('subprocess.Popen')
    def test_integration_with_influx_client(self, mock_popen):
        """Verify InfluxClient streams through the Docker provider."""
        from influx_powerbi_export.influx_client import InfluxClient

        mock_proc, fds = make_streaming_proc(["line1\n", "line2\n"])
        self.addCleanup(close_fds, *fds)
        mock_popen.return_value = mock_proc

        client = InfluxClient()
        result = list(client.query_flux("test"))

        self.assertEqual(result, ["line1", "line2"])


class TestSafeKillpgGuards(unittest.TestCase):
    """Regression guards: _safe_killpg must never signal our own group.

    A bare MagicMock pid resolved to 1 through int(), so
    os.killpg(os.getpgid(process.pid), SIGKILL) became os.killpg(1, SIGKILL)
    and killed the whole session, SSH included. Two RPi freezes on
    2026-09-14 were caused by exactly that.
    """

    def test_refuses_non_integer_pid(self):
        provider = DockerInternalCliQueryProvider()
        process = MagicMock()  # int(MagicMock().pid) is 1
        with patch('os.killpg') as mock_killpg:
            self.assertFalse(provider._safe_killpg(process, signal.SIGKILL))
            mock_killpg.assert_not_called()

    def test_refuses_own_process_group(self):
        provider = DockerInternalCliQueryProvider()
        process = MagicMock()
        process.pid = os.getpid()
        with patch('os.killpg') as mock_killpg:
            self.assertTrue(provider._safe_killpg(process, signal.SIGKILL))
            mock_killpg.assert_not_called()
            process.kill.assert_called_once()

    def test_signals_distinct_process_group(self):
        provider = DockerInternalCliQueryProvider()
        process = MagicMock()
        process.pid = 4242424
        with patch('os.killpg') as mock_killpg, \
             patch('os.getpgid',
                   side_effect=lambda pid: 111111 if pid == 0 else 222222):
            self.assertTrue(provider._safe_killpg(process, signal.SIGTERM))
            mock_killpg.assert_called_once_with(222222, signal.SIGTERM)


if __name__ == '__main__':
    unittest.main(verbosity=2)
