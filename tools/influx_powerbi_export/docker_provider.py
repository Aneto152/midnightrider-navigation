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
                 timeout: int = 1200):
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
        """Auto-discover docker-compose.yml by walking upward from package root."""
        # Start from package directory
        current = Path(__file__).resolve().parent
        
        # Walk upward to find repo root (indicated by presence of .git or docker-compose.yml)
        while current != current.parent:
            for filename in ["docker-compose.yml", "docker-compose.yaml"]:
                candidate = current / filename
                if candidate.is_file():
                    logger.debug(f"Discovered compose file: {candidate}")
                    return str(candidate)
            
            # Check for .git directory to confirm repo root
            if (current / ".git").exists():
                logger.debug(f"Reached repo root: {current}")
                return None  # No compose file found
            
            current = current.parent
        
        return None
    
    def _build_docker_exec_cmd(self, flux_query: str) -> list:
        """
        Build docker exec command for running container.
        
        Uses direct docker exec (not compose) to avoid requiring .env.
        Container-internal auth is preserved via established CLI context.
        NO --token in argv.
        Returns command ready for subprocess.Popen().
        """
        # Use the running container directly via docker exec
        # This avoids needing .env or docker-compose.yml
        return [
            "docker", "exec", "-i", self.service,
            "influx", "query", "--raw",
            flux_query
        ]
    
    def _drain_concurrent_streams(self, process: subprocess.Popen, deadline: float):
        """
        Concurrently drain stdout and stderr, yielding stdout lines incrementally.
        Bounded stderr (max 8KB), true streaming (NO accumulation).
        Uses non-blocking I/O with selectors.
        
        Yields:
            Decoded stdout lines as they arrive (BEFORE process completion)
        
        Returns stderr text (sanitized, bounded):
            Raises TimeoutError if deadline exceeded
        """
        MAX_STDERR_BYTES = 8192
        stderr_buffer = bytearray()
        stdout_buffer = b""
        sel = selectors.DefaultSelector()
        
        # Register both pipes as binary non-blocking
        sel.register(process.stdout, selectors.EVENT_READ)
        sel.register(process.stderr, selectors.EVENT_READ)
        
        try:
            while True:
                remaining = max(0, deadline - time.monotonic())
                if remaining <= 0:
                    raise TimeoutError("Stream draining timeout (deadline exceeded)")
                
                # Wait for either stream with timeout
                events = sel.select(timeout=min(remaining, 0.1))
                
                if not events:
                    if process.poll() is not None:
                        break
                    continue
                
                # Process ready streams
                for key, mask in events:
                    try:
                        # Non-blocking binary read
                        chunk = os.read(key.fileobj.fileno(), 4096)
                        if not chunk:
                            sel.unregister(key.fileobj)
                            continue
                        
                        if key.fileobj == process.stdout:
                            # Decode and YIELD complete lines immediately
                            stdout_buffer += chunk
                            while b'\n' in stdout_buffer:
                                line, stdout_buffer = stdout_buffer.split(b'\n', 1)
                                yield line.decode('utf-8', errors='replace')
                        
                        elif key.fileobj == process.stderr:
                            # Bound stderr (max 8KB)
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
        
        # Yield any remaining complete lines from stdout_buffer (BEFORE returning stderr)
        if stdout_buffer:
            yield stdout_buffer.decode('utf-8', errors='replace')
        
        # Return stderr (bounded, sanitized) after all stdout yielded
        stderr_text = stderr_buffer.decode('utf-8', errors='replace')
        if len(stderr_buffer) >= MAX_STDERR_BYTES:
            stderr_text = stderr_text[:MAX_STDERR_BYTES] + "\n[stderr truncated at 8KB limit]"
        
        return stderr_text
    
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
        
        Yields lines of CSV as they arrive from container (TRUE STREAMING).
        Lines are yielded BEFORE process completion (no accumulation).
        Handles subprocess lifecycle with monotonic timeout covering:
        - process startup
        - stdout reading
        - stderr reading  
        - process completion
        - process cleanup
        
        Raises:
            DockerComposeError: If service not running or query fails
            TimeoutError: If query exceeds timeout
        """
        cmd = self._build_docker_exec_cmd(flux_query)
        process = None
        deadline = time.monotonic() + self.timeout
        stderr_text = None
        
        try:
            logger.debug(f"Executing Flux query (timeout={self.timeout}s)")
            
            # Start process in new session on Unix for group termination
            popen_kwargs = {
                'stdout': subprocess.PIPE,
                'stderr': subprocess.PIPE,
                'text': False,  # Binary mode for true non-blocking streaming
                'bufsize': 0,   # Unbuffered
            }
            if hasattr(os, 'setsid'):
                popen_kwargs['preexec_fn'] = os.setsid
            
            process = subprocess.Popen(cmd, **popen_kwargs)
            
            # Concurrently drain both stdout and stderr
            # _drain_concurrent_streams() is a generator that YIELDS stdout lines
            # and RETURNS stderr text
            stream_gen = self._drain_concurrent_streams(process, deadline)
            
            # Yield stdout lines as they arrive (BEFORE process completion)
            # This is TRUE STREAMING - no accumulation
            try:
                while True:
                    try:
                        line = next(stream_gen)
                        yield line  # Yield immediately, don't accumulate
                    except StopIteration as e:
                        # Generator exhausted, stderr is in e.value
                        stderr_text = e.value
                        break
            except TimeoutError:
                # Re-raise timeout during streaming
                if process and process.poll() is None:
                    self._terminate_process_group(process)
                raise
            
            # Wait for process completion with remaining timeout
            remaining = max(0, deadline - time.monotonic())
            if remaining <= 0:
                raise TimeoutError("Deadline exceeded during stream drain")
            
            try:
                process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                logger.error("Process timeout during wait")
                self._terminate_process_group(process)
                raise TimeoutError(f"Query timeout after {self.timeout}s")
            
            # Check exit code
            if process.returncode != 0:
                # Sanitize stderr (bounded, no token extraction)
                if stderr_text:
                    stderr_summary = stderr_text.split('\n')[0][:200]
                else:
                    stderr_summary = "(stderr unavailable)"
                raise DockerComposeError(
                    f"Query failed (exit {process.returncode}): {stderr_summary}"
                )
        
        except TimeoutError:
            if process and process.poll() is None:
                self._terminate_process_group(process)
            raise
        
        except Exception as e:
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


class TokenFileHttpProvider:
    """
    Token-file HTTP provider: fallback when Docker-internal CLI is unavailable.
    Reads token from secure file, sends only via HTTP Authorization header.
    Never places token in argv or env.
    """
    
    def __init__(self, org: str = "MidnightRider", bucket: str = "midnight_rider",
                 host: str = "http://localhost:8086", timeout: int = 1200):
        self.org = org
        self.bucket = bucket
        self.host = host
        self.timeout = timeout
        self.token = None
        
        # Load token from secure file (into memory only)
        token_file = Path.home() / ".config" / "midnightrider" / "influxdb-read-token"
        if token_file.exists():
            try:
                self.token = token_file.read_text().strip()
                if self.token:
                    logger.info("AUTH_METHOD_CATEGORY: TOKEN_FILE_FALLBACK")
                else:
                    raise ValueError("Token file is empty")
            except Exception as e:
                logger.error(f"Failed to read token file: {type(e).__name__}")
                raise
        else:
            raise DockerComposeError(
                f"Token file not found: {token_file}"
            )
    
    def query_flux(self, flux_query: str) -> Iterator[str]:
        """
        Execute Flux query via HTTP with Authorization header.
        Token is NEVER in argv or logged.
        """
        import http.client
        import json
        
        try:
            # Create HTTPS request with Authorization header
            conn = http.client.HTTPConnection(
                self.host.replace("http://", "").replace("https://", ""),
                timeout=self.timeout
            )
            
            # Prepare query (read-only)
            payload = json.dumps({
                "query": flux_query,
                "type": "flux",
                "org": self.org
            })
            
            headers = {
                "Authorization": f"Token {self.token}",
                "Content-Type": "application/json"
            }
            
            # Send request
            conn.request("POST", "/api/v2/query?org=" + self.org, payload, headers)
            response = conn.getresponse()
            
            if response.status != 200:
                raise DockerComposeError(
                    f"Query failed (HTTP {response.status})"
                )
            
            # Stream response lines
            for line in response:
                decoded = line.decode('utf-8').rstrip('\n')
                if decoded:
                    yield decoded
            
            conn.close()
        
        except Exception as e:
            logger.error(f"Token-file HTTP query failed: {type(e).__name__}")
            raise
    
    def test_auth(self) -> bool:
        """Test authentication via HTTP."""
        try:
            for line in self.query_flux(
                f'from(bucket: "{self.bucket}") |> range(start: -1h) |> limit(n: 1)'
            ):
                return True
            return True
        except Exception:
            return False


def get_or_fallback_provider():
    """
    Factory: Get Docker-internal provider, or fallback to token-file HTTP.
    
    Primary: Docker exec (no token extraction)
    Fallback: Token file HTTP (token in Authorization header only, never in argv/env)
    
    Returns:
        DockerInternalCliQueryProvider or TokenFileHttpProvider
    
    Raises:
        DockerComposeError: If both providers fail.
    """
    try:
        # Try Docker-internal CLI first
        provider = DockerInternalCliQueryProvider()
        
        if provider.test_auth():
            logger.info("Docker-internal CLI provider initialized and authenticated")
            return provider
        else:
            logger.warning("Docker provider auth test failed")
    
    except DockerComposeError as e:
        logger.warning(f"Docker provider unavailable: {e}")
    
    # Try token-file HTTP fallback
    try:
        logger.info("Attempting token-file HTTP fallback")
        provider = TokenFileHttpProvider()
        
        if provider.test_auth():
            logger.info("Token-file HTTP provider initialized and authenticated")
            return provider
        else:
            logger.warning("Token-file HTTP provider auth test failed")
    
    except Exception as e:
        logger.warning(f"Token-file fallback failed: {type(e).__name__}")
    
    # Both failed
    raise DockerComposeError(
        "Neither Docker-internal CLI nor token-file HTTP provider available"
    )
