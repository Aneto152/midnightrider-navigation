"""
CLI interface for InfluxDB queries with authentication provider selection.

Supports multiple authentication methods and streaming output.
"""

import argparse
import sys
import logging
from typing import Optional
from pathlib import Path

from influx_client import InfluxDBClient
from auth_providers import (
    AuthProvider,
    AuthProviderChain,
    DockerInternalCliAuthProvider,
    SecureTokenFileAuthProvider,
    EnvironmentTokenAuthProvider,
)

logger = logging.getLogger(__name__)


def setup_logging(debug: bool = False):
    """Configure logging."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )


def build_auth_provider(args) -> Optional[AuthProvider]:
    """
    Build auth provider based on CLI arguments.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        AuthProvider instance or None for default chain
    """
    if args.auth_method == "auto":
        # Use default chain
        return AuthProviderChain()

    elif args.auth_method == "docker-internal-cli":
        return DockerInternalCliAuthProvider(
            compose_file=args.compose_file,
            docker_service=args.docker_service,
        )

    elif args.auth_method == "token-file":
        return SecureTokenFileAuthProvider(
            token_file=args.token_file,
        )

    elif args.auth_method == "environment":
        return EnvironmentTokenAuthProvider(
            env_var=args.env_var,
        )

    else:
        raise ValueError(f"Unknown auth method: {args.auth_method}")


def load_query_file(path: str) -> str:
    """Load Flux query from file."""
    try:
        with open(path, 'r') as f:
            return f.read()
    except IOError as e:
        raise RuntimeError(f"Failed to read query file: {e}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Query InfluxDB with pluggable authentication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  # Query with automatic auth (Docker CLI → Token File → Environment)
  %(prog)s query 'from(bucket:"midnight_rider") |> range(start:-1h)'

  # Query using Docker-internal InfluxDB CLI
  %(prog)s --auth-method docker-internal-cli query 'from(bucket:"midnight_rider")'

  # Stream query results to file
  %(prog)s --output results.csv query 'from(bucket:"midnight_rider")'

  # Load query from file
  %(prog)s --query-file my_query.flux query

  # Dry-run (show command, don't execute)
  %(prog)s --dry-run query 'from(bucket:"midnight_rider")'

  # Schema report
  %(prog)s schema-report
        """,
    )

    # Global options
    parser.add_argument(
        "--url",
        default="http://localhost:8086",
        help="InfluxDB URL (default: http://localhost:8086)",
    )
    parser.add_argument(
        "--org",
        default="midnight-rider",
        help="InfluxDB organization (default: midnight-rider)",
    )
    parser.add_argument(
        "--auth-method",
        choices=["auto", "docker-internal-cli", "token-file", "environment"],
        default="auto",
        help="Authentication method (default: auto)",
    )
    parser.add_argument(
        "--compose-file",
        help="Path to docker-compose.yml for Docker method",
    )
    parser.add_argument(
        "--docker-service",
        default="influxdb",
        help="Docker service name (default: influxdb)",
    )
    parser.add_argument(
        "--token-file",
        help="Path to token file for token-file method",
    )
    parser.add_argument(
        "--env-var",
        default="INFLUXDB_TOKEN",
        help="Environment variable name for token (default: INFLUXDB_TOKEN)",
    )
    parser.add_argument(
        "--output",
        help="Output file for results (stdout if not specified)",
    )
    parser.add_argument(
        "--query-file",
        help="Load query from file instead of command-line argument",
    )
    parser.add_argument(
        "--schema-report",
        action="store_true",
        help="Generate schema report",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without running",
    )
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # query subcommand
    query_parser = subparsers.add_parser("query", help="Execute Flux query")
    query_parser.add_argument(
        "query",
        nargs="?",
        help="Flux query string (or use --query-file)",
    )

    # schema-report subcommand
    schema_parser = subparsers.add_parser(
        "schema-report",
        help="Generate InfluxDB schema report",
    )

    # health-check subcommand
    health_parser = subparsers.add_parser(
        "health",
        help="Check InfluxDB health",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.debug)

    try:
        # Build auth provider
        auth_provider = build_auth_provider(args)

        # Handle query command
        if args.command == "query":
            query = None

            if args.query_file:
                query = load_query_file(args.query_file)
            elif args.query:
                query = args.query
            else:
                parser.error("Query required (via argument or --query-file)")

            if args.dry_run:
                print(f"DRY RUN: Would execute query:")
                print(f"  URL: {args.url}")
                print(f"  Org: {args.org}")
                print(f"  Auth: {args.auth_method}")
                if args.output:
                    print(f"  Output: {args.output}")
                print(f"  Query: {query[:100]}...")
                return 0

            # Execute query
            client = InfluxDBClient(
                url=args.url,
                auth_provider=auth_provider,
            )

            logger.info("Executing query...")
            bytes_written = client.stream_query(
                query,
                args.org,
                output_file=args.output,
                progress_callback=lambda b: logger.debug(f"Progress: {b} bytes"),
            )

            if args.output:
                print(f"Results written to {args.output} ({bytes_written} bytes)")
            else:
                print(f"\n[{bytes_written} bytes written to stdout]")

        elif args.command == "schema-report":
            print("Schema Report: Not yet implemented")

        elif args.command == "health":
            client = InfluxDBClient(url=args.url)
            if client.health_check():
                print("✓ InfluxDB is healthy")
                return 0
            else:
                print("✗ InfluxDB is unhealthy")
                return 1

        else:
            parser.print_help()

        return 0

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=args.debug)
        return 1


if __name__ == "__main__":
    sys.exit(main())
