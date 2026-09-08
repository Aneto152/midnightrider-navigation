"""
InfluxDB client with pluggable authentication and streaming support.

Features:
- Injectable authentication provider interface
- Streaming Flux query results to file/stdout
- Comprehensive error handling
- Support for multiple table formats (CSV, annotated CSV)
"""

import logging
import subprocess
from typing import Optional, Callable, TextIO
from abc import ABC, abstractmethod
from pathlib import Path

from auth_providers import AuthProvider, AuthProviderChain

logger = logging.getLogger(__name__)


class Transport(ABC):
    """Abstract transport interface for InfluxDB communication."""

    @abstractmethod
    def query(
        self,
        flux_query: str,
        org: str,
    ) -> str:
        """
        Execute Flux query and return results as string.
        
        Args:
            flux_query: Flux query string
            org: InfluxDB organization ID
            
        Returns:
            Query result string
            
        Raises:
            RuntimeError: On query failure
        """
        pass

    @abstractmethod
    def stream_query(
        self,
        flux_query: str,
        org: str,
        output_stream: TextIO,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> int:
        """
        Execute Flux query and stream results to output.
        
        Args:
            flux_query: Flux query string
            org: InfluxDB organization ID
            output_stream: File-like object to write results to
            progress_callback: Optional callback(bytes_written) for progress
            
        Returns:
            Total bytes written
            
        Raises:
            RuntimeError: On query failure
        """
        pass


class InfluxDBCLITransport(Transport):
    """Transport using InfluxDB CLI (influx command)."""

    def __init__(
        self,
        url: str,
        auth_provider: Optional[AuthProvider] = None,
    ):
        """
        Initialize InfluxDB CLI transport.
        
        Args:
            url: InfluxDB URL (http://localhost:8086)
            auth_provider: AuthProvider instance. If None, uses default chain.
        """
        self.url = url
        self.auth_provider = auth_provider or AuthProviderChain()

    def _get_base_cmd(self) -> list[str]:
        """Build base influx command with auth."""
        token = self.auth_provider.get_token() if hasattr(self.auth_provider, 'get_token') else None
        if isinstance(self.auth_provider, AuthProviderChain):
            token = self.auth_provider.get_token()
        else:
            token = self.auth_provider.get_token() if self.auth_provider else None

        if not token:
            raise RuntimeError("Failed to obtain authentication token")

        return [
            "influx",
            "--host", self.url,
            "--token", token,
        ]

    def query(
        self,
        flux_query: str,
        org: str,
    ) -> str:
        """Execute query and return string result."""
        try:
            cmd = self._get_base_cmd() + [
                "query",
                "--org", org,
                "--format", "csv",
            ]

            result = subprocess.run(
                cmd,
                input=flux_query,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"Query failed: {result.stderr}"
                )

            return result.stdout

        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"Query timeout: {e}")
        except Exception as e:
            raise RuntimeError(f"Query error: {e}")

    def stream_query(
        self,
        flux_query: str,
        org: str,
        output_stream: TextIO,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> int:
        """
        Execute query and stream results.
        
        Handles multiple Flux tables, annotated CSV, and progress tracking.
        """
        try:
            cmd = self._get_base_cmd() + [
                "query",
                "--org", org,
                "--format", "csv",
            ]

            # Use Popen for streaming
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=8192,
            )

            bytes_written = 0
            table_count = 0
            current_table_headers = []

            try:
                # Write query to stdin
                process.stdin.write(flux_query)
                process.stdin.close()

                # Read output line by line
                for line in process.stdout:
                    # Handle table separators (empty lines between Flux tables)
                    if line.strip() == "":
                        if bytes_written > 0:
                            output_stream.write("\n")
                            bytes_written += 1
                        table_count += 1
                        current_table_headers = []
                        continue

                    # Write line to output
                    output_stream.write(line)
                    line_bytes = len(line.encode('utf-8'))
                    bytes_written += line_bytes

                    # Progress callback
                    if progress_callback:
                        progress_callback(bytes_written)

                    # Track headers for debugging
                    if line.startswith("#group"):
                        current_table_headers.append(line)

                # Wait for process completion
                process.wait(timeout=30)

                if process.returncode != 0:
                    stderr = process.stderr.read() if process.stderr else ""
                    raise RuntimeError(
                        f"Stream query failed (code {process.returncode}): {stderr}"
                    )

                logger.info(
                    f"Query streaming complete: {bytes_written} bytes, "
                    f"{table_count} tables"
                )
                return bytes_written

            except subprocess.TimeoutExpired:
                process.kill()
                raise RuntimeError("Stream query timeout")

        except Exception as e:
            raise RuntimeError(f"Stream query error: {e}")


class InfluxDBClient:
    """High-level InfluxDB client."""

    def __init__(
        self,
        url: str = "http://localhost:8086",
        auth_provider: Optional[AuthProvider] = None,
        transport: Optional[Transport] = None,
    ):
        """
        Initialize InfluxDB client.
        
        Args:
            url: InfluxDB URL
            auth_provider: Custom authentication provider
            transport: Custom transport (uses InfluxDBCLITransport if None)
        """
        self.url = url
        self.auth_provider = auth_provider or AuthProviderChain()
        self.transport = transport or InfluxDBCLITransport(url, self.auth_provider)

    def query(
        self,
        flux_query: str,
        org: str,
    ) -> str:
        """Execute Flux query and return results."""
        return self.transport.query(flux_query, org)

    def stream_query(
        self,
        flux_query: str,
        org: str,
        output_file: Optional[str] = None,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> int:
        """
        Execute query and stream results.
        
        Args:
            flux_query: Flux query string
            org: InfluxDB organization
            output_file: File path to write results (stdout if None)
            progress_callback: Optional progress callback
            
        Returns:
            Bytes written
        """
        if output_file:
            with open(output_file, 'w') as f:
                return self.transport.stream_query(
                    flux_query,
                    org,
                    f,
                    progress_callback,
                )
        else:
            import sys
            return self.transport.stream_query(
                flux_query,
                org,
                sys.stdout,
                progress_callback,
            )

    def health_check(self) -> bool:
        """Verify InfluxDB connectivity."""
        try:
            result = subprocess.run(
                ["influx", "health", "--url", self.url],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
