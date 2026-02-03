"""
Integration tests for multi-policy support.

Tests the complete flow of multi-policy evaluation including:
- Creating multiple policies for an agent
- Evaluating all policies together
- Handling policy conflicts
"""

import pytest
from decimal import Decimal
from datetime import datetime
from pathlib import Path

from caracal.core.policy import PolicyStore, PolicyEvaluator
from caracal.core.ledger import LedgerWriter, LedgerQuery
from caracal.core.identity import AgentRegistry
from caracal.core.time_windows import TimeWindowCalculator


class TestMultiPolicyIntegration:
    """Integration tests for multi-policy support."""

    def test_multi_policy_budget_enforcement(self, temp_dir):
        """
        Test complete multi-policy budget enforcement flow.
        
        Scenario:
        - Agent has two policies: daily limit of 100 and daily limit of 150
        - Agent spends 80 (within both limits)
        - Request for 30 more should be denied (would exceed first policy)
        """
        # Setup
        policy_path = temp_dir / "policies.json"
        ledger_path = temp_dir / "ledger.jsonl"
        registry_path = temp_dir / "agents.json"
        
        # Create agent
        agent_registry = AgentRegistry(str(registry_path))
        agent_id = "550e8400-e29b-41d4-a716-446655440000"
        agent_registry.create_agent(
            agent_id=agent_id,
            name="Test Agent",
            agent_type="test"
        )
        
        # Create policy store
        policy_store = PolicyStore(str(policy_path), agent_registry=agent_registry)
        
        # Create two policies
        policy1 = policy_store.create_policy(
            agent_id=agent_id,
            limit_amount=Decimal("100.00"),
            time_window="daily"
        )
        
        policy2 = policy_store.create_policy(
            agent_id=agent_id,
            limit_amount=Decimal("150.00"),
            time_window="daily"
        )
        
        # Create ledger with initial spending
        ledger_writer = LedgerWriter(str(ledger_path))
        ledger_writer.append_event(
            agent_id=agent_id,
            resource_type="test.resource",
            quantity=Decimal("10"),
            cost=Decimal("80.00"),
            timestamp=datetime.utcnow()
        )
        
        # Create evaluator
        ledger_query = LedgerQuery(str(ledger_path))
        time_window_calculator = TimeWindowCalculator()
        evaluator = PolicyEvaluator(
            policy_store,
            ledger_query,
            time_window_calculator=time_window_calculator
        )
        
        # Check budget without estimated cost (should pass)
        decision1 = evaluator.check_budget(agent_id)
        assert decision1.allowed is True
        assert len(decision1.policy_decisions) == 2
        
        # Check budget with estimated cost of 30 (should fail - would exceed policy1)
        decision2 = evaluator.check_budget(agent_id, estimated_cost=Decimal("30.00"))
        assert decision2.allowed is False
        assert decision2.failed_policy_id == policy1.policy_id
        assert "100.00" in decision2.reason  # Policy1 limit
        
        # Check budget with estimated cost of 15 (should pass - within both limits)
        decision3 = evaluator.check_budget(agent_id, estimated_cost=Decimal("15.00"))
        assert decision3.allowed is True
        assert decision3.remaining_budget == Decimal("5.00")  # Min(100-80-15, 150-80-15) = 5

    def test_policy_status_reporting(self, temp_dir):
        """
        Test that policy status correctly identifies closest to limit.
        
        Scenario:
        - Agent has two policies with different utilization levels
        - Status should identify which policy is closest to limit
        """
        # Setup
        policy_path = temp_dir / "policies.json"
        ledger_path = temp_dir / "ledger.jsonl"
        registry_path = temp_dir / "agents.json"
        
        # Create agent
        agent_registry = AgentRegistry(str(registry_path))
        agent_id = "550e8400-e29b-41d4-a716-446655440000"
        agent_registry.create_agent(
            agent_id=agent_id,
            name="Test Agent",
            agent_type="test"
        )
        
        # Create policy store
        policy_store = PolicyStore(str(policy_path), agent_registry=agent_registry)
        
        # Create two policies with different limits
        policy1 = policy_store.create_policy(
            agent_id=agent_id,
            limit_amount=Decimal("100.00"),  # Will be 90% utilized
            time_window="daily"
        )
        
        policy2 = policy_store.create_policy(
            agent_id=agent_id,
            limit_amount=Decimal("200.00"),  # Will be 45% utilized
            time_window="daily"
        )
        
        # Create ledger with spending of 90
        ledger_writer = LedgerWriter(str(ledger_path))
        ledger_writer.append_event(
            agent_id=agent_id,
            resource_type="test.resource",
            quantity=Decimal("10"),
            cost=Decimal("90.00"),
            timestamp=datetime.utcnow()
        )
        
        # Create evaluator
        ledger_query = LedgerQuery(str(ledger_path))
        time_window_calculator = TimeWindowCalculator()
        evaluator = PolicyEvaluator(
            policy_store,
            ledger_query,
            time_window_calculator=time_window_calculator
        )
        
        # Evaluate all policies
        decision = evaluator.check_budget(agent_id)
        
        assert decision.allowed is True
        assert len(decision.policy_decisions) == 2
        
        # Find policy with highest utilization
        policy1_decision = next(d for d in decision.policy_decisions if d.policy_id == policy1.policy_id)
        policy2_decision = next(d for d in decision.policy_decisions if d.policy_id == policy2.policy_id)
        
        # Policy1 should be closer to limit
        policy1_utilization = (policy1_decision.current_spending / policy1_decision.limit_amount) * 100
        policy2_utilization = (policy2_decision.current_spending / policy2_decision.limit_amount) * 100
        
        assert policy1_utilization == 90.0
        assert policy2_utilization == 45.0
        assert policy1_utilization > policy2_utilization
