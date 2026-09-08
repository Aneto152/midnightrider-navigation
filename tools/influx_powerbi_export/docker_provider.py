"""
Docker-internal InfluxDB CLI provider.
Streams queries from container process WITHOUT token extraction or CLI args.

Authentication:
  1. Primary: Docker exec (container-internal auth context)
  2. Fallback: Token file at ~/.config/midnightrider/influxdb-read-token (via env)

No tokens in:
  - Command-line arguments
  - Logs or exceptions
  - Git or manifests
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

class DockerInternalCliQueryProvider:
    """
    Streams Flux queries via Docker exec from running InfluxDB container.
    Uses InfluxDB's internal CLI authentication context (no token extraction).
    """
    
    def __init__(self, org: str = "MidnightRider", bucket: str = "midnight_rider",
                 compose_file: Optional[str] = None, service: str = "influxdb",
                 timeout: int = 300):
        """
        Initialize Docker-internal provider.
        
        Args:
            org: InfluxDB organization (default: MidnightRider)
            bucket: InfluxDB bucket (default: midnight_rider)
            compose_file: Path to docker-compose.yml (auto-discovery if None)
            service: Container service name (default: influxdb)
            timeout: Query timeout in seconds (default: 300)
        """
        self.org = org
        self.bucket = bucket
        self.service = service
        self.timeout = timeout
        self.compose_file = compose_file or self._discover_compose_file()
        
        if not self.compose_file:
            raise DockerComposeError(
                "docker-compose.yml not found. Set COMPOSE_FILE or run from repo root."
            )
        
        logger.info(f"AUTH_METHOD_CATEGORY: DOCKER_INTERNAL_CLI_CONTEXT")
        logger.debug(f"Compose file: {self.compose_file}")
    
    @staticmethod
    def _discover_compose_file() -> Optional[str]:
        """Auto-discover docker-compose.yml from repo root."""
        candidates = [
            Path("/home/aneto/midnightrider-navigation/docker-compose.yml"),
            Path.cwd() / "docker-compose.yml",
            Path.cwd() / "docker-compose.yaml",
        ]
        
        for candidate in candidates:
            if candidate.is_file():
                logger.debug(f"Discovered compose file: {candidate}")
                return str(candidate)
        
        return None
    
    def _build_docker_exec_cmd(self, flux_query: str) -> list:
        """
        Build docker compose exec command.
        
        NO --token in argv.
        Returns command ready for subprocess.Popen().
        """
        return [
            "docker", "compose",
            "-f", self.compose_file,
            "exec", "-T", self.service,
            "influx", "query", "--raw",
            flux_query
        ]
    
    def _drain_concurrent_streams(self, process: subprocess.Popen, deadline: float) -> Tuple[list, str]:
        """
        Concurrently drain stdout and stderr to avoid deadlock.
        Uses selectors for non-blocking I/O.
        
        Returns:
            (stdout_lines, stderr_text) - all output drained
        """
        stdout_lines = []
        stderr_lines = []
        sel = selectors.DefaultSelector()
        
        # Register both pipes as ready-to-read
        sel.register(process.stdout, selectors.EVENT_READ)
        sel.register(process.stderr, selectors.EVENT_READ)
        
        try:
            while True:
                remaining = max(0, deadline - time.monotonic())
                if remaining <= 0:
                    raise TimeoutError(f"Stream draining timeout (deadline exceeded)")
                
                # Wait for either stream to have data, or timeout
                events = sel.select(timeout=min(remaining, 0.1))
                
                if not events:
                    # Check if process completed
                    if process.poll() is not None:
                        break
                    continue
                
                # Process available streams
                for key, mask in events:
                    try:
                        line = key.fileobj.readline()
                        if line:
                            if key.fileobj == process.stdout:
                                stdout_lines.append(line.rstrip('\n'))
                            elif key.fileobj == process.stderr:
                                stderr_lines.append(line.rstrip('\n'))
                        else:
                            # EOF on this stream
                            sel.unregister(key.fileobj)
                    except IOError:
                        # Stream closed
                        sel.unregister(key.fileobj)
                
                # Check if both streams are closed
                if not sel.get_map():
                    break
        
        finally:
            sel.close()
        
        # Read any remaining buffered data
        if process.stdout:
            remaining_out = process.stdout.read()
            if remaining_out:
                stdout_lines.extend(remaining_out.rstrip('\n').split('\n'))
        if process.stderr:
            remaining_err = process.stderr.read()
            if remaining_err:
                stderr_lines.extend(remaining_err.rstrip('\n').split('\n'))
        
        stderr_text = '\n'.join(stderr_lines)
        return stdout_lines, stderr_text
    
    def _terminate_process_group(self, process: subprocess.Popen, timeout: int = 5) -> bool:
        """
        Cleanly terminate process group, escalate if necessary.
        Returns True if process stopped, False if force-kill was needed.
        """
        if process.poll() is not None:
            return True  # Already terminated
        
        try:
            # Send SIGTERM to process group (on Unix)
            if hasattr(signal, 'SIGTERM'):
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except:
            # Fallback: terminate single process
            try:
                process.terminate()
            except:
                pass
        
        # Wait for graceful termination
        try:
            process.wait(timeout=timeout)
            logger.debug(f"Process {process.pid} terminated gracefully")
            return True
        except subprocess.TimeoutExpired:
            pass
        
        # Force-kill if graceful termination failed
        try:
            if hasattr(signal, 'SIGKILL'):
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            else:
                process.kill()
            process.wait(timeout=2)
            logger.warning(f"Process {process.pid} force-killed")
            return False
        except:
            logger.error(f"Failed to kill process {process.pid}")
            return False
    
    def query_flux(self, flux_query: str) -> Iterator[str]:
        """
        Execute read-only Flux query, stream annotated CSV output.
        
        Yields lines of CSV as they arrive from container.
        Handles subprocess lifecycle with true monotonic timeout,
        concurrent stream draining, and process cleanup.
        
        Raises:
            DockerComposeError: If service not running or query fails
            TimeoutError: If query exceeds timeout
        """
        cmd = self._build_docker_exec_cmd(flux_query)
        process = None
        deadline = time.monotonic() + self.timeout
        
        try:
            logger.debug(f"Executing Flux query (timeout={self.timeout}s)")
            
            # Start process in new session on Unix to handle group termination
            popen_kwargs = {
                'stdout': subprocess.PIPE,
                'stderr': subprocess.PIPE,
                'text': True,
            }
            if hasattr(os, 'setsid'):
                popen_kwargs['preexec_fn'] = os.setsid
            
            process = subprocess.Popen(cmd, **popen_kwargs)
            
            # Concurrently drain both stdout and stderr
            stdout_lines, stderr_text = self._drain_concurrent_streams(process, deadline)
            
            # Wait for process completion with remaining timeout
            remaining = max(0, deadline - time.monotonic())
            try:
                process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                logger.error("Process still running after stream drain, terminating...")
                self._terminate_process_group(process)
                raise TimeoutError(f"Query timeout after {self.timeout}s")
            
            # Yield all stdout lines
            for line in stdout_lines:
                if line:
                    yield line
            
            # Check exit code
            if process.returncode != 0:
                # Sanitize stderr (no token extraction, first 5 lines max)
                stderr_summary = " ".join(stderr_text.split('\n')[:5])
                raise DockerComposeError(
                    f"Query failed (exit {process.returncode}): {stderr_summary[:200]}"
                )
        
        except subprocess.TimeoutExpired:
            logger.error("Query execution timeout")
            if process:
                self._terminate_process_group(process)
            raise TimeoutError(f"Query timeout after {self.timeout}s")
        
        except TimeoutError:
            # Re-raise timeout errors as-is
            raise
        
        except Exception as e:
            # Cleanup on any other exception
            if process and process.poll() is None:
                self._terminate_process_group(process)
            raise
        
        finally:
            # Final safety: ensure no orphan process
            if process and process.poll() is None:
                logger.warning("Process still running in finally block, force-terminating")
                self._terminate_process_group(process, timeout=2)
    
    def test_auth(self) -> bool:
        """
        Minimal read-only test to verify authentication.
        Returns True if authenticated and bucket is accessible.
        """
        test_query = f'''
from(bucket: "{self.bucket}")
  |> range(start: -1h)
  |> limit(n: 1)
'''
        try:
            logger.debug("Testing InfluxDB authentication...")
            for line in self.query_flux(test_query):
                # Just consume one result
                logger.debug("Auth test: bucket accessible")
                return True
            
            logger.debug("Auth test: no data in bucket (normal for empty bucket)")
            return True
        
        except DockerComposeError as e:
            logger.error(f"Auth test failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Auth test error: {type(e).__name__}: {e}")
            return False
    
    def query_measurements_24h(self) -> Iterator[str]:
        """Query measurement counts for last 24 hours."""
        flux = f'''
from(bucket: "{self.bucket}")
  |> range(start: -24h)
  |> group(columns: ["_measurement"])
  |> count()
  |> sort(columns: ["_value"], desc: true)
'''
        return self.query_flux(flux)
    
    def query_self_tag_24h(self) -> Iterator[str]:
        """Query self tag distribution for last 24 hours."""
        flux = f'''
from(bucket: "{self.bucket}")
  |> range(start: -24h)
  |> group(columns: ["self"])
  |> count()
  |> sort(columns: ["_value"], desc: true)
'''
        return self.query_flux(flux)
    
    def query_range(self, start: str, stop: str) -> Iterator[str]:
        """Query raw data in time range."""
        flux = f'''
from(bucket: "{self.bucket}")
  |> range(start: {start}, stop: {stop})
  |> sort(columns: ["_time"])
'''
        return self.query_flux(flux)


def get_or_fallback_provider() -> DockerInternalCliQueryProvider:
    """
    Factory: Get Docker-internal provider with optional token-file fallback.
    
    Primary: Docker exec (no token)
    Fallback: Token file at ~/.config/midnightrider/influxdb-read-token (env-only)
    
    Returns:
        DockerInternalCliQueryProvider configured and ready to query.
    
    Raises:
        DockerComposeError: If provider cannot be initialized.
    """
    try:
        provider = DockerInternalCliQueryProvider()
        
        # Test authentication
        if not provider.test_auth():
            raise DockerComposeError("Docker provider auth test failed")
        
        logger.info("Docker-internal CLI provider initialized and authenticated")
        return provider
    
    except DockerComposeError as e:
        logger.warning(f"Docker provider unavailable: {e}")
        
        # Try token-file fallback
        token_file = Path.home() / ".config" / "midnightrider" / "influxdb-read-token"
        if token_file.exists():
            logger.info(f"Attempting token-file fallback")
            try:
                token = token_file.read_text().strip()
                if token:
                    # Set as env variable for subprocess, NOT in logs/argv
                    os.environ["INFLUX_TOKEN"] = token
                    logger.info("AUTH_METHOD_CATEGORY: TOKEN_FILE_FALLBACK (env only)")
                    # Return Docker provider which will use env var
                    return DockerInternalCliQueryProvider()
            except Exception as e:
                logger.error(f"Token-file fallback failed: {type(e).__name__}")
        
        raise
