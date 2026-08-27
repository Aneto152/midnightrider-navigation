"""
Tests for OpenClaw adapter with mocked subprocess.
"""

import pytest
from unittest.mock import patch, MagicMock
from mediaman.openclaw_adapter import OpenClawAdapter, OpenClawResult


class TestOpenClawAdapter:
    """Test OpenClaw CLI adapter."""
    
    @patch('mediaman.openclaw_adapter.subprocess.run')
    def test_successful_generation(self, mock_run):
        """Successful generation should return content."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Midnight Rider navigue avec excellence à 8.5 nœuds au 270°. Le vent du 180° favorise la course. Excellentes conditions pour continuer.",
            stderr=""
        )
        
        adapter = OpenClawAdapter()
        # Mock availability check
        adapter.available = True
        
        result = adapter.generate_article(
            prompt="Générez un article sur Midnight Rider...",
            agent_id="main"
        )
        
        assert result.success
        assert "Midnight Rider" in result.content
        assert result.provider_status == "success"
    
    @patch('mediaman.openclaw_adapter.subprocess.run')
    def test_cli_not_available(self, mock_run):
        """Generate should fail if CLI unavailable."""
        adapter = OpenClawAdapter()
        adapter.available = False
        
        result = adapter.generate_article(
            prompt="Test prompt"
        )
        
        assert not result.success
        assert result.provider_status == "unavailable"
        assert "not available" in result.error.lower()
    
    @patch('mediaman.openclaw_adapter.subprocess.run')
    def test_cli_error(self, mock_run):
        """CLI error should return error result."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Invalid argument"
        )
        
        adapter = OpenClawAdapter()
        adapter.available = True
        
        result = adapter.generate_article(
            prompt="Test prompt"
        )
        
        assert not result.success
        assert result.provider_status == "error"
        assert "Invalid argument" in result.error
    
    @patch('mediaman.openclaw_adapter.subprocess.run')
    def test_timeout(self, mock_run):
        """Timeout should return timeout result."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired('openclaw', 30)
        
        adapter = OpenClawAdapter(timeout_seconds=30)
        adapter.available = True
        
        result = adapter.generate_article(
            prompt="Test prompt"
        )
        
        assert not result.success
        assert result.provider_status == "timeout"
        assert "30 seconds" in result.error
    
    @patch('mediaman.openclaw_adapter.subprocess.run')
    def test_empty_output(self, mock_run):
        """Empty CLI output should fail."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        adapter = OpenClawAdapter()
        adapter.available = True
        
        result = adapter.generate_article(
            prompt="Test prompt"
        )
        
        assert not result.success
        assert "empty output" in result.error.lower()
    
    @patch('mediaman.openclaw_adapter.subprocess.run')
    def test_file_handling(self, mock_run):
        """Prompt file should be created and cleaned up."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Generated content",
            stderr=""
        )
        
        adapter = OpenClawAdapter()
        adapter.available = True
        
        with patch('tempfile.NamedTemporaryFile') as mock_tempfile:
            mock_tempfile.return_value.__enter__.return_value.name = "/tmp/test_prompt.txt"
            
            result = adapter.generate_article(
                prompt="Test prompt"
            )
            
            assert result.success
            # Verify the command was called with --message-file
            call_args = mock_run.call_args[0][0]
            assert "--message-file" in call_args
    
    @patch('mediaman.openclaw_adapter.subprocess.run')
    def test_cli_contract_verification(self, mock_run):
        """Verify OpenClaw CLI is called with correct arguments."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Content",
            stderr=""
        )
        
        adapter = OpenClawAdapter(timeout_seconds=45)
        adapter.available = True
        
        adapter.generate_article(
            prompt="Test",
            agent_id="custom-agent",
            thinking_level="medium"
        )
        
        # Verify the command structure
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "openclaw"
        assert call_args[1] == "agent"
        assert "--agent" in call_args
        assert "custom-agent" in call_args
        assert "--thinking" in call_args
        assert "medium" in call_args
        assert "--timeout" in call_args
        assert "45" in call_args
        # Should NOT use --deliver
        assert "--deliver" not in call_args
        # Should NOT use --timeout-seconds
        assert "--timeout-seconds" not in call_args
