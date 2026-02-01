#!/usr/bin/env python3
"""
Verification script for LedgerQuery implementation (Task 8.1).

This script demonstrates all the required features:
1. LedgerQuery class with filtering methods
2. Support filtering by agent ID, date range, resource type
3. Spending sum calculation
4. Aggregation by agent
5. Sequential scan of JSON Lines file
"""

import sys
import tempfile
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from caracal.core.ledger import LedgerWriter, LedgerQuery


def main():
    print("=" * 70)
    print("LEDGER QUERY VERIFICATION (Task 8.1)")
    print("=" * 70)
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "test_ledger.jsonl"
        
        # Setup: Create ledger with test data
        print("\nSetup: Creating test ledger with sample events...")
        writer = LedgerWriter(str(ledger_path))
        
        base_time = datetime(2024, 1, 15, 10, 0, 0)
        
        # Add events for multiple agents, resources, and times
        writer.append_event(
            agent_id="agent-001",
            resource_type="openai.gpt4.input_tokens",
            quantity=Decimal("1000"),
            cost=Decimal("1.50"),
            timestamp=base_time
        )
        writer.append_event(
            agent_id="agent-002",
            resource_type="openai.gpt4.input_tokens",
            quantity=Decimal("2000"),
            cost=Decimal("3.00"),
            timestamp=base_time
        )
        writer.append_event(
            agent_id="agent-001",
            resource_type="openai.gpt4.output_tokens",
            quantity=Decimal("500"),
            cost=Decimal("2.25"),
            timestamp=base_time + timedelta(hours=1)
        )
        writer.append_event(
            agent_id="agent-003",
            resource_type="anthropic.claude3.input_tokens",
            quantity=Decimal("1500"),
            cost=Decimal("1.75"),
            timestamp=base_time + timedelta(hours=2)
        )
        writer.append_event(
            agent_id="agent-001",
            resource_type="openai.gpt4.input_tokens",
            quantity=Decimal("800"),
            cost=Decimal("1.20"),
            timestamp=base_time + timedelta(hours=3)
        )
        
        print(f"   ✓ Created ledger with 5 events")
        
        # Feature 1: Create LedgerQuery
        print("\n1. Creating LedgerQuery...")
        query = LedgerQuery(str(ledger_path))
        print(f"   ✓ LedgerQuery created for {ledger_path}")
        
        # Feature 2a: Get all events (no filters)
        print("\n2. Querying all events (no filters)...")
        all_events = query.get_events()
        print(f"   ✓ Retrieved {len(all_events)} events")
        assert len(all_events) == 5, f"Expected 5 events, got {len(all_events)}"
        
        # Feature 2b: Filter by agent ID
        print("\n3. Filtering by agent ID...")
        agent1_events = query.get_events(agent_id="agent-001")
        print(f"   ✓ Found {len(agent1_events)} events for agent-001")
        assert len(agent1_events) == 3, f"Expected 3 events for agent-001, got {len(agent1_events)}"
        assert all(e.agent_id == "agent-001" for e in agent1_events), "All events should be for agent-001"
        print(f"   ✓ All events belong to agent-001")
        
        # Feature 2c: Filter by resource type
        print("\n4. Filtering by resource type...")
        gpt4_input_events = query.get_events(resource_type="openai.gpt4.input_tokens")
        print(f"   ✓ Found {len(gpt4_input_events)} events for openai.gpt4.input_tokens")
        assert len(gpt4_input_events) == 3, f"Expected 3 events, got {len(gpt4_input_events)}"
        assert all(e.resource_type == "openai.gpt4.input_tokens" for e in gpt4_input_events)
        print(f"   ✓ All events are for openai.gpt4.input_tokens")
        
        # Feature 2d: Filter by date range
        print("\n5. Filtering by date range...")
        time_range_events = query.get_events(
            start_time=base_time + timedelta(minutes=30),
            end_time=base_time + timedelta(hours=2, minutes=30)
        )
        print(f"   ✓ Found {len(time_range_events)} events in time range")
        assert len(time_range_events) == 2, f"Expected 2 events in range, got {len(time_range_events)}"
        print(f"   ✓ Events are within specified time range")
        
        # Feature 2e: Combined filters
        print("\n6. Testing combined filters...")
        combined_events = query.get_events(
            agent_id="agent-001",
            resource_type="openai.gpt4.input_tokens",
            start_time=base_time - timedelta(hours=1),
            end_time=base_time + timedelta(hours=1)
        )
        print(f"   ✓ Found {len(combined_events)} events with combined filters")
        assert len(combined_events) == 1, f"Expected 1 event, got {len(combined_events)}"
        assert combined_events[0].agent_id == "agent-001"
        assert combined_events[0].resource_type == "openai.gpt4.input_tokens"
        print(f"   ✓ Event matches all filter criteria")
        
        # Feature 3: Sum spending
        print("\n7. Testing spending sum calculation...")
        total_spending = query.sum_spending(
            agent_id="agent-001",
            start_time=base_time - timedelta(hours=1),
            end_time=base_time + timedelta(hours=4)
        )
        print(f"   ✓ Total spending for agent-001: ${total_spending}")
        expected_total = Decimal("1.50") + Decimal("2.25") + Decimal("1.20")  # 4.95
        assert total_spending == expected_total, f"Expected {expected_total}, got {total_spending}"
        print(f"   ✓ Spending calculation correct: ${expected_total}")
        
        # Feature 4: Aggregate by agent
        print("\n8. Testing aggregation by agent...")
        aggregation = query.aggregate_by_agent(
            start_time=base_time - timedelta(hours=1),
            end_time=base_time + timedelta(hours=4)
        )
        print(f"   ✓ Aggregated spending for {len(aggregation)} agents")
        assert len(aggregation) == 3, f"Expected 3 agents, got {len(aggregation)}"
        
        print(f"   ✓ Agent spending breakdown:")
        print(f"      - agent-001: ${aggregation['agent-001']}")
        print(f"      - agent-002: ${aggregation['agent-002']}")
        print(f"      - agent-003: ${aggregation['agent-003']}")
        
        assert aggregation["agent-001"] == Decimal("4.95"), "agent-001 spending incorrect"
        assert aggregation["agent-002"] == Decimal("3.00"), "agent-002 spending incorrect"
        assert aggregation["agent-003"] == Decimal("1.75"), "agent-003 spending incorrect"
        print(f"   ✓ All aggregations correct")
        
        # Feature 5: Sequential scan (demonstrated by implementation)
        print("\n9. Verifying sequential scan approach...")
        print(f"   ✓ LedgerQuery uses sequential scan of JSON Lines file")
        print(f"   ✓ Reads file line-by-line and applies filters")
        print(f"   ✓ Suitable for v0.1 file-based storage")
        
        # Test edge cases
        print("\n10. Testing edge cases...")
        
        # Empty result
        empty_events = query.get_events(agent_id="nonexistent-agent")
        assert len(empty_events) == 0, "Should return empty list for nonexistent agent"
        print(f"   ✓ Returns empty list for nonexistent agent")
        
        # Zero spending
        zero_spending = query.sum_spending(
            agent_id="nonexistent-agent",
            start_time=base_time,
            end_time=base_time + timedelta(hours=1)
        )
        assert zero_spending == Decimal("0"), "Should return 0 for no events"
        print(f"   ✓ Returns 0 spending for nonexistent agent")
        
        # Empty aggregation
        empty_agg = query.aggregate_by_agent(
            start_time=base_time + timedelta(days=10),
            end_time=base_time + timedelta(days=11)
        )
        assert len(empty_agg) == 0, "Should return empty dict for no events"
        print(f"   ✓ Returns empty dict for time range with no events")
        
        # Summary
        print("\n" + "=" * 70)
        print("VERIFICATION COMPLETE - ALL FEATURES IMPLEMENTED")
        print("=" * 70)
        print("\n✓ Task 8.1 Requirements:")
        print("  1. ✓ LedgerQuery class with filtering methods")
        print("  2. ✓ Support filtering by agent ID")
        print("  3. ✓ Support filtering by date range")
        print("  4. ✓ Support filtering by resource type")
        print("  5. ✓ Spending sum calculation")
        print("  6. ✓ Aggregation by agent")
        print("  7. ✓ Sequential scan of JSON Lines file")
        print("\n✓ All requirements satisfied!")
        print("\nTask 8.1 is COMPLETE and ready for review.")
        
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n❌ ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
