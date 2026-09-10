import pytest
from unittest.mock import Mock, patch
from tools.influx_powerbi_export.influx_client import InfluxClient
from tools.influx_powerbi_export.docker_provider import DockerInternalCliQueryProvider


class TestProviderTimeoutConfiguration:
    """Test provider timeout configuration and parameter passing."""

    def test_provider_default_timeout_1200(self):
        """Provider should default to 1200 seconds (not 300)."""
        provider = DockerInternalCliQueryProvider()
        assert provider.timeout == 1200

    def test_provider_explicit_timeout_3600(self):
        """Provider should accept explicit 3600 seconds."""
        provider = DockerInternalCliQueryProvider(timeout=3600)
        assert provider.timeout == 3600

    def test_provider_timeout_stored(self):
        """Provider should store timeout for deadline calculation."""
        provider = DockerInternalCliQueryProvider(timeout=3600)
        assert hasattr(provider, 'timeout')
        assert provider.timeout == 3600


class TestDockerExecCommandGeneration:
    """Test that docker exec command is generated (not docker compose)."""

    def test_command_uses_docker_exec(self):
        """Command should use docker exec, not docker compose."""
        provider = DockerInternalCliQueryProvider()
        cmd = provider._build_docker_exec_cmd("test_query")

        # Verify structure: docker exec -i <service> influx query --raw <query>
        assert 'docker' in cmd
        assert 'exec' in cmd
        assert '-i' in cmd
        assert 'influx' in cmd
        assert 'query' in cmd
        assert '--raw' in cmd
        # Should NOT contain compose
        assert 'compose' not in cmd
        assert '-f' not in cmd

    def test_command_no_token_in_argv(self):
        """No token should appear in command arguments."""
        provider = DockerInternalCliQueryProvider()
        cmd = provider._build_docker_exec_cmd("from(bucket: \"test\")")
        cmd_str = ' '.join(cmd)

        assert 'INFLUX_TOKEN' not in cmd_str
        assert 'token=' not in cmd_str


class TestClientTimeoutPropagation:
    """Test that InfluxClient passes timeout to provider."""

    @patch('tools.influx_powerbi_export.influx_client.DockerInternalCliQueryProvider')
    def test_client_passes_timeout_to_provider(self, mock_provider_class):
        """InfluxClient should pass timeout to DockerInternalCliQueryProvider."""
        mock_provider = Mock()
        mock_provider_class.return_value = mock_provider

        # Create client with explicit timeout
        client = InfluxClient(query_timeout_seconds=3600)

        # Verify provider was instantiated with timeout parameter
        assert mock_provider_class.called
        call_kwargs = mock_provider_class.call_args[1]
        assert 'timeout' in call_kwargs
        assert call_kwargs['timeout'] == 3600

    @patch('tools.influx_powerbi_export.influx_client.DockerInternalCliQueryProvider')
    def test_client_default_timeout_1200(self, mock_provider_class):
        """InfluxClient should default to 1200 seconds."""
        mock_provider = Mock()
        mock_provider_class.return_value = mock_provider

        client = InfluxClient()
        assert client.query_timeout_seconds == 1200

    @patch('tools.influx_powerbi_export.influx_client.DockerInternalCliQueryProvider')
    def test_client_passes_default_timeout_to_provider(self, mock_provider_class):
        """InfluxClient should pass default 1200s timeout to provider."""
        mock_provider = Mock()
        mock_provider_class.return_value = mock_provider

        client = InfluxClient()
        call_kwargs = mock_provider_class.call_args[1]
        assert call_kwargs['timeout'] == 1200


class TestTimeoutBoundedness:
    """Test timeout properties (finite, positive, bounded)."""

    def test_timeout_is_positive_integer(self):
        """Timeout must be positive integer."""
        provider = DockerInternalCliQueryProvider(timeout=3600)
        assert isinstance(provider.timeout, int)
        assert provider.timeout > 0

    def test_timeout_is_finite(self):
        """Timeout must be finite (not inf)."""
        provider = DockerInternalCliQueryProvider(timeout=3600)
        assert provider.timeout < float('inf')

    def test_multiple_timeout_values(self):
        """Provider should handle various timeout values."""
        for timeout in [1200, 1800, 3600, 7200]:
            provider = DockerInternalCliQueryProvider(timeout=timeout)
            assert provider.timeout == timeout
            assert provider.timeout > 0


class TestProcessLifecycle:
    """Test process termination and timeout infrastructure."""

    def test_provider_has_terminate_method(self):
        """Provider should have process termination capability."""
        provider = DockerInternalCliQueryProvider()
        assert hasattr(provider, '_terminate_process_group')
        assert callable(provider._terminate_process_group)

    def test_provider_has_stream_drain_method(self):
        """Provider should have concurrent stream draining."""
        provider = DockerInternalCliQueryProvider()
        assert hasattr(provider, '_drain_concurrent_streams')
        assert callable(provider._drain_concurrent_streams)

    def test_provider_has_query_flux_method(self):
        """Provider should have query_flux execution method."""
        provider = DockerInternalCliQueryProvider()
        assert hasattr(provider, 'query_flux')
        assert callable(provider.query_flux)


class TestCredentialSafety:
    """Test that no credentials are exposed in timeout implementation."""

    def test_no_influx_url_attribute(self):
        """Provider should not have INFLUX_URL attribute."""
        provider = DockerInternalCliQueryProvider(timeout=3600)
        assert not hasattr(provider, 'url')
        assert not hasattr(provider, 'influx_url')
        assert not hasattr(provider, 'http_url')

    def test_command_no_http_headers(self):
        """Command should not contain Authorization headers."""
        provider = DockerInternalCliQueryProvider()
        cmd = provider._build_docker_exec_cmd("test")
        cmd_str = ' '.join(cmd)

        assert 'Authorization:' not in cmd_str
        assert 'Bearer ' not in cmd_str


class TestContainerNamePreservation:
    """Test that container service name is preserved."""

    def test_provider_has_service_name(self):
        """Provider should store container service name."""
        provider = DockerInternalCliQueryProvider(timeout=3600)
        assert hasattr(provider, 'service')
        assert provider.service == 'influxdb'

    def test_docker_exec_uses_service_name(self):
        """docker exec command should use the service name."""
        provider = DockerInternalCliQueryProvider(timeout=3600)
        cmd = provider._build_docker_exec_cmd("test")

        # Should contain the service name (influxdb)
        assert 'influxdb' in cmd
