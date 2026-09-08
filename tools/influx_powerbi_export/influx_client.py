"""
Read-only InfluxDB Flux query client.
Uses Docker-internal CLI (no token extraction).
Fallback: Token file at ~/.config/midnightrider/influxdb-read-token
"""
import os
import logging
from typing import Iterator, Optional
from .docker_provider import (
    DockerInternalCliQueryProvider,
    get_or_fallback_provider,
    DockerComposeError
)

logger = logging.getLogger(__name__)

class InfluxClient:
    """
    Read-only InfluxDB client using Docker-internal CLI.
    Streams queries via container without token extraction.
    """
    
    def __init__(self, org: Optional[str] = None, bucket: Optional[str] = None,
                 compose_file: Optional[str] = None):
        """
        Initialize client with Docker-internal provider.
        
        Args:
            org: InfluxDB organization (default: MidnightRider)
            bucket: InfluxDB bucket (default: midnight_rider)
            compose_file: Path to docker-compose.yml (auto-discovered if None)
        
        Raises:
            DockerComposeError: If Docker provider cannot be initialized
        """
        self.org = org or os.environ.get("INFLUX_ORG", "MidnightRider")
        self.bucket = bucket or os.environ.get("INFLUX_BUCKET", "midnight_rider")
        
        # Initialize Docker-internal provider (with token-file fallback)
        try:
            self.provider = DockerInternalCliQueryProvider(
                org=self.org,
                bucket=self.bucket,
                compose_file=compose_file
            )
        except DockerComposeError:
            # Try fallback provider (may load token file)
            self.provider = get_or_fallback_provider()
    
    def query_flux(self, flux_query: str, timeout: int = 300) -> Iterator[str]:
        """
        Execute read-only Flux query, stream annotated CSV output.
        Yields lines of CSV as they arrive from Docker container.
        
        Note: Timeout is set on provider; this parameter is for compatibility.
        """
        return self.provider.query_flux(flux_query)
    
    def query_measurements_24h(self) -> Iterator[str]:
        """Query measurement counts for last 24 hours."""
        return self.provider.query_measurements_24h()
    
    def query_self_tag_24h(self) -> Iterator[str]:
        """Query self tag distribution for last 24 hours."""
        return self.provider.query_self_tag_24h()
    
    def query_range(self, start: str, stop: str) -> Iterator[str]:
        """Query raw data in time range."""
        return self.provider.query_range(start, stop)
