#!/usr/bin/env python
"""
Manual test script for multi-policy support.

This script demonstrates the multi-policy functionality by:
1. Creating an agent with two policies
2. Adding spending to the ledger
3. Checking budget with multiple policies
"""

import tempfile
from decimal import Decimal
from datetime import datetime
from pathlib import Path

from caracal.core.policy import PolicyStore, PolicyEvaluator
from caracal.core.ledger import LedgerWriter, LedgerQuery
from caracal.core.identity import AgentRegistry
from caracal.core.time_windows import TimeWindowCalculator


def main():
    """Run manual test of multi-policy support."""
    print("=" * 70)
    print("Multi-Policy Support Manual Test")
    print("=" * 70)
    print()
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        policy_path = temp_path / "policies.json"
        ledger_path = temp_path / "ledger.jsonl"
        registry_path = temp_path / "agents.json"
        
        # Step 1: Create agent
        print("Step 1: Creating agent...")
        agent_registry = AgentRegistry(str(registry_path))
        agent_id = "550e8400-e29b-41d4-a716-446655440000"
        agent = agent_registry.create_agent(
            agent_id=agent_id,
            name="Test Agent",
            agent_type="test"
        )
        print(f"  ✓ Created agent: {agent.name} ({agent.agent_id})")
        print()
        
        # Step 2: Create multiple policies
        print("Step 2: Creating multiple policies...")
        policy_store = PolicyStore(str(policy_path), agent_registry=agent_registry)
        
        policy1 = policy_store.create_policy(
            agent_id=agent_id,
            limit_amount=Decimal("100.00"),
            time_window="daily",
            currency="USD"
        )
        print(f"  ✓ Created Policy 1: {policy1.policy_id}")
        print(f"    - Limit: {policy1.limit_amount} {policy1.currency}")
        print(f"    - Window: {policy1.time_window}")
        
        policy2 = policy_store.create_policy(
            agent_id=agent_id,
            limit_amount=Decimal("150.00"),
            time_window="daily",
            currency="USD"
        )
        print(f"  ✓ Created Policy 2: {policy2.policy_id}")
        print(f"    - Limit: {policy2.limit_amount} {policy2.currency}")
        print(f"    - Window: {policy2.time_window}")
        print()
        
        # Step 3: Add spending to ledger
        print("Step 3: Adding spending to ledger...")
        ledger_writer = LedgerWriter(str(ledger_path))
        ledger_writer.append_event(
            agent_id=agent_id,
            resource_type="test.resource",
            quantity=Decimal("10"),
            cost=Decimal("80.00"),
            timestamp=datetime.utcnow()
        )
        print(f"  ✓ Added spending: $80.00")
        print()
        
        # Step 4: Check budget with multiple policies
        print("Step 4: Checking budget with multiple policies...")
        ledger_query = LedgerQuery(str(ledger_path))
        time_window_calculator = TimeWindowCalculator()
        evaluator = PolicyEvaluator(
            policy_store,
            ledger_query,
            time_window_calculator=time_window_calculator
        )
        
        # Check without estimated cost
        print("  Checking budget (no estimated cost)...")
        decision1 = evaluator.check_budget(agent_id)
        print(f"    - Allowed: {decision1.allowed}")
        print(f"    - Reason: {decision1.reason}")
        print(f"    - Remaining: ${decision1.remaining_budget}")
        print(f"    - Policies evaluated: {len(decision1.policy_decisions)}")
        
        for i, pd in enumerate(decision1.policy_decisions, 1):
            print(f"      Policy {i}:")
            print(f"        - ID: {pd.policy_id}")
            print(f"        - Allowed: {pd.allowed}")
            print(f"        - Limit: ${pd.limit_amount}")
            print(f"        - Spent: ${pd.current_spending}")
            print(f"        - Available: ${pd.available_budget}")
        print()
        
        # Check with estimated cost that exceeds first policy
        print("  Checking budget with estimated cost of $30...")
        decision2 = evaluator.check_budget(agent_id, estimated_cost=Decimal("30.00"))
        print(f"    - Allowed: {decision2.allowed}")
        print(f"    - Reason: {decision2.reason}")
        if decision2.failed_policy_id:
            print(f"    - Failed Policy: {decision2.failed_policy_id}")
        print()
        
        # Check with estimated cost that fits both policies
        print("  Checking budget with estimated cost of $15...")
        decision3 = evaluator.check_budget(agent_id, estimated_cost=Decimal("15.00"))
        print(f"    - Allowed: {decision3.allowed}")
        print(f"    - Reason: {decision3.reason}")
        print(f"    - Remaining: ${decision3.remaining_budget}")
        print()
        
        print("=" * 70)
        print("Test completed successfully!")
        print("=" * 70)


if __name__ == "__main__":
    main()
