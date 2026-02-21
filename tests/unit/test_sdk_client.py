"""
Copyright (C) 2026 Garudex Labs.  All Rights Reserved.
Caracal, a product of Garudex Labs

Unit tests for SDK client.

Tests the CaracalClient class for configuration loading, component initialization,
event emission, and fail-closed semantics.
"""

from decimal import Decimal
from pathlib import Path

import pytest

from caracal.exceptions import ConnectionError
from caracal.sdk.client import CaracalClient


class TestCaracalClient:
    """Test CaracalClient class."""

    def test_client_initialization_with_config(self, temp_dir, make_config_yaml):
        """Test initializing client with configuration file."""
        # Create config file using helper that includes merkle settings
        config_path = temp_dir / "config.yaml"
        config_content = make_config_yaml()
        config_path.write_text(config_content)
        
        # Initialize client
        client = CaracalClient(config_path=str(config_path))
        
        # Verify components are initialized
        assert client.agent_registry is not None
        assert client.policy_store is not None
        assert client.ledger_writer is not None
        assert client.ledger_query is not None
        assert client.policy_evaluator is not None
        assert client.metering_collector is not None

    def test_client_initialization_with_default_config(self, temp_dir, monkeypatch):
        """Test initializing client with default configuration."""
        # Mock the default config path to use temp directory
        def mock_get_default_config():
            from caracal.config.settings import CaracalConfig, StorageConfig, DefaultsConfig, LoggingConfig, PerformanceConfig
            return CaracalConfig(
                storage=StorageConfig(
                    agent_registry=str(temp_dir / "agents.json"),
                    policy_store=str(temp_dir / "policies.json"),
                    ledger=str(temp_dir / "ledger.jsonl"),
                    backup_dir=str(temp_dir / "backups"),
                    backup_count=3,
                ),
                defaults=DefaultsConfig(),
                logging=LoggingConfig(file=str(temp_dir / "caracal.log")),
                performance=PerformanceConfig(),
            )
        
        monkeypatch.setattr("caracal.sdk.client.load_config", lambda x: mock_get_default_config())
        
        # Initialize client without config path
        client = CaracalClient()
        
        # Verify components are initialized
        assert client.agent_registry is not None
        assert client.policy_store is not None






# ===========================================================================
# CaracalClient & CaracalBuilder tests
# ===========================================================================


class TestCaracalClientV2:
    """Test the CaracalClient and CaracalBuilder."""

    def test_init_with_api_key(self):
        """CaracalClient(api_key=...) creates client with HttpAdapter."""
        from caracal.sdk.client import CaracalClient, SDKConfigurationError
        from caracal.sdk.adapters.http import HttpAdapter

        client = CaracalClient(api_key="sk_test_123")
        assert not client._is_legacy
        assert isinstance(client._adapter, HttpAdapter)
        assert client._adapter._api_key == "sk_test_123"
        client.close()

    def test_init_with_custom_base_url(self):
        """CaracalClient(api_key=, base_url=) uses custom URL."""
        from caracal.sdk.client import CaracalClient
        from caracal.sdk.adapters.http import HttpAdapter

        client = CaracalClient(api_key="sk_test_456", base_url="https://api.example.com")
        assert isinstance(client._adapter, HttpAdapter)
        assert client._adapter._base_url == "https://api.example.com"
        client.close()

    def test_init_with_mock_adapter(self):
        """CaracalClient with custom adapter skips api_key requirement."""
        from caracal.sdk.client import CaracalClient
        from caracal.sdk.adapters.mock import MockAdapter

        mock = MockAdapter(responses={})
        client = CaracalClient(adapter=mock)
        assert not client._is_legacy
        assert client._adapter is mock
        client.close()

    def test_init_requires_api_key_or_adapter(self):
        """CaracalClient without api_key or adapter raises SDKConfigurationError."""
        from caracal.sdk.client import CaracalClient, SDKConfigurationError

        with pytest.raises(SDKConfigurationError, match="requires either"):
            CaracalClient()

    def test_context_returns_context_manager(self):
        """client.context is a ContextManager."""
        from caracal.sdk.client import CaracalClient
        from caracal.sdk.context import ContextManager

        client = CaracalClient(api_key="sk_test_ctx")
        assert isinstance(client.context, ContextManager)
        client.close()

    def test_context_checkout_returns_scoped_context(self):
        """client.context.checkout() returns ScopeContext with correct IDs."""
        from caracal.sdk.client import CaracalClient
        from caracal.sdk.context import ScopeContext

        client = CaracalClient(api_key="sk_test_scope")
        ctx = client.context.checkout(
            organization_id="org_1",
            workspace_id="ws_2",
            project_id="proj_3",
        )
        assert isinstance(ctx, ScopeContext)
        assert ctx.organization_id == "org_1"
        assert ctx.workspace_id == "ws_2"
        assert ctx.project_id == "proj_3"
        client.close()

    def test_agents_returns_agent_operations(self):
        """client.agents shortcut returns AgentOperations."""
        from caracal.sdk.client import CaracalClient
        from caracal.sdk.agents import AgentOperations

        client = CaracalClient(api_key="sk_test_agents")
        assert isinstance(client.agents, AgentOperations)
        client.close()

    def test_mandates_returns_mandate_operations(self):
        """client.mandates shortcut returns MandateOperations."""
        from caracal.sdk.client import CaracalClient
        from caracal.sdk.mandates import MandateOperations

        client = CaracalClient(api_key="sk_test_mandates")
        assert isinstance(client.mandates, MandateOperations)
        client.close()

    def test_use_installs_extension(self):
        """client.use(extension) calls install and chains."""
        from caracal.sdk.client import CaracalClient
        from caracal.sdk.extensions import CaracalExtension
        from caracal.sdk.hooks import HookRegistry

        class TestExtension(CaracalExtension):
            installed = False

            @property
            def name(self) -> str:
                return "test-ext"

            @property
            def version(self) -> str:
                return "1.0.0"

            def install(self, hooks: HookRegistry) -> None:
                TestExtension.installed = True

        client = CaracalClient(api_key="sk_test_ext")
        result = client.use(TestExtension())
        assert result is client  # chaining
        assert TestExtension.installed
        assert len(client._extensions) == 1
        client.close()



class TestCaracalBuilderV2:
    """Test the CaracalBuilder fluent API."""

    def test_builder_basic_build(self):
        """Builder with api_key builds successfully."""
        from caracal.sdk.client import CaracalBuilder, CaracalClient

        client = CaracalBuilder().set_api_key("sk_build_1").build()
        assert isinstance(client, CaracalClient)
        assert not client._is_legacy
        client.close()

    def test_builder_custom_base_url(self):
        """Builder with custom base_url."""
        from caracal.sdk.client import CaracalBuilder
        from caracal.sdk.adapters.http import HttpAdapter

        client = (
            CaracalBuilder()
            .set_api_key("sk_build_2")
            .set_base_url("https://custom.api.io")
            .build()
        )
        assert isinstance(client._adapter, HttpAdapter)
        assert client._adapter._base_url == "https://custom.api.io"
        client.close()

    def test_builder_with_transport(self):
        """Builder with custom transport adapter."""
        from caracal.sdk.client import CaracalBuilder
        from caracal.sdk.adapters.mock import MockAdapter

        mock = MockAdapter(responses={})
        client = CaracalBuilder().set_transport(mock).build()
        assert client._adapter is mock
        client.close()

    def test_builder_with_extension(self):
        """Builder .use() queues extensions, build() installs them."""
        from caracal.sdk.client import CaracalBuilder
        from caracal.sdk.extensions import CaracalExtension
        from caracal.sdk.hooks import HookRegistry

        installed_hooks = []

        class BuilderExt(CaracalExtension):
            @property
            def name(self) -> str:
                return "builder-ext"

            @property
            def version(self) -> str:
                return "2.0.0"

            def install(self, hooks: HookRegistry) -> None:
                installed_hooks.append(hooks)

        client = (
            CaracalBuilder()
            .set_api_key("sk_ext_build")
            .use(BuilderExt())
            .build()
        )
        assert len(installed_hooks) == 1
        assert len(client._extensions) == 1
        client.close()

    def test_builder_fires_initialize_hooks(self):
        """Builder.build() fires on_initialize hooks."""
        from caracal.sdk.client import CaracalBuilder
        from caracal.sdk.extensions import CaracalExtension
        from caracal.sdk.hooks import HookRegistry

        init_called = []

        class InitExt(CaracalExtension):
            @property
            def name(self) -> str:
                return "init-ext"

            @property
            def version(self) -> str:
                return "1.0.0"

            def install(self, hooks: HookRegistry) -> None:
                hooks.on_initialize(lambda: init_called.append(True))

        client = (
            CaracalBuilder()
            .set_api_key("sk_init")
            .use(InitExt())
            .build()
        )
        assert len(init_called) == 1
        client.close()

    def test_builder_no_key_no_adapter_raises(self):
        """Builder without api_key or transport raises SDKConfigurationError."""
        from caracal.sdk.client import CaracalBuilder, SDKConfigurationError

        with pytest.raises(SDKConfigurationError, match="requires either"):
            CaracalBuilder().build()

    def test_builder_fluent_chaining(self):
        """All builder methods return self for chaining."""
        from caracal.sdk.client import CaracalBuilder

        builder = CaracalBuilder()
        assert builder.set_api_key("x") is builder
        assert builder.set_base_url("http://x") is builder
