#!/usr/bin/env python3
"""
Manual test script for LedgerQuery implementation.
"""

import tempfile
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from caracal.core.ledger import LedgerWriter, LedgerQuery


def test_ledger_query():
    """Test LedgerQuery functionality."""
    print("Testing LedgerQuery implementation...")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "ledger.jsonl"
        
        # Test 1: Initialize LedgerQuery
        print("\n1. Testing LedgerQuery initialization...")
        query = LedgerQuery(str(ledger_path))
        assert ledger_path.exists(), "Ledger file should be created"
        print("✓ LedgerQuery initialization successful")
        
        # Test 2: Query empty ledger
        print("\n2. Testing query on empty ledger...")
        events = query.get_events()
        assert events == [], "Empty ledger should return empty list"
        print("✓ Empty ledger query successful")
        
        # Test 3: Add events and query all
        print("\n3. Testing get_events without filters...")
        writer = LedgerWriter(str(ledger_path))
        writer.append_event(
            agent_id="agent-1",
            resource_type="resource-1",
            quantity=Decimal("100"),
            cost=Decimal("1.00")
        )
        writer.append_event(
            agent_id="agent-2",
            resource_type="resource-2",
            quantity=Decimal("200"),
            cost=Decimal("2.00")
        )
        
        events = query.get_events()
        assert len(events) == 2, f"Expected 2 events, got {len(events)}"
        assert events[0].agent_id == "agent-1"
        assert events[1].agent_id == "agent-2"
        print("✓ Get all events successful")
        
        # Test 4: Filter by agent_id
        print("\n4. Testing filter by agent_id...")
        writer.append_event(
            agent_id="agent-1",
            resource_type="resource-3",
            quantity=Decimal("300"),
            cost=Decimal("3.00")
        )
        
        events = query.get_events(agent_id="agent-1")
        assert len(events) == 2, f"Expected 2 events for agent-1, got {len(events)}"
        assert all(e.agent_id == "agent-1" for e in events)
        print("✓ Filter by agent_id successful")
        
        # Test 5: Filter by resource_type
        print("\n5. Testing filter by resource_type...")
        events = query.get_events(resource_type="resource-1")
        assert len(events) == 1, f"Expected 1 event for resource-1, got {len(events)}"
        assert events[0].resource_type == "resource-1"
        print("✓ Filter by resource_type successful")
        
        # Test 6: Filter by time range
        print("\n6. Testing filter by time range...")
        base_time = datetime(2024, 1, 15, 10, 0, 0)
        
        # Create new ledger with timestamped events
        ledger_path2 = Path(tmpdir) / "ledger2.jsonl"
        writer2 = LedgerWriter(str(ledger_path2))
        
        writer2.append_event(
            agent_id="agent-1",
            resource_type="resource-1",
            quantity=Decimal("100"),
            cost=Decimal("1.00"),
            timestamp=base_time
        )
        writer2.append_event(
            agent_id="agent-1",
            resource_type="resource-2",
            quantity=Decimal("200"),
            cost=Decimal("2.00"),
            timestamp=base_time + timedelta(hours=1)
        )
        writer2.append_event(
            agent_id="agent-1",
            resource_type="resource-3",
            quantity=Decimal("300"),
            cost=Decimal("3.00"),
            timestamp=base_time + timedelta(hours=2)
        )
        
        query2 = LedgerQuery(str(ledger_path2))
        events = query2.get_events(
            start_time=base_time + timedelta(minutes=30),
            end_time=base_time + timedelta(hours=1, minutes=30)
        )
        assert len(events) == 1, f"Expected 1 event in time range, got {len(events)}"
        assert events[0].resource_type == "resource-2"
        print("✓ Filter by time range successful")
        
        # Test 7: Sum spending
        print("\n7. Testing sum_spending...")
        total = query2.sum_spending(
            agent_id="agent-1",
            start_time=base_time - timedelta(hours=1),
            end_time=base_time + timedelta(hours=3)
        )
        assert total == Decimal("6.00"), f"Expected total 6.00, got {total}"
        print("✓ Sum spending successful")
        
        # Test 8: Aggregate by agent
        print("\n8. Testing aggregate_by_agent...")
        ledger_path3 = Path(tmpdir) / "ledger3.jsonl"
        writer3 = LedgerWriter(str(ledger_path3))
        
        writer3.append_event(
            agent_id="agent-1",
            resource_type="resource-1",
            quantity=Decimal("100"),
            cost=Decimal("1.00"),
            timestamp=base_time
        )
        writer3.append_event(
            agent_id="agent-2",
            resource_type="resource-2",
            quantity=Decimal("200"),
            cost=Decimal("2.00"),
            timestamp=base_time
        )
        writer3.append_event(
            agent_id="agent-1",
            resource_type="resource-3",
            quantity=Decimal("300"),
            cost=Decimal("3.00"),
            timestamp=base_time
        )
        
        query3 = LedgerQuery(str(ledger_path3))
        aggregation = query3.aggregate_by_agent(
            start_time=base_time - timedelta(hours=1),
            end_time=base_time + timedelta(hours=1)
        )
        
        assert len(aggregation) == 2, f"Expected 2 agents, got {len(aggregation)}"
        assert aggregation["agent-1"] == Decimal("4.00"), f"Expected 4.00 for agent-1, got {aggregation['agent-1']}"
        assert aggregation["agent-2"] == Decimal("2.00"), f"Expected 2.00 for agent-2, got {aggregation['agent-2']}"
        print("✓ Aggregate by agent successful")
        
        # Test 9: Combined filters
        print("\n9. Testing combined filters...")
        events = query2.get_events(
            agent_id="agent-1",
            resource_type="resource-2",
            start_time=base_time,
            end_time=base_time + timedelta(hours=2)
        )
        assert len(events) == 1, f"Expected 1 event with combined filters, got {len(events)}"
        assert events[0].agent_id == "agent-1"
        assert events[0].resource_type == "resource-2"
        print("✓ Combined filters successful")
        
    print("\n" + "="*50)
    print("All tests passed! ✓")
    print("="*50)


if __name__ == "__main__":
    test_ledger_query()
