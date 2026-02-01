"""
Unit tests for SDK client.

Tests the CaracalClient class for configuration loading, component initialization,
event emission, and fail-closed semantics.
"""

from decimal import Decimal
from pathlib import Path

import pytest

from caracal.exceptions import BudgetExceededError, ConnectionError
from caracal.sdk.client import CaracalClient
from caracal.sdk.context import BudgetCheckContext


class TestCaracalClient:
    """Test CaracalClient class."""

    def test_client_initialization_with_config(self, temp_dir, sample_pricebook_path):
        """Test initializing client with configuration file."""
        # Create config file
        config_path = temp_dir / "config.yaml"
        config_content = f"""
storage:
  agent_registry: {temp_dir}/agents.json
  policy_store: {temp_dir}/policies.json
  ledger: {temp_dir}/ledger.jsonl
  pricebook: {sample_pricebook_path}
  backup_dir: {temp_dir}/backups
  backup_count: 3

defaults:
  currency: USD
  time_window: daily

logging:
  level: INFO
  file: {temp_dir}/caracal.log
"""
        config_path.write_text(config_content)
        
        # Initialize client
        client = CaracalClient(config_path=str(config_path))
        
        # Verify components are initialized
        assert client.agent_registry is not None
        assert client.policy_store is not None
        assert client.pricebook is not None
        assert client.ledger_writer is not None
        assert client.ledger_query is not None
        assert client.policy_evaluator is not None
        assert client.metering_collector is not None

    def test_client_initialization_with_default_config(self, temp_dir, sample_pricebook_path, monkeypatch):
        """Test initializing client with default configuration."""
        # Mock the default config path to use temp directory
        def mock_get_default_config():
            from caracal.config.settings import CaracalConfig, StorageConfig, DefaultsConfig, LoggingConfig, PerformanceConfig
            return CaracalConfig(
                storage=StorageConfig(
                    agent_registry=str(temp_dir / "agents.json"),
                    policy_store=str(temp_dir / "policies.json"),
                    ledger=str(temp_dir / "ledger.jsonl"),
                    pricebook=str(sample_pricebook_path),
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

    def test_emit_event(self, temp_dir, sample_pricebook_path):
        """Test emitting a metering event."""
        # Create config
        config_path = temp_dir / "config.yaml"
        config_content = f"""
storage:
  agent_registry: {temp_dir}/agents.json
  policy_store: {temp_dir}/policies.json
  ledger: {temp_dir}/ledger.jsonl
  pricebook: {sample_pricebook_path}
  backup_dir: {temp_dir}/backups
  backup_count: 3
"""
        config_path.write_text(config_content)
        
        # Initialize client
        client = CaracalClient(config_path=str(config_path))
        
        # Register an agent first
        agent = client.agent_registry.register_agent(
            name="test-agent",
            owner="test@example.com"
        )
        
        # Emit event
        client.emit_event(
            agent_id=agent.agent_id,
            resource_type="openai.gpt4.input_tokens",
            quantity=Decimal("1000"),
            metadata={"model": "gpt-4"}
        )
        
        # Verify event was written to ledger
        ledger_path = temp_dir / "ledger.jsonl"
        assert ledger_path.exists()
        
        # Read ledger and verify event
        with open(ledger_path, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) == 1
        
        import json
        event_data = json.loads(lines[0])
        assert event_data["agent_id"] == agent.agent_id
        assert event_data["resource_type"] == "openai.gpt4.input_tokens"
        assert event_data["quantity"] == "1000"
        # Cost should be 1000 * 0.000030 = 0.030
        assert Decimal(event_data["cost"]) == Decimal("0.030")

    def test_check_budget_no_policy(self, temp_dir, sample_pricebook_path):
        """Test budget check with no policy (should fail closed)."""
        # Create config
        config_path = temp_dir / "config.yaml"
        config_content = f"""
storage:
  agent_registry: {temp_dir}/agents.json
  policy_store: {temp_dir}/policies.json
  ledger: {temp_dir}/ledger.jsonl
  pricebook: {sample_pricebook_path}
  backup_dir: {temp_dir}/backups
  backup_count: 3
"""
        config_path.write_text(config_content)
        
        # Initialize client
        client = CaracalClient(config_path=str(config_path))
        
        # Register an agent
        agent = client.agent_registry.register_agent(
            name="test-agent",
            owner="test@example.com"
        )
        
        # Check budget (should fail closed - no policy)
        result = client.check_budget(agent.agent_id)
        assert result is False

    def test_check_budget_within_limit(self, temp_dir, sample_pricebook_path):
        """Test budget check when agent is within budget."""
        # Create config
        config_path = temp_dir / "config.yaml"
        config_content = f"""
storage:
  agent_registry: {temp_dir}/agents.json
  policy_store: {temp_dir}/policies.json
  ledger: {temp_dir}/ledger.jsonl
  pricebook: {sample_pricebook_path}
  backup_dir: {temp_dir}/backups
  backup_count: 3
"""
        config_path.write_text(config_content)
        
        # Initialize client
        client = CaracalClient(config_path=str(config_path))
        
        # Register an agent
        agent = client.agent_registry.register_agent(
            name="test-agent",
            owner="test@example.com"
        )
        
        # Create a policy
        client.policy_store.create_policy(
            agent_id=agent.agent_id,
            limit_amount=Decimal("100.00"),
            time_window="daily"
        )
        
        # Check budget (should pass - no spending yet)
        result = client.check_budget(agent.agent_id)
        assert result is True

    def test_check_budget_exceeded(self, temp_dir, sample_pricebook_path):
        """Test budget check when agent has exceeded budget."""
        # Create config
        config_path = temp_dir / "config.yaml"
        config_content = f"""
storage:
  agent_registry: {temp_dir}/agents.json
  policy_store: {temp_dir}/policies.json
  ledger: {temp_dir}/ledger.jsonl
  pricebook: {sample_pricebook_path}
  backup_dir: {temp_dir}/backups
  backup_count: 3
"""
        config_path.write_text(config_content)
        
        # Initialize client
        client = CaracalClient(config_path=str(config_path))
        
        # Register an agent
        agent = client.agent_registry.register_agent(
            name="test-agent",
            owner="test@example.com"
        )
        
        # Create a policy with low limit
        client.policy_store.create_policy(
            agent_id=agent.agent_id,
            limit_amount=Decimal("0.01"),  # Very low limit
            time_window="daily"
        )
        
        # Emit event that exceeds budget
        client.emit_event(
            agent_id=agent.agent_id,
            resource_type="openai.gpt4.input_tokens",
            quantity=Decimal("1000"),  # Cost: 0.030
        )
        
        # Check budget (should fail - exceeded)
        result = client.check_budget(agent.agent_id)
        assert result is False

    def test_get_remaining_budget(self, temp_dir, sample_pricebook_path):
        """Test getting remaining budget for an agent."""
        # Create config
        config_path = temp_dir / "config.yaml"
        config_content = f"""
storage:
  agent_registry: {temp_dir}/agents.json
  policy_store: {temp_dir}/policies.json
  ledger: {temp_dir}/ledger.jsonl
  pricebook: {sample_pricebook_path}
  backup_dir: {temp_dir}/backups
  backup_count: 3
"""
        config_path.write_text(config_content)
        
        # Initialize client
        client = CaracalClient(config_path=str(config_path))
        
        # Register an agent
        agent = client.agent_registry.register_agent(
            name="test-agent",
            owner="test@example.com"
        )
        
        # Create a policy
        client.policy_store.create_policy(
            agent_id=agent.agent_id,
            limit_amount=Decimal("100.00"),
            time_window="daily"
        )
        
        # Emit event
        client.emit_event(
            agent_id=agent.agent_id,
            resource_type="openai.gpt4.input_tokens",
            quantity=Decimal("1000"),  # Cost: 0.030
        )
        
        # Get remaining budget
        remaining = client.get_remaining_budget(agent.agent_id)
        assert remaining is not None
        assert remaining == Decimal("99.970")  # 100.00 - 0.030

    def test_get_remaining_budget_no_policy(self, temp_dir, sample_pricebook_path):
        """Test getting remaining budget with no policy (should return None)."""
        # Create config
        config_path = temp_dir / "config.yaml"
        config_content = f"""
storage:
  agent_registry: {temp_dir}/agents.json
  policy_store: {temp_dir}/policies.json
  ledger: {temp_dir}/ledger.jsonl
  pricebook: {sample_pricebook_path}
  backup_dir: {temp_dir}/backups
  backup_count: 3
"""
        config_path.write_text(config_content)
        
        # Initialize client
        client = CaracalClient(config_path=str(config_path))
        
        # Register an agent
        agent = client.agent_registry.register_agent(
            name="test-agent",
            owner="test@example.com"
        )
        
        # Get remaining budget (should return None - no policy)
        remaining = client.get_remaining_budget(agent.agent_id)
        assert remaining is None

    def test_emit_event_with_metadata(self, temp_dir, sample_pricebook_path):
        """Test emitting event with metadata."""
        # Create config
        config_path = temp_dir / "config.yaml"
        config_content = f"""
storage:
  agent_registry: {temp_dir}/agents.json
  policy_store: {temp_dir}/policies.json
  ledger: {temp_dir}/ledger.jsonl
  pricebook: {sample_pricebook_path}
  backup_dir: {temp_dir}/backups
  backup_count: 3
"""
        config_path.write_text(config_content)
        
        # Initialize client
        client = CaracalClient(config_path=str(config_path))
        
        # Register an agent
        agent = client.agent_registry.register_agent(
            name="test-agent",
            owner="test@example.com"
        )
        
        # Emit event with metadata
        metadata = {
            "model": "gpt-4",
            "request_id": "req_123",
            "user": "test@example.com"
        }
        
        client.emit_event(
            agent_id=agent.agent_id,
            resource_type="openai.gpt4.input_tokens",
            quantity=Decimal("1000"),
            metadata=metadata
        )
        
        # Verify metadata was stored
        ledger_path = temp_dir / "ledger.jsonl"
        with open(ledger_path, 'r') as f:
            import json
            event_data = json.loads(f.readline())
        
        assert event_data["metadata"] == metadata


class TestBudgetCheckContext:
    """Test BudgetCheckContext class."""

    def test_budget_check_context_success(self, temp_dir, sample_pricebook_path):
        """Test budget check context when agent is within budget."""
        # Create config
        config_path = temp_dir / "config.yaml"
        config_content = f"""
storage:
  agent_registry: {temp_dir}/agents.json
  policy_store: {temp_dir}/policies.json
  ledger: {temp_dir}/ledger.jsonl
  pricebook: {sample_pricebook_path}
  backup_dir: {temp_dir}/backups
  backup_count: 3
"""
        config_path.write_text(config_content)
        
        # Initialize client
        client = CaracalClient(config_path=str(config_path))
        
        # Register an agent
        agent = client.agent_registry.register_agent(
            name="test-agent",
            owner="test@example.com"
        )
        
        # Create a policy
        client.policy_store.create_policy(
            agent_id=agent.agent_id,
            limit_amount=Decimal("100.00"),
            time_window="daily"
        )
        
        # Use budget check context (should succeed)
        with client.budget_check(agent_id=agent.agent_id):
            # Code that would incur costs
            pass

    def test_budget_check_context_exceeded(self, temp_dir, sample_pricebook_path):
        """Test budget check context when agent has exceeded budget."""
        # Create config
        config_path = temp_dir / "config.yaml"
        config_content = f"""
storage:
  agent_registry: {temp_dir}/agents.json
  policy_store: {temp_dir}/policies.json
  ledger: {temp_dir}/ledger.jsonl
  pricebook: {sample_pricebook_path}
  backup_dir: {temp_dir}/backups
  backup_count: 3
"""
        config_path.write_text(config_content)
        
        # Initialize client
        client = CaracalClient(config_path=str(config_path))
        
        # Register an agent
        agent = client.agent_registry.register_agent(
            name="test-agent",
            owner="test@example.com"
        )
        
        # Create a policy with low limit
        client.policy_store.create_policy(
            agent_id=agent.agent_id,
            limit_amount=Decimal("0.01"),  # Very low limit
            time_window="daily"
        )
        
        # Emit event that exceeds budget
        client.emit_event(
            agent_id=agent.agent_id,
            resource_type="openai.gpt4.input_tokens",
            quantity=Decimal("1000"),  # Cost: 0.030
        )
        
        # Use budget check context (should raise BudgetExceededError)
        with pytest.raises(BudgetExceededError) as exc_info:
            with client.budget_check(agent_id=agent.agent_id):
                # This code should not execute
                pass
        
        assert "Budget check failed" in str(exc_info.value)
        assert agent.agent_id in str(exc_info.value)

    def test_budget_check_context_no_policy(self, temp_dir, sample_pricebook_path):
        """Test budget check context with no policy (should fail closed)."""
        # Create config
        config_path = temp_dir / "config.yaml"
        config_content = f"""
storage:
  agent_registry: {temp_dir}/agents.json
  policy_store: {temp_dir}/policies.json
  ledger: {temp_dir}/ledger.jsonl
  pricebook: {sample_pricebook_path}
  backup_dir: {temp_dir}/backups
  backup_count: 3
"""
        config_path.write_text(config_content)
        
        # Initialize client
        client = CaracalClient(config_path=str(config_path))
        
        # Register an agent
        agent = client.agent_registry.register_agent(
            name="test-agent",
            owner="test@example.com"
        )
        
        # Use budget check context without policy (should raise BudgetExceededError)
        with pytest.raises(BudgetExceededError) as exc_info:
            with client.budget_check(agent_id=agent.agent_id):
                # This code should not execute
                pass
        
        assert "Budget check failed" in str(exc_info.value)
        assert "No active policy" in str(exc_info.value)

    def test_budget_check_context_with_exception(self, temp_dir, sample_pricebook_path):
        """Test that budget check context doesn't suppress exceptions."""
        # Create config
        config_path = temp_dir / "config.yaml"
        config_content = f"""
storage:
  agent_registry: {temp_dir}/agents.json
  policy_store: {temp_dir}/policies.json
  ledger: {temp_dir}/ledger.jsonl
  pricebook: {sample_pricebook_path}
  backup_dir: {temp_dir}/backups
  backup_count: 3
"""
        config_path.write_text(config_content)
        
        # Initialize client
        client = CaracalClient(config_path=str(config_path))
        
        # Register an agent
        agent = client.agent_registry.register_agent(
            name="test-agent",
            owner="test@example.com"
        )
        
        # Create a policy
        client.policy_store.create_policy(
            agent_id=agent.agent_id,
            limit_amount=Decimal("100.00"),
            time_window="daily"
        )
        
        # Use budget check context and raise exception inside
        with pytest.raises(ValueError) as exc_info:
            with client.budget_check(agent_id=agent.agent_id):
                # Raise an exception inside the context
                raise ValueError("Test exception")
        
        assert "Test exception" in str(exc_info.value)

    def test_budget_check_method_returns_context(self, temp_dir, sample_pricebook_path):
        """Test that budget_check method returns BudgetCheckContext instance."""
        # Create config
        config_path = temp_dir / "config.yaml"
        config_content = f"""
storage:
  agent_registry: {temp_dir}/agents.json
  policy_store: {temp_dir}/policies.json
  ledger: {temp_dir}/ledger.jsonl
  pricebook: {sample_pricebook_path}
  backup_dir: {temp_dir}/backups
  backup_count: 3
"""
        config_path.write_text(config_content)
        
        # Initialize client
        client = CaracalClient(config_path=str(config_path))
        
        # Register an agent
        agent = client.agent_registry.register_agent(
            name="test-agent",
            owner="test@example.com"
        )
        
        # Get context manager
        context = client.budget_check(agent_id=agent.agent_id)
        
        # Verify it's a BudgetCheckContext instance
        assert isinstance(context, BudgetCheckContext)
        assert context.client is client
        assert context.agent_id == agent.agent_id
