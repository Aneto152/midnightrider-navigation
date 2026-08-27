"""
OpenClaw Agent CLI adapter for LLM-based content generation.

Provides a safe, testable interface to the local OpenClaw agent command.
Fails closed if the CLI is unavailable or returns invalid output.
"""

import subprocess
import os
import tempfile
import json
from typing import Optional, Tuple
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
    
    Notes:
    - No --deliver (output only, no Telegram here)
    - No credentials in environment
    - Fails closed if CLI unavailable
    - All subprocess calls must be mockable in tests
    """
    
    CLI_PATH = "openclaw"  # Assumes openclaw is in PATH
    DEFAULT_TIMEOUT = 30  # seconds
    
    def __init__(self, timeout_seconds: Optional[int] = None):
        """Initialize adapter with optional timeout override."""
        self.timeout_seconds = timeout_seconds or self.DEFAULT_TIMEOUT
        self.available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check if openclaw CLI is available."""
        try:
            result = subprocess.run(
                [self.CLI_PATH, "--version"],
                capture_output=True,
                timeout=5,
                text=True
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False
    
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
        """
        
        if not self.available:
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
                return OpenClawResult(
                    success=False,
                    provider_status="error",
                    error=f"CLI returned {result.returncode}: {error_msg[:200]}"
                )
            
            # Extract content from stdout
            content = result.stdout.strip()
            if not content:
                return OpenClawResult(
                    success=False,
                    provider_status="error",
                    error="CLI returned empty output"
                )
            
            return OpenClawResult(
                success=True,
                content=content,
                provider_status="success"
            )
        
        except subprocess.TimeoutExpired:
            return OpenClawResult(
                success=False,
                provider_status="timeout",
                error=f"OpenClaw agent timed out after {self.timeout_seconds} seconds"
            )
        
        except Exception as e:
            return OpenClawResult(
                success=False,
                provider_status="error",
                error=f"Unexpected error: {type(e).__name__}: {str(e)[:200]}"
            )
        
        finally:
            # Cleanup temp file
            try:
                os.unlink(prompt_file)
            except OSError:
                pass
