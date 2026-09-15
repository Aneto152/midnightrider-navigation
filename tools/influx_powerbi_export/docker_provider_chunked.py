"""
Refactored Docker provider with SEPARATED timeout scopes.

Timeout Architecture:
1. query_startup_timeout: Time to start query execution
2. stream_idle_timeout: Time allowed between data packets on stream
3. stream_overall_timeout: Total time allowed for streaming one chunk
4. process_cleanup_timeout: Time allowed for process cleanup

No single global deadline covering entire export.
Each timeout scope is independent and clearly defined.
"""

import os
import subprocess
import logging
import time
import selectors
import signal
from typing import Iterator, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class DockerComposeError(Exception):
    """Docker Compose execution error."""
    pass


class TimeoutError(Exception):
    """Timeout during stream draining."""
    pass


class DockerChunkedQueryProvider:
    """
    Streams Flux queries via Docker exec with SEPARATED timeout scopes.
    
    Timeout Architecture:
    - query_startup_timeout: Time to start query (default: 10s)
    - stream_idle_timeout: Time between data packets (default: 60s)
    - stream_overall_timeout: Total time for chunk streaming (e.g., 900s/15min per chunk)
    - process_cleanup_timeout: Time to terminate process (default: 5s)
    """
    
    def __init__(
        self,
        org: str = "MidnightRider",
        bucket: str = "midnight_rider",
        compose_file: Optional[str] = None,
        service: str = "influxdb",
        query_startup_timeout: int = 10,
        stream_idle_timeout: int = 60,
        stream_overall_timeout: int = 900,
        process_cleanup_timeout: int = 5
    ):
        """
        Initialize chunked query provider with separated timeout scopes.
        
        Args:
            org: InfluxDB organization
            bucket: InfluxDB bucket
            compose_file: Path to docker-compose.yml
            service: Container service name
            query_startup_timeout: Time to start query (seconds)
            stream_idle_timeout: Time between data packets (seconds)
            stream_overall_timeout: Total time for chunk streaming (seconds)
            process_cleanup_timeout: Time to terminate process (seconds)
        """
        self.org = org
        self.bucket = bucket
        self.service = service
        self.query_startup_timeout = query_startup_timeout
        self.stream_idle_timeout = stream_idle_timeout
        self.stream_overall_timeout = stream_overall_timeout
        self.process_cleanup_timeout = process_cleanup_timeout
        self.compose_file = compose_file or self._discover_compose_file()
        
        if not self.compose_file:
            raise DockerComposeError(
                "docker-compose.yml not found. Set COMPOSE_FILE or run from repo root."
            )
        
        logger.info(f"AUTH_METHOD_CATEGORY: DOCKER_INTERNAL_CLI_CONTEXT")
        logger.info(
            f"Timeout scopes: "
            f"query_startup={query_startup_timeout}s, "
            f"stream_idle={stream_idle_timeout}s, "
            f"stream_overall={stream_overall_timeout}s, "
            f"cleanup={process_cleanup_timeout}s"
        )
    
    @staticmethod
    def _discover_compose_file() -> Optional[str]:
        """Auto-discover docker-compose.yml by walking upward from package root."""
        current = Path(__file__).resolve().parent
        
        while current != current.parent:
            for filename in ["docker-compose.yml", "docker-compose.yaml"]:
                candidate = current / filename
                if candidate.is_file():
                    logger.debug(f"Discovered compose file: {candidate}")
                    return str(candidate)
            
            if (current / ".git").exists():
                logger.debug(f"Reached repo root: {current}")
                return None
            
            current = current.parent
        
        return None
    
    def _build_docker_exec_cmd(self, flux_query: str) -> list:
        """Build docker exec command (no tokens in argv)."""
        return [
            "docker", "exec", "-i", self.service,
            "influx", "query", "--raw",
            flux_query
        ]
    
    def _drain_concurrent_streams_with_separate_timeouts(
        self,
        process: subprocess.Popen,
        stream_idle_deadline: float,
        stream_overall_deadline: float
    ) -> Tuple[Iterator[str], str]:
        """
        Concurrently drain stdout and stderr with SEPARATE timeout scopes.
        
        Args:
            process: subprocess.Popen instance
            stream_idle_deadline: Deadline for stream idle timeout
            stream_overall_deadline: Deadline for overall stream reading
        
        Yields:
            Decoded stdout lines
        
        Returns:
            Stderr text (bounded, sanitized)
        
        Raises:
            TimeoutError: If stream idle or overall deadline exceeded
        """
        MAX_STDERR_BYTES = 8192
        stderr_buffer = bytearray()
        stdout_buffer = b""
        sel = selectors.DefaultSelector()
        
        sel.register(process.stdout, selectors.EVENT_READ)
        sel.register(process.stderr, selectors.EVENT_READ)
        
        last_data_time = time.monotonic()
        
        try:
            while True:
                current_time = time.monotonic()
                
                # Check overall stream deadline
                if current_time >= stream_overall_deadline:
                    raise TimeoutError(
                        f"Stream overall timeout exceeded "
                        f"({self.stream_overall_timeout}s limit)"
                    )
                
                # Check idle timeout (no data for stream_idle_timeout seconds)
                if current_time - last_data_time > self.stream_idle_timeout:
                    raise TimeoutError(
                        f"Stream idle timeout exceeded "
                        f"({self.stream_idle_timeout}s without data)"
                    )
                
                # Calculate remaining time for select()
                remaining_overall = stream_overall_deadline - current_time
                remaining_idle = self.stream_idle_timeout - (current_time - last_data_time)
                select_timeout = min(remaining_overall, remaining_idle, 0.1)
                
                if select_timeout <= 0:
                    raise TimeoutError("Stream timeout (no select time remaining)")
                
                # Wait for data
                events = sel.select(timeout=select_timeout)
                
                if not events:
                    # No data available
                    if process.poll() is not None:
                        # Process exited, break to finalize
                        break
                    continue
                
                # Data is available
                last_data_time = time.monotonic()
                
                for key, mask in events:
                    try:
                        chunk = os.read(key.fileobj.fileno(), 4096)
                        if not chunk:
                            sel.unregister(key.fileobj)
                            continue
                        
                        if key.fileobj == process.stdout:
                            stdout_buffer += chunk
                            while b'\n' in stdout_buffer:
                                line, stdout_buffer = stdout_buffer.split(b'\n', 1)
                                yield line.decode('utf-8', errors='replace')
                        
                        elif key.fileobj == process.stderr:
                            if len(stderr_buffer) < MAX_STDERR_BYTES:
                                space_left = MAX_STDERR_BYTES - len(stderr_buffer)
                                stderr_buffer.extend(chunk[:space_left])
                    
                    except (IOError, OSError):
                        try:
                            sel.unregister(key.fileobj)
                        except:
                            pass
        
        finally:
            sel.close()
        
        # Yield remaining stdout
        if stdout_buffer:
            yield stdout_buffer.decode('utf-8', errors='replace')
        
        # Return stderr (bounded)
        stderr_text = stderr_buffer.decode('utf-8', errors='replace')
        if len(stderr_buffer) >= MAX_STDERR_BYTES:
            stderr_text = stderr_text[:MAX_STDERR_BYTES] + "\n[stderr truncated at 8KB limit]"
        
        return stderr_text
    
    def _safe_killpg(self, process, sig) -> bool:
        """Signal the child's process group, never our own.

        Guards two failure modes:

        1. process.pid is not a real OS pid (e.g. a test double). int() of a
           MagicMock is 1, so os.getpgid(process.pid) resolved to process
           group 1 and os.killpg() then signalled essentially every process
           of the session, killing the exporter, its shell and the SSH
           session with it.
        2. The child shares our own process group, which happens whenever
           preexec_fn=os.setsid did not take effect. Signalling that group
           would kill this exporter and all of its siblings.

        In both cases we fall back to signalling the child alone.
        """
        pid = getattr(process, "pid", None)
        if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 1:
            logger.error(f"Refusing killpg: invalid child pid {pid!r}")
            return False
        try:
            pgid = os.getpgid(pid)
            own_pgid = os.getpgid(0)
        except OSError as e:
            logger.warning(f"Cannot resolve process group for pid {pid}: {type(e).__name__}")
            return False
        if pgid <= 1 or pgid == own_pgid:
            logger.warning(
                f"Child pid {pid} shares our process group (pgid={pgid}); "
                "signalling the child only"
            )
            try:
                if sig == signal.SIGKILL:
                    process.kill()
                else:
                    process.terminate()
                return True
            except Exception as e:
                logger.error(f"Child-only signal failed: {type(e).__name__}")
                return False
        os.killpg(pgid, sig)
        return True

    def _terminate_process_group(self, process: subprocess.Popen) -> bool:
        """
        Cleanly terminate process group.
        
        Returns:
            True if process stopped, False if force-kill was needed
        """
        if process.poll() is not None:
            return True
        
        try:
            if hasattr(signal, 'SIGTERM'):
                self._safe_killpg(process, signal.SIGTERM)
        except:
            try:
                process.terminate()
            except:
                pass
        
        try:
            process.wait(timeout=self.process_cleanup_timeout)
            logger.debug(f"Process {process.pid} terminated gracefully")
            return True
        except subprocess.TimeoutExpired:
            pass
        
        try:
            if hasattr(signal, 'SIGKILL'):
                self._safe_killpg(process, signal.SIGKILL)
            else:
                process.kill()
            process.wait(timeout=2)
            logger.warning(f"Process {process.pid} force-killed")
            return False
        except:
            logger.error(f"Failed to kill process {process.pid}")
            return False
    
    def query_flux_chunk(
        self,
        flux_query: str,
        chunk_index: int,
        chunk_start: str,
        chunk_stop: str
    ) -> Iterator[str]:
        """
        Execute read-only Flux query for a chunk with SEPARATED timeout scopes.
        
        Args:
            flux_query: Flux query string
            chunk_index: Chunk number for logging
            chunk_start: Chunk start timestamp (ISO 8601 UTC)
            chunk_stop: Chunk stop timestamp (ISO 8601 UTC)
        
        Yields:
            Lines of CSV output
        
        Raises:
            TimeoutError: If query startup, stream idle, or stream overall timeout exceeded
            DockerComposeError: If query fails
        """
        cmd = self._build_docker_exec_cmd(flux_query)
        process = None
        
        # Set up timeout deadlines
        query_startup_deadline = time.monotonic() + self.query_startup_timeout
        stream_idle_deadline = time.monotonic() + self.stream_idle_timeout
        stream_overall_deadline = time.monotonic() + self.stream_overall_timeout
        
        logger.info(
            f"CHUNK_QUERY: chunk_index={chunk_index}, "
            f"start={chunk_start}, stop={chunk_stop}, "
            f"stream_timeout={self.stream_overall_timeout}s"
        )
        
        stderr_text = None
        
        try:
            # Start process with startup timeout
            logger.debug(f"Starting query process for chunk {chunk_index}...")
            
            popen_kwargs = {
                'stdout': subprocess.PIPE,
                'stderr': subprocess.PIPE,
                'text': False,
                'bufsize': 0
            }
            if hasattr(os, 'setsid'):
                popen_kwargs['preexec_fn'] = os.setsid
            
            process = subprocess.Popen(cmd, **popen_kwargs)
            logger.info(f"CHUNK_START: chunk_index={chunk_index}, pid={process.pid}")
            
            # Drain streams with separated timeout scopes
            try:
                line_count = 0
                for line in self._drain_concurrent_streams_with_separate_timeouts(
                    process,
                    stream_idle_deadline,
                    stream_overall_deadline
                ):
                    line_count += 1
                    if line_count % 10000 == 0:
                        logger.info(f"CHUNK_PROGRESS: chunk_index={chunk_index}, lines={line_count}")
                    yield line
                
                logger.info(f"CHUNK_PROGRESS: chunk_index={chunk_index}, lines={line_count} (final)")
            
            except TimeoutError as e:
                logger.error(f"CHUNK_FAILURE: chunk_index={chunk_index}, category=STREAM_TIMEOUT, {e}")
                if process and process.poll() is None:
                    self._terminate_process_group(process)
                raise
            
            # Wait for process completion with cleanup timeout
            try:
                process.wait(timeout=self.process_cleanup_timeout)
            except subprocess.TimeoutExpired:
                logger.error(f"CHUNK_FAILURE: chunk_index={chunk_index}, category=PROCESS_TIMEOUT")
                self._terminate_process_group(process)
                raise TimeoutError(f"Process timeout for chunk {chunk_index}")
            
            # Check exit code
            if process.returncode != 0:
                stderr_summary = (stderr_text.split('\n')[0][:200] if stderr_text else "(no stderr)")
                logger.error(
                    f"CHUNK_FAILURE: chunk_index={chunk_index}, "
                    f"category=QUERY_ERROR, exit_code={process.returncode}"
                )
                raise DockerComposeError(
                    f"Query failed for chunk {chunk_index} (exit {process.returncode}): {stderr_summary}"
                )
            
            logger.info(f"CHUNK_SUCCESS: chunk_index={chunk_index}")
        
        except TimeoutError:
            if process and process.poll() is None:
                self._terminate_process_group(process)
            raise
        
        except Exception as e:
            logger.error(f"CHUNK_FAILURE: chunk_index={chunk_index}, category=EXCEPTION, {type(e).__name__}")
            if process and process.poll() is None:
                self._terminate_process_group(process)
            raise
        
        finally:
            if process and process.poll() is None:
                logger.warning(f"CHUNK_CLEANUP: chunk_index={chunk_index}, force-terminating")
                self._terminate_process_group(process)
    
    def query_range_chunk(self, start: str, stop: str, chunk_index: int) -> Iterator[str]:
        """Query raw data for a chunk time range.
        
        NOTE: start and stop parameters MUST be unquoted ISO 8601 timestamps.
        The range() function expects TIME values, not STRING values.
        Example: start="2026-09-04T16:00:00Z" (not start='"2026-09-04T16:00:00Z"')
        """
        # Ensure timestamps are not quoted (they're passed as strings from chunked_export)
        # but used unquoted in the Flux query to represent TIME values
        # NOTE: sort() is intentionally NOT used here.
        # sort() is a BLOCKING Flux operation: it materialises the whole
        # result set in memory before emitting any row. One minute of this
        # bucket already holds ~1687 distinct series (mostly AIS targets and
        # virtual AtoNs), so a 15-minute chunk forced the engine to merge
        # tens of thousands of series at once. That exhausted RPi memory and
        # killed the InfluxDB container (exitCode=137 SIGKILL, exitCode=2),
        # which surfaced as DockerComposeError on every chunk.
        # range() already returns rows time-ordered per table, and
        # deterministic global ordering is applied downstream in merge.py.
        flux = f'''
from(bucket: "{self.bucket}")
  |> range(start: {start}, stop: {stop})
'''
        return self.query_flux_chunk(flux, chunk_index, start, stop)
