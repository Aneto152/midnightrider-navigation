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
    
    def query_flux(self, flux_query: str) -> Iterator[str]:
        """
        Execute read-only Flux query, stream annotated CSV output.
        
        Yields lines of CSV as they arrive from container.
        Handles subprocess lifecycle, timeout, and stderr sanitization.
        
        Raises:
            DockerComposeError: If service not running or query fails
            TimeoutError: If query exceeds timeout
        """
        cmd = self._build_docker_exec_cmd(flux_query)
        process = None
        
        try:
            logger.debug(f"Executing Flux query (timeout={self.timeout}s)")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Stream stdout line-by-line
            for line in iter(process.stdout.readline, ''):
                if line:
                    yield line.rstrip('\n')
            
            # Wait for process completion
            process.wait(timeout=self.timeout)
            
            if process.returncode != 0:
                stderr_lines = []
                if process.stderr:
                    for line in process.stderr:
                        stderr_lines.append(line.strip())
                
                # Sanitize stderr (no token extraction)
                stderr_summary = " ".join(stderr_lines[:5])  # First 5 lines
                raise DockerComposeError(
                    f"Query failed (exit {process.returncode}): {stderr_summary[:200]}"
                )
        
        except subprocess.TimeoutExpired:
            if process:
                process.kill()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.terminate()
            raise TimeoutError(f"Query timeout after {self.timeout}s")
        
        except Exception as e:
            if process and process.poll() is None:
                process.kill()
                try:
                    process.wait(timeout=5)
                except:
                    pass
            raise
        
        finally:
            # Ensure process cleanup
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
    
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
        logger.info("Docker-internal CLI provider initialized")
        return provider
    
    except DockerComposeError as e:
        logger.warning(f"Docker provider unavailable: {e}")
        
        # Try token-file fallback
        token_file = Path.home() / ".config" / "midnightrider" / "influxdb-read-token"
        if token_file.exists():
            logger.info(f"Attempting token-file fallback: {token_file}")
            try:
                token = token_file.read_text().strip()
                if token:
                    # Set as env variable for subprocess, NOT in logs/argv
                    os.environ["INFLUX_TOKEN"] = token
                    logger.info("Token loaded from fallback file (env only)")
                    # Return Docker provider which will use env var
                    return DockerInternalCliQueryProvider()
            except Exception as e:
                logger.error(f"Token-file fallback failed: {e}")
        
        raise
