"""
OpenClaw Agent CLI adapter for LLM-based content generation.

Provides a safe, testable interface to the local OpenClaw agent command.
Fails closed if the CLI is unavailable or returns invalid output.

Initialization contract:
- Determines CLI availability at adapter creation time
- Validates configuration (timeout, agent_id) without exposing secrets
- Provides deterministic availability status
- Logs safe initialization metadata only (no credentials, no payloads)
- All subprocess calls are mockable for testing
"""

import subprocess
import os
import tempfile
import json
import logging
from typing import Optional, Tuple, Callable
from dataclasses import dataclass
from .logging_utils import SanitizedMessage


@dataclass
class OpenClawResult:
    """Result from OpenClaw agent call."""
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    provider_status: str = "unavailable"  # or "timeout", "error", "success"
    execution_id: Optional[str] = None


class OpenClawAdapter:
    """
    Adapter for local OpenClaw agent CLI.

    Contract:
    - openclaw agent --message <string> --timeout <seconds>
    - --message-file <path> for multiline prompts
    - --json for JSON output
    - --agent main (the main agent)
    - --thinking low (disable verbose thinking)

    Initialization:
    - Determines CLI availability at creation time
    - Uses default timeout (30s) or override
    - Logs safe initialization metadata only
    - Fails closed if CLI unavailable

    Notes:
    - No --deliver (output only, no Telegram here)
    - No credentials in environment
    - Fails closed if CLI unavailable
    - All subprocess calls must be mockable in tests
    - No production runtime loop (library component only)
    """

    CLI_PATH = "openclaw"  # Assumes openclaw is in PATH
    DEFAULT_TIMEOUT = 30  # seconds

    def __init__(self, timeout_seconds: Optional[int] = None, availability_check: Optional[Callable[[], bool]] = None):
        """
        Initialize adapter with optional timeout override and availability check.

        Args:
            timeout_seconds: Optional timeout override (default: 30)
                - None uses DEFAULT_TIMEOUT (30 seconds)
                - Must be positive integer if provided
                - Rejects: 0, negative, non-integer, boolean, float
            availability_check: Optional injected availability function (for testing)

        Raises:
            ValueError: If timeout_seconds is invalid (not None and not positive integer)
        """
        # Validate timeout_seconds
        if timeout_seconds is None:
            self.timeout_seconds = self.DEFAULT_TIMEOUT
        else:
            # Reject non-integer types (including bool which is subclass of int)
            if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int):
                raise ValueError(
                    f"timeout_seconds must be a positive integer, got {type(timeout_seconds).__name__}: {timeout_seconds}"
                )
            # Reject zero or negative
            if timeout_seconds <= 0:
                raise ValueError(
                    f"timeout_seconds must be positive, got {timeout_seconds}"
                )
            self.timeout_seconds = timeout_seconds

        self.logger = logging.getLogger("mediaman.openclaw_adapter")

        # Determine availability (use injected function or default check)
        if availability_check is not None:
            self.available = availability_check()
        else:
            self.available = self._check_availability()

        # Log initialization (safe metadata only)
        init_status = "available" if self.available else "unavailable"
        self.logger.debug(
            f"OpenClawAdapter initialized: status={init_status} timeout={self.timeout_seconds}s"
        )

    def _check_availability(self) -> bool:
        """
        Check if openclaw CLI is available.

        Safe: Returns boolean only, no credential checks, no error details logged.
        """
        try:
            result = subprocess.run(
                [self.CLI_PATH, "--version"],
                capture_output=True,
                timeout=5,
                text=True
            )
            available = result.returncode == 0
            return available
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            # Fail closed: unavailable on any error
            return False

    def is_available(self) -> bool:
        """
        Check if adapter is available and ready to generate.

        Returns: True if OpenClaw CLI is available.
        """
        return self.available

    def generate_article(
        self,
        prompt: str,
        agent_id: str = "main",
        thinking_level: str = "low"
    ) -> OpenClawResult:
        """
        Generate article using OpenClaw agent.

        Args:
            prompt: Plain text prompt (French writing instructions)
            agent_id: Agent identifier (default: main)
            thinking_level: Reasoning level (low, medium, high)

        Returns:
            OpenClawResult with content or error details.

        Safe: Never logs prompt, payload, or error content.
        """

        if not self.available:
            self.logger.debug(f"Generate article skipped: CLI unavailable")
            return OpenClawResult(
                success=False,
                provider_status="unavailable",
                error="OpenClaw CLI not available"
            )

        # Use temp file for multiline prompt
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.txt',
                delete=False,
                encoding='utf-8'
            ) as f:
                f.write(prompt)
                prompt_file = f.name
        except OSError as e:
            return OpenClawResult(
                success=False,
                provider_status="error",
                error=f"Failed to create prompt file: {e}"
            )

        try:
            # Build command
            cmd = [
                self.CLI_PATH,
                "agent",
                "--message-file", prompt_file,
                "--agent", agent_id,
                "--thinking", thinking_level,
                "--timeout", str(self.timeout_seconds)
            ]

            # Execute
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=self.timeout_seconds + 5,  # allow some overhead
                text=True
            )

            # Parse result
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                self.logger.warning(f"Generate article failed: returncode={result.returncode}")
                return OpenClawResult(
                    success=False,
                    provider_status="error",
                    error=f"CLI returned {result.returncode}: {error_msg[:200]}"
                )

            # Extract content from stdout
            content = result.stdout.strip()
            if not content:
                self.logger.warning(f"Generate article failed: empty output")
                return OpenClawResult(
                    success=False,
                    provider_status="error",
                    error="CLI returned empty output"
                )

            self.logger.debug(f"Generate article succeeded: length={len(content)}")
            return OpenClawResult(
                success=True,
                content=content,
                provider_status="success"
            )

        except subprocess.TimeoutExpired:
            self.logger.warning(f"Generate article failed: timeout after {self.timeout_seconds}s")
            return OpenClawResult(
                success=False,
                provider_status="timeout",
                error=f"OpenClaw agent timed out after {self.timeout_seconds} seconds"
            )

        except Exception as e:
            self.logger.warning(f"Generate article failed: {type(e).__name__}")
            return OpenClawResult(
                success=False,
                provider_status="error",
                error=f"Unexpected error: {type(e).__name__}: {str(e)[:200]}"
            )

        finally:
            # Cleanup temp file (safe)
            try:
                os.unlink(prompt_file)
            except OSError:
                # Safe: fail silently if cleanup fails
                pass
