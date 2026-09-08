"""
InfluxDB Power BI Exporter — USB-first professional package.

USB-first architecture:
- All runtime artifacts and logs → USB only
- Fail closed if USB unavailable
- No local disk fallback
- Read-only InfluxDB access
- HIPAA/security-compliant logging

Module structure:
- cli: Command-line interface
- main: Orchestration entry point
- influx_client: InfluxDB read-only query client
- annotated_csv: InfluxDB annotated CSV parser
- classifier: Midnight Rider & AIS event classification
- normalizer: Field aggregation and circular means
- writers: USB CSV output writers
- logging_utils: USB-safe logging
- schema: Output schema definitions
"""

__version__ = "1.0.0"
__author__ = "Midnight Rider Navigation"
