"""
Unit tests for policy management.
"""

import json
import uuid
from decimal import Decimal
from pathlib import Path

import pytest

from caracal.core.identity import AgentRegistry
from caracal.core.policy import BudgetPolicy, PolicyStore
from caracal.exceptions import (
    AgentNotFoundError,
    InvalidPolicyError,
)


class TestBudgetPolicy:
    """Test BudgetPolicy dataclass."""

    def test_budget_policy_creation(self):
        """Test creating a BudgetPolicy."""
        policy = BudgetPolicy(
            policy_id="660e8400-e29b-41d4-a716-446655440001",
            agent_id="550e8400-e29b-41d4-a716-446655440000",
            limit_amount="100.00",
            time_window="daily",
            currency="USD",
            created_at="2024-01-15T10:05:00Z",
            active=True
        )
        
        assert policy.policy_id == "660e8400-e29b-41d4-a716-446655440001"
        assert policy.agent_id == "550e8400-e29b-41d4-a716-446655440000"
        assert policy.limit_amount == "100.00"
        assert policy.time_window == "daily"
        assert policy.currency == "USD"
        assert policy.active is True

    def test_budget_policy_to_dict(self):
        """Test converting BudgetPolicy to dictionary."""
        policy = BudgetPolicy(
            policy_id="660e8400-e29b-41d4-a716-446655440001",
            agent_id="550e8400-e29b-41d4-a716-446655440000",
            limit_amount="100.00",
            time_window="daily",
            currency="USD",
            created_at="2024-01-15T10:05:00Z",
            active=True
        )
        
        data = policy.to_dict()
        assert data["policy_id"] == "660e8400-e29b-41d4-a716-446655440001"
        assert data["agent_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert data["limit_amount"] == "100.00"

    def test_budget_policy_from_dict(self):
        """Test creating BudgetPolicy from dictionary."""
        data = {
            "policy_id": "660e8400-e29b-41d4-a716-446655440001",
            "agent_id": "550e8400-e29b-41d4-a716-446655440000",
            "limit_amount": "100.00",
            "time_window": "daily",
            "currency": "USD",
            "created_at": "2024-01-15T10:05:00Z",
            "active": True
        }
        
        policy = BudgetPolicy.from_dict(data)
        assert policy.policy_id == "660e8400-e29b-41d4-a716-446655440001"
        assert policy.agent_id == "550e8400-e29b-41d4-a716-446655440000"
        assert policy.limit_amount == "100.00"

    def test_get_limit_decimal(self):
        """Test converting limit amount to Decimal."""
        policy = BudgetPolicy(
            policy_id="660e8400-e29b-41d4-a716-446655440001",
            agent_id="550e8400-e29b-41d4-a716-446655440000",
            limit_amount="100.50",
            time_window="daily",
            currency="USD",
            created_at="2024-01-15T10:05:00Z",
            active=True
        )
        
        limit = policy.get_limit_decimal()
        assert isinstance(limit, Decimal)
        assert limit == Decimal("100.50")


class TestPolicyStore:
    """Test PolicyStore class."""

    def test_policy_store_initialization(self, temp_dir):
        """Test initializing a PolicyStore."""
        policy_path = temp_dir / "policies.json"
        store = PolicyStore(str(policy_path))
        
        assert store.policy_path == policy_path
        assert store.backup_count == 3
        assert len(store.list_all_policies()) == 0

    def test_create_policy(self, temp_dir):
        """Test creating a new policy."""
        policy_path = temp_dir / "policies.json"
        store = PolicyStore(str(policy_path))
        
        policy = store.create_policy(
            agent_id="550e8400-e29b-41d4-a716-446655440000",
            limit_amount=Decimal("100.00"),
            time_window="daily",
            currency="USD"
        )
        
        # Verify policy properties
        assert policy.agent_id == "550e8400-e29b-41d4-a716-446655440000"
        assert policy.limit_amount == "100.00"
        assert policy.time_window == "daily"
        assert policy.currency == "USD"
        assert policy.active is True
        
        # Verify UUID v4 format
        try:
            uuid_obj = uuid.UUID(policy.policy_id, version=4)
            assert str(uuid_obj) == policy.policy_id
        except ValueError:
            pytest.fail("Policy ID is not a valid UUID v4")
        
        # Verify timestamp format
        assert policy.created_at.endswith("Z")
        assert "T" in policy.created_at

    def test_create_policy_with_agent_validation(self, temp_dir):
        """Test creating policy with agent existence validation."""
        # Create agent registry
        registry_path = temp_dir / "agents.json"
        registry = AgentRegistry(str(registry_path))
        agent = registry.register_agent(
            name="test-agent",
            owner="test@example.com"
        )
        
        # Create policy store with registry
        policy_path = temp_dir / "policies.json"
        store = PolicyStore(str(policy_path), agent_registry=registry)
        
        # Create policy for existing agent (should succeed)
        policy = store.create_policy(
            agent_id=agent.agent_id,
            limit_amount=Decimal("100.00")
        )
        assert policy.agent_id == agent.agent_id

    def test_create_policy_nonexistent_agent(self, temp_dir):
        """Test creating policy for non-existent agent."""
        # Create agent registry
        registry_path = temp_dir / "agents.json"
        registry = AgentRegistry(str(registry_path))
        
        # Create policy store with registry
        policy_path = temp_dir / "policies.json"
        store = PolicyStore(str(policy_path), agent_registry=registry)
        
        # Attempt to create policy for non-existent agent
        with pytest.raises(AgentNotFoundError) as exc_info:
            store.create_policy(
                agent_id="non-existent-id",
                limit_amount=Decimal("100.00")
            )
        
        assert "non-existent-id" in str(exc_info.value)

    def test_create_policy_zero_limit(self, temp_dir):
        """Test that zero limit is rejected."""
        policy_path = temp_dir / "policies.json"
        store = PolicyStore(str(policy_path))
        
        with pytest.raises(InvalidPolicyError) as exc_info:
            store.create_policy(
                agent_id="550e8400-e29b-41d4-a716-446655440000",
                limit_amount=Decimal("0.00")
            )
        
        assert "positive" in str(exc_info.value).lower()

    def test_create_policy_negative_limit(self, temp_dir):
        """Test that negative limit is rejected."""
        policy_path = temp_dir / "policies.json"
        store = PolicyStore(str(policy_path))
        
        with pytest.raises(InvalidPolicyError) as exc_info:
            store.create_policy(
                agent_id="550e8400-e29b-41d4-a716-446655440000",
                limit_amount=Decimal("-50.00")
            )
        
        assert "positive" in str(exc_info.value).lower()

    def test_create_policy_invalid_time_window(self, temp_dir):
        """Test that non-daily time window is rejected in v0.1."""
        policy_path = temp_dir / "policies.json"
        store = PolicyStore(str(policy_path))
        
        with pytest.raises(InvalidPolicyError) as exc_info:
            store.create_policy(
                agent_id="550e8400-e29b-41d4-a716-446655440000",
                limit_amount=Decimal("100.00"),
                time_window="weekly"
            )
        
        assert "daily" in str(exc_info.value).lower()

    def test_get_policies(self, temp_dir):
        """Test retrieving policies for an agent."""
        policy_path = temp_dir / "policies.json"
        store = PolicyStore(str(policy_path))
        
        agent_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Create policy
        policy = store.create_policy(
            agent_id=agent_id,
            limit_amount=Decimal("100.00")
        )
        
        # Retrieve policies
        policies = store.get_policies(agent_id)
        assert len(policies) == 1
        assert policies[0].policy_id == policy.policy_id
        assert policies[0].agent_id == agent_id

    def test_get_policies_no_policies(self, temp_dir):
        """Test retrieving policies for agent with no policies."""
        policy_path = temp_dir / "policies.json"
        store = PolicyStore(str(policy_path))
        
        policies = store.get_policies("non-existent-agent")
        assert len(policies) == 0

    def test_get_policies_multiple_agents(self, temp_dir):
        """Test that policies are isolated by agent."""
        policy_path = temp_dir / "policies.json"
        store = PolicyStore(str(policy_path))
        
        agent1_id = "550e8400-e29b-41d4-a716-446655440000"
        agent2_id = "660e8400-e29b-41d4-a716-446655440001"
        
        # Create policies for different agents
        policy1 = store.create_policy(
            agent_id=agent1_id,
            limit_amount=Decimal("100.00")
        )
        policy2 = store.create_policy(
            agent_id=agent2_id,
            limit_amount=Decimal("200.00")
        )
        
        # Verify isolation
        agent1_policies = store.get_policies(agent1_id)
        assert len(agent1_policies) == 1
        assert agent1_policies[0].policy_id == policy1.policy_id
        
        agent2_policies = store.get_policies(agent2_id)
        assert len(agent2_policies) == 1
        assert agent2_policies[0].policy_id == policy2.policy_id

    def test_list_all_policies(self, temp_dir):
        """Test listing all policies."""
        policy_path = temp_dir / "policies.json"
        store = PolicyStore(str(policy_path))
        
        # Create multiple policies
        policy1 = store.create_policy(
            agent_id="550e8400-e29b-41d4-a716-446655440000",
            limit_amount=Decimal("100.00")
        )
        policy2 = store.create_policy(
            agent_id="660e8400-e29b-41d4-a716-446655440001",
            limit_amount=Decimal("200.00")
        )
        
        # List all policies
        policies = store.list_all_policies()
        assert len(policies) == 2
        
        policy_ids = {p.policy_id for p in policies}
        assert policy1.policy_id in policy_ids
        assert policy2.policy_id in policy_ids

    def test_persistence(self, temp_dir):
        """Test that policies are persisted to disk."""
        policy_path = temp_dir / "policies.json"
        store = PolicyStore(str(policy_path))
        
        # Create policy
        policy = store.create_policy(
            agent_id="550e8400-e29b-41d4-a716-446655440000",
            limit_amount=Decimal("100.00"),
            time_window="daily",
            currency="USD"
        )
        
        # Verify file was created
        assert policy_path.exists()
        
        # Verify file content
        with open(policy_path, 'r') as f:
            data = json.load(f)
        
        assert len(data) == 1
        assert data[0]["policy_id"] == policy.policy_id
        assert data[0]["agent_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert data[0]["limit_amount"] == "100.00"
        assert data[0]["time_window"] == "daily"
        assert data[0]["currency"] == "USD"
        assert data[0]["active"] is True

    def test_load_from_disk(self, temp_dir):
        """Test loading policies from disk."""
        policy_path = temp_dir / "policies.json"
        
        # Create first store and create policy
        store1 = PolicyStore(str(policy_path))
        policy = store1.create_policy(
            agent_id="550e8400-e29b-41d4-a716-446655440000",
            limit_amount=Decimal("100.00")
        )
        
        # Create second store (should load from disk)
        store2 = PolicyStore(str(policy_path))
        
        # Verify policy was loaded
        policies = store2.get_policies(policy.agent_id)
        assert len(policies) == 1
        assert policies[0].policy_id == policy.policy_id
        assert policies[0].agent_id == policy.agent_id
        assert policies[0].limit_amount == "100.00"

    def test_backup_creation(self, temp_dir):
        """Test that backups are created."""
        policy_path = temp_dir / "policies.json"
        store = PolicyStore(str(policy_path))
        
        # Create first policy (creates initial file)
        store.create_policy(
            agent_id="550e8400-e29b-41d4-a716-446655440000",
            limit_amount=Decimal("100.00")
        )
        
        # Create second policy (should create backup)
        store.create_policy(
            agent_id="660e8400-e29b-41d4-a716-446655440001",
            limit_amount=Decimal("200.00")
        )
        
        # Verify backup exists
        backup_path = Path(f"{policy_path}.bak.1")
        assert backup_path.exists()

    def test_decimal_precision(self, temp_dir):
        """Test that decimal precision is preserved."""
        policy_path = temp_dir / "policies.json"
        store = PolicyStore(str(policy_path))
        
        # Create policy with precise decimal
        policy = store.create_policy(
            agent_id="550e8400-e29b-41d4-a716-446655440000",
            limit_amount=Decimal("123.456789")
        )
        
        # Verify precision is preserved
        assert policy.limit_amount == "123.456789"
        
        # Reload from disk
        store2 = PolicyStore(str(policy_path))
        policies = store2.get_policies(policy.agent_id)
        assert policies[0].limit_amount == "123.456789"
        
        # Verify Decimal conversion
        limit = policies[0].get_limit_decimal()
        assert limit == Decimal("123.456789")
