"""
Authentication providers for InfluxDB integration.

Supports multiple authentication strategies:
1. Docker-internal CLI (primary)
2. Secure token file (fallback)
3. Environment variables (fallback)
"""

import os
import subprocess
import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class AuthProvider(ABC):
    """Abstract base for authentication providers."""

    @abstractmethod
    def get_token(self) -> Optional[str]:
        """
        Retrieve authentication token.
        
        Returns:
            Token string, or None if unable to authenticate.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if this auth provider can be used in current environment.
        
        Returns:
            True if provider prerequisites are met.
        """
        pass

    @abstractmethod
    def method_name(self) -> str:
        """Return human-readable method name."""
        pass


class DockerInternalCliAuthProvider(AuthProvider):
    """
    Primary provider: retrieve token via Docker container's InfluxDB CLI.
    
    Executes `influx auth list` command inside running InfluxDB container
    to extract the default token without exposing it on command line.
    
    Prerequisites:
    - Docker running with InfluxDB container
    - Container accessible via docker exec
    - InfluxDB CLI available inside container
    """

    def __init__(
        self,
        compose_file: Optional[str] = None,
        docker_service: str = "influxdb",
    ):
        """
        Initialize Docker-internal CLI provider.
        
        Args:
            compose_file: Path to docker-compose.yml (auto-detected if None)
            docker_service: Service name in compose file (default: "influxdb")
        """
        self.compose_file = compose_file or self._find_compose_file()
        self.docker_service = docker_service
        self._token_cache: Optional[str] = None

    @staticmethod
    def _find_compose_file() -> Optional[str]:
        """Search for docker-compose.yml in common locations."""
        candidates = [
            "docker-compose.yml",
            "docker-compose.yaml",
            "../docker-compose.yml",
            "/home/pi/midnightrider-navigation/docker-compose.yml",
        ]
        for path in candidates:
            if os.path.exists(path):
                return os.path.abspath(path)
        return None

    def is_available(self) -> bool:
        """Check if Docker and InfluxDB container are accessible."""
        if not self.compose_file or not os.path.exists(self.compose_file):
            logger.debug(
                f"DockerInternalCliAuthProvider not available: "
                f"compose file not found ({self.compose_file})"
            )
            return False

        try:
            # Test docker compose ps
            result = subprocess.run(
                ["docker", "compose", "-f", self.compose_file, "ps", "-q", self.docker_service],
                capture_output=True,
                text=True,
                timeout=5,
            )
            available = result.returncode == 0 and bool(result.stdout.strip())
            if not available:
                logger.debug(
                    f"DockerInternalCliAuthProvider not available: "
                    f"service '{self.docker_service}' not running"
                )
            return available
        except Exception as e:
            logger.debug(f"DockerInternalCliAuthProvider not available: {e}")
            return False

    def get_token(self) -> Optional[str]:
        """
        Retrieve token via docker exec influx auth list.
        
        Executes command inside InfluxDB container to avoid exposing
        token on host command line (ps, bash history, etc.).
        
        Returns:
            Token string, or None on failure.
        """
        if self._token_cache:
            return self._token_cache

        if not self.compose_file:
            logger.error("Docker compose file not found")
            return None

        try:
            # Get container ID
            result = subprocess.run(
                ["docker", "compose", "-f", self.compose_file, "ps", "-q", self.docker_service],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0 or not result.stdout.strip():
                logger.error(f"Failed to get container ID for {self.docker_service}")
                return None

            container_id = result.stdout.strip()

            # Execute influx auth list inside container
            # This command outputs JSON with token field
            exec_result = subprocess.run(
                [
                    "docker",
                    "exec",
                    container_id,
                    "influx",
                    "auth",
                    "list",
                    "--format",
                    "json",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if exec_result.returncode != 0:
                logger.error(
                    f"Failed to list auth tokens: {exec_result.stderr}"
                )
                return None

            # Parse JSON output
            try:
                auths = json.loads(exec_result.stdout)
                # Find first token (typically the default/admin token)
                if isinstance(auths, list) and len(auths) > 0:
                    token = auths[0].get("token")
                    if token:
                        self._token_cache = token
                        logger.debug("Successfully retrieved token via Docker CLI")
                        return token
                elif isinstance(auths, dict) and "authorizations" in auths:
                    for auth in auths.get("authorizations", []):
                        token = auth.get("token")
                        if token:
                            self._token_cache = token
                            logger.debug("Successfully retrieved token via Docker CLI")
                            return token
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse auth list JSON: {e}")
                return None

            logger.error("No tokens found in auth list response")
            return None

        except subprocess.TimeoutExpired:
            logger.error("Docker exec command timed out")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting token via Docker CLI: {e}")
            return None

    def method_name(self) -> str:
        return "docker-internal-cli"

    def __del__(self):
        """Cleanup: ensure subprocess resources are released."""
        # Token cache will be garbage collected
        pass


class SecureTokenFileAuthProvider(AuthProvider):
    """
    Fallback provider: read token from secure file.
    
    Reads InfluxDB token from a file with restricted permissions.
    
    Prerequisites:
    - Token file at specified path
    - File readable by current user
    """

    def __init__(self, token_file: Optional[str] = None):
        """
        Initialize token file provider.
        
        Args:
            token_file: Path to file containing token (auto-detect if None)
        """
        self.token_file = token_file or self._find_token_file()

    @staticmethod
    def _find_token_file() -> Optional[str]:
        """Search for token file in common locations."""
        candidates = [
            ".influxdb-token",
            "~/.influxdb-token",
            "/home/pi/.influxdb-token",
            "/etc/influxdb/.influxdb-token",
        ]
        for path in candidates:
            expanded = os.path.expanduser(path)
            if os.path.exists(expanded):
                return expanded
        return None

    def is_available(self) -> bool:
        """Check if token file exists and is readable."""
        if not self.token_file:
            logger.debug("SecureTokenFileAuthProvider not available: no token file found")
            return False

        if not os.path.isfile(self.token_file):
            logger.debug(
                f"SecureTokenFileAuthProvider not available: "
                f"file not found ({self.token_file})"
            )
            return False

        if not os.access(self.token_file, os.R_OK):
            logger.debug(
                f"SecureTokenFileAuthProvider not available: "
                f"file not readable ({self.token_file})"
            )
            return False

        return True

    def get_token(self) -> Optional[str]:
        """
        Read token from file.
        
        Returns:
            Token string (whitespace trimmed), or None on failure.
        """
        if not self.token_file or not os.path.exists(self.token_file):
            logger.error(f"Token file not found: {self.token_file}")
            return None

        try:
            with open(self.token_file, "r") as f:
                token = f.read().strip()
                if token:
                    logger.debug(f"Successfully retrieved token from file: {self.token_file}")
                    return token
                else:
                    logger.error(f"Token file is empty: {self.token_file}")
                    return None
        except IOError as e:
            logger.error(f"Failed to read token file: {e}")
            return None

    def method_name(self) -> str:
        return "token-file"


class EnvironmentTokenAuthProvider(AuthProvider):
    """
    Fallback provider: retrieve token from environment variable.
    
    Reads token from INFLUXDB_TOKEN or similar environment variable.
    
    Prerequisites:
    - Environment variable set
    """

    def __init__(self, env_var: str = "INFLUXDB_TOKEN"):
        """
        Initialize environment variable provider.
        
        Args:
            env_var: Environment variable name (default: INFLUXDB_TOKEN)
        """
        self.env_var = env_var

    def is_available(self) -> bool:
        """Check if environment variable is set."""
        available = self.env_var in os.environ and bool(os.environ[self.env_var].strip())
        if not available:
            logger.debug(
                f"EnvironmentTokenAuthProvider not available: "
                f"${self.env_var} not set or empty"
            )
        return available

    def get_token(self) -> Optional[str]:
        """
        Retrieve token from environment variable.
        
        Returns:
            Token string, or None if not set.
        """
        token = os.environ.get(self.env_var, "").strip()
        if token:
            logger.debug(f"Successfully retrieved token from ${self.env_var}")
            return token
        else:
            logger.error(f"Environment variable ${self.env_var} not set or empty")
            return None

    def method_name(self) -> str:
        return "environment"


class AuthProviderChain:
    """
    Attempt multiple authentication providers in order (fallback chain).
    
    Tries each provider until one succeeds. Logs which provider was used.
    """

    def __init__(self, providers: Optional[list[AuthProvider]] = None):
        """
        Initialize auth chain.
        
        Args:
            providers: List of providers to try in order.
                      If None, uses default chain: Docker CLI → Token File → Environment
        """
        if providers is None:
            providers = [
                DockerInternalCliAuthProvider(),
                SecureTokenFileAuthProvider(),
                EnvironmentTokenAuthProvider(),
            ]
        self.providers = providers
        self._used_method: Optional[str] = None

    def get_token(self) -> Optional[str]:
        """
        Try each provider until one succeeds.
        
        Returns:
            Token string, or None if all providers fail.
        """
        for provider in self.providers:
            if provider.is_available():
                token = provider.get_token()
                if token:
                    self._used_method = provider.method_name()
                    logger.info(f"Authentication successful via: {self._used_method}")
                    return token
                else:
                    logger.debug(
                        f"Provider {provider.method_name()} available but token retrieval failed"
                    )

        logger.error("All authentication providers exhausted")
        return None

    def used_method(self) -> Optional[str]:
        """Return the authentication method used (after get_token)."""
        return self._used_method
