"""
Read-only InfluxDB Flux query client.
Uses environment variables: INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET.
"""
import os
import subprocess
from typing import Iterator, Optional

class InfluxClient:
    """Read-only InfluxDB client using influx CLI."""
    
    def __init__(self, url: Optional[str] = None, token: Optional[str] = None, 
                 org: Optional[str] = None, bucket: Optional[str] = None):
        self.url = url or os.environ.get("INFLUX_URL")
        self.token = token or os.environ.get("INFLUX_TOKEN")
        self.org = org or os.environ.get("INFLUX_ORG", "MidnightRider")
        self.bucket = bucket or os.environ.get("INFLUX_BUCKET", "midnight_rider")
        
        if not self.url or not self.token:
            raise ValueError("INFLUX_URL and INFLUX_TOKEN required")
    
    def query_flux(self, flux_query: str, timeout: int = 300) -> Iterator[str]:
        """
        Execute read-only Flux query, stream annotated CSV output.
        Yields lines of CSV as they arrive.
        """
        cmd = [
            "docker", "compose", "exec", "-T", "influxdb",
            "influx", "query", flux_query, "--raw"
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout
            )
            
            for line in iter(process.stdout.readline, ''):
                if line:
                    yield line.rstrip('\n')
            
            process.wait(timeout=timeout)
            
            if process.returncode != 0:
                stderr = process.stderr.read() if process.stderr else ""
                raise RuntimeError(f"Flux query failed: {stderr[:200]}")
        
        except subprocess.TimeoutExpired:
            process.kill()
            raise TimeoutError("Flux query timeout")
    
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
