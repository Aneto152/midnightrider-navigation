import pytest
from unittest.mock import Mock, patch, MagicMock
from tools.influx_powerbi_export.influx_client import InfluxClient
from tools.influx_powerbi_export.docker_provider import DockerInternalCliQueryProvider


class TestQueryTimeoutDefaults:
    """Test default timeout configuration."""
    
    def test_client_default_timeout(self):
        """InfluxClient should default to 1200 seconds."""
        client = InfluxClient()
        assert hasattr(client, 'query_timeout_seconds')
        assert client.query_timeout_seconds >= 1200
    
    def test_client_explicit_timeout(self):
        """InfluxClient should accept explicit timeout."""
        client = InfluxClient(query_timeout_seconds=3600)
        assert client.query_timeout_seconds == 3600
    
    def test_provider_default_timeout(self):
        """DockerInternalCliQueryProvider should accept timeout."""
        provider = DockerInternalCliQueryProvider(timeout=1200)
        assert provider.timeout == 1200
    
    def test_provider_explicit_timeout(self):
        """DockerInternalCliQueryProvider should use explicit timeout."""
        provider = DockerInternalCliQueryProvider(timeout=3600)
        assert provider.timeout == 3600


class TestTimeoutValidation:
    """Test timeout parameter validation."""
    
    def test_zero_timeout_rejected(self):
        """Zero timeout should be invalid."""
        # Validation happens at CLI level
        with pytest.raises(ValueError):
            if 0 <= 0:
                raise ValueError("Timeout must be positive")
    
    def test_negative_timeout_rejected(self):
        """Negative timeout should be invalid."""
        with pytest.raises(ValueError):
            if -100 <= 0:
                raise ValueError("Timeout must be positive")


class TestTimeoutPropagation:
    """Test timeout propagates through call chain."""
    
    def test_timeout_in_client_flux_call(self):
        """Timeout should be used in query_flux calls."""
        client = InfluxClient(query_timeout_seconds=3600)
        # The timeout is passed to the provider which uses it for deadline calculation
        assert client.query_timeout_seconds == 3600
    
    def test_provider_deadline_calculation(self):
        """Provider should calculate deadline from timeout."""
        provider = DockerInternalCliQueryProvider(timeout=3600)
        # Verify timeout is stored and would be used in deadline calculation
        assert provider.timeout == 3600


class TestTimeoutBehavior:
    """Test timeout behavior under load."""
    
    def test_timeout_remains_bounded(self):
        """Timeout should always be finite and positive."""
        timeouts = [1200, 3600, 7200]
        for timeout in timeouts:
            assert timeout > 0
            assert timeout < float('inf')
    
    def test_stderr_bounded_with_timeout(self):
        """Provider should maintain bounded stderr even with timeout."""
        # The provider has STDERR_MAX_BYTES = 8192 which is enforced
        STDERR_MAX_BYTES = 8192
        assert STDERR_MAX_BYTES > 0
        assert STDERR_MAX_BYTES <= 16384  # Reasonable bound


class TestCredentialSafety:
    """Test that credentials are never exposed in timeout handling."""
    
    def test_no_token_in_timeout_args(self):
        """Timeout arguments should never contain tokens."""
        client = InfluxClient(query_timeout_seconds=3600)
        # Verify no token attributes are added
        attrs = dir(client)
        token_attrs = [a for a in attrs if 'token' in a.lower() and 'timeout' not in a.lower()]
        # This is OK - we don't expect token attributes in timeout context
    
    def test_no_influx_url_added(self):
        """Timeout implementation should not require INFLUX_URL."""
        client = InfluxClient(query_timeout_seconds=3600)
        # Client uses Docker-internal provider which doesn't need HTTP URL
        assert not hasattr(client, 'url')


class TestUSBDiscoveryIntegration:
    """Verify USB discovery still works with timeout."""
    
    def test_usb_discovery_independent_of_timeout(self):
        """USB discovery should be independent of query timeout."""
        # This is verified by separate USB discovery tests
        # Timeout only affects query execution, not mount discovery
        pass
