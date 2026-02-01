"""
Unit tests for spending aggregation functionality.

Tests the hierarchical spending aggregation features added in v0.2.
"""

from decimal import Decimal
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from caracal.core.ledger import LedgerWriter, LedgerQuery
from caracal.core.identity import AgentRegistry


class TestSpendingAggregation:
    """Tests for spending aggregation with parent-child relationships."""
    
    def test_sum_spending_with_children_no_registry(self, temp_dir):
        """Test sum_spending_with_children without agent registry returns only parent spending."""
        ledger_path = temp_dir / "ledger.jsonl"
        writer = LedgerWriter(str(ledger_path))
        
        base_time = datetime(2024, 1, 15, 10, 0, 0)
        
        # Add events for parent agent
        writer.append_event(
            agent_id="parent-agent",
            resource_type="resource-1",
            quantity=Decimal("100"),
            cost=Decimal("10.00"),
            timestamp=base_time
        )
        
        # Query spending
        query = LedgerQuery(str(ledger_path))
        spending = query.sum_spending_with_children(
            agent_id="parent-agent",
            start_time=base_time - timedelta(hours=1),
            end_time=base_time + timedelta(hours=1),
            agent_registry=None
        )
        
        # Should only return parent's spending
        assert len(spending) == 1
        assert spending["parent-agent"] == Decimal("10.00")
    
    def test_sum_spending_with_children_with_registry(self, temp_dir):
        """Test sum_spending_with_children includes child agent spending."""
        ledger_path = temp_dir / "ledger.jsonl"
        registry_path = temp_dir / "agents.json"
        
        # Create agent registry with parent-child relationships
        registry = AgentRegistry(str(registry_path))
        parent = registry.register_agent("parent-agent", "owner@example.com", generate_keys=False)
        child1 = registry.register_agent("child-agent-1", "owner@example.com", 
                                        parent_agent_id=parent.agent_id, generate_keys=False)
        child2 = registry.register_agent("child-agent-2", "owner@example.com", 
                                        parent_agent_id=parent.agent_id, generate_keys=False)
        
        # Add spending events
        writer = LedgerWriter(str(ledger_path))
        base_time = datetime(2024, 1, 15, 10, 0, 0)
        
        writer.append_event(
            agent_id=parent.agent_id,
            resource_type="resource-1",
            quantity=Decimal("100"),
            cost=Decimal("10.00"),
            timestamp=base_time
        )
        writer.append_event(
            agent_id=child1.agent_id,
            resource_type="resource-2",
            quantity=Decimal("200"),
            cost=Decimal("5.00"),
            timestamp=base_time
        )
        writer.append_event(
            agent_id=child2.agent_id,
            resource_type="resource-3",
            quantity=Decimal("300"),
            cost=Decimal("3.00"),
            timestamp=base_time
        )
        
        # Query spending with children
        query = LedgerQuery(str(ledger_path))
        spending = query.sum_spending_with_children(
            agent_id=parent.agent_id,
            start_time=base_time - timedelta(hours=1),
            end_time=base_time + timedelta(hours=1),
            agent_registry=registry
        )
        
        # Should include parent and both children
        assert len(spending) == 3
        assert spending[parent.agent_id] == Decimal("10.00")
        assert spending[child1.agent_id] == Decimal("5.00")
        assert spending[child2.agent_id] == Decimal("3.00")
        
        # Total should be sum of all
        total = sum(spending.values())
        assert total == Decimal("18.00")
    
    def test_sum_spending_with_children_multi_level(self, temp_dir):
        """Test sum_spending_with_children with grandchildren."""
        ledger_path = temp_dir / "ledger.jsonl"
        registry_path = temp_dir / "agents.json"
        
        # Create multi-level hierarchy
        registry = AgentRegistry(str(registry_path))
        parent = registry.register_agent("parent", "owner@example.com", generate_keys=False)
        child = registry.register_agent("child", "owner@example.com", 
                                       parent_agent_id=parent.agent_id, generate_keys=False)
        grandchild = registry.register_agent("grandchild", "owner@example.com", 
                                            parent_agent_id=child.agent_id, generate_keys=False)
        
        # Add spending events
        writer = LedgerWriter(str(ledger_path))
        base_time = datetime(2024, 1, 15, 10, 0, 0)
        
        writer.append_event(
            agent_id=parent.agent_id,
            resource_type="resource-1",
            quantity=Decimal("100"),
            cost=Decimal("10.00"),
            timestamp=base_time
        )
        writer.append_event(
            agent_id=child.agent_id,
            resource_type="resource-2",
            quantity=Decimal("200"),
            cost=Decimal("5.00"),
            timestamp=base_time
        )
        writer.append_event(
            agent_id=grandchild.agent_id,
            resource_type="resource-3",
            quantity=Decimal("300"),
            cost=Decimal("2.00"),
            timestamp=base_time
        )
        
        # Query spending from parent (should include all descendants)
        query = LedgerQuery(str(ledger_path))
        spending = query.sum_spending_with_children(
            agent_id=parent.agent_id,
            start_time=base_time - timedelta(hours=1),
            end_time=base_time + timedelta(hours=1),
            agent_registry=registry
        )
        
        # Should include parent, child, and grandchild
        assert len(spending) == 3
        assert spending[parent.agent_id] == Decimal("10.00")
        assert spending[child.agent_id] == Decimal("5.00")
        assert spending[grandchild.agent_id] == Decimal("2.00")
        
        total = sum(spending.values())
        assert total == Decimal("17.00")
    
    def test_get_spending_breakdown_no_children(self, temp_dir):
        """Test get_spending_breakdown for agent with no children."""
        ledger_path = temp_dir / "ledger.jsonl"
        registry_path = temp_dir / "agents.json"
        
        registry = AgentRegistry(str(registry_path))
        agent = registry.register_agent("solo-agent", "owner@example.com", generate_keys=False)
        
        # Add spending
        writer = LedgerWriter(str(ledger_path))
        base_time = datetime(2024, 1, 15, 10, 0, 0)
        
        writer.append_event(
            agent_id=agent.agent_id,
            resource_type="resource-1",
            quantity=Decimal("100"),
            cost=Decimal("10.00"),
            timestamp=base_time
        )
        
        # Get breakdown
        query = LedgerQuery(str(ledger_path))
        breakdown = query.get_spending_breakdown(
            agent_id=agent.agent_id,
            start_time=base_time - timedelta(hours=1),
            end_time=base_time + timedelta(hours=1),
            agent_registry=registry
        )
        
        assert breakdown["agent_id"] == agent.agent_id
        assert breakdown["agent_name"] == "solo-agent"
        assert breakdown["spending"] == Decimal("10.00")
        assert breakdown["children"] == []
        assert breakdown["total_with_children"] == Decimal("10.00")
    
    def test_get_spending_breakdown_with_children(self, temp_dir):
        """Test get_spending_breakdown with hierarchical structure."""
        ledger_path = temp_dir / "ledger.jsonl"
        registry_path = temp_dir / "agents.json"
        
        # Create hierarchy
        registry = AgentRegistry(str(registry_path))
        parent = registry.register_agent("parent", "owner@example.com", generate_keys=False)
        child1 = registry.register_agent("child1", "owner@example.com", 
                                        parent_agent_id=parent.agent_id, generate_keys=False)
        child2 = registry.register_agent("child2", "owner@example.com", 
                                        parent_agent_id=parent.agent_id, generate_keys=False)
        grandchild = registry.register_agent("grandchild", "owner@example.com", 
                                            parent_agent_id=child1.agent_id, generate_keys=False)
        
        # Add spending
        writer = LedgerWriter(str(ledger_path))
        base_time = datetime(2024, 1, 15, 10, 0, 0)
        
        writer.append_event(
            agent_id=parent.agent_id,
            resource_type="resource-1",
            quantity=Decimal("100"),
            cost=Decimal("10.00"),
            timestamp=base_time
        )
        writer.append_event(
            agent_id=child1.agent_id,
            resource_type="resource-2",
            quantity=Decimal("200"),
            cost=Decimal("5.00"),
            timestamp=base_time
        )
        writer.append_event(
            agent_id=child2.agent_id,
            resource_type="resource-3",
            quantity=Decimal("300"),
            cost=Decimal("3.00"),
            timestamp=base_time
        )
        writer.append_event(
            agent_id=grandchild.agent_id,
            resource_type="resource-4",
            quantity=Decimal("400"),
            cost=Decimal("2.00"),
            timestamp=base_time
        )
        
        # Get breakdown
        query = LedgerQuery(str(ledger_path))
        breakdown = query.get_spending_breakdown(
            agent_id=parent.agent_id,
            start_time=base_time - timedelta(hours=1),
            end_time=base_time + timedelta(hours=1),
            agent_registry=registry
        )
        
        # Verify parent level
        assert breakdown["agent_id"] == parent.agent_id
        assert breakdown["agent_name"] == "parent"
        assert breakdown["spending"] == Decimal("10.00")
        assert len(breakdown["children"]) == 2
        assert breakdown["total_with_children"] == Decimal("20.00")  # 10 + 5 + 3 + 2
        
        # Verify child1 (has grandchild)
        child1_breakdown = next(c for c in breakdown["children"] if c["agent_id"] == child1.agent_id)
        assert child1_breakdown["spending"] == Decimal("5.00")
        assert len(child1_breakdown["children"]) == 1
        assert child1_breakdown["total_with_children"] == Decimal("7.00")  # 5 + 2
        
        # Verify grandchild
        grandchild_breakdown = child1_breakdown["children"][0]
        assert grandchild_breakdown["agent_id"] == grandchild.agent_id
        assert grandchild_breakdown["spending"] == Decimal("2.00")
        assert grandchild_breakdown["children"] == []
        assert grandchild_breakdown["total_with_children"] == Decimal("2.00")
        
        # Verify child2 (no children)
        child2_breakdown = next(c for c in breakdown["children"] if c["agent_id"] == child2.agent_id)
        assert child2_breakdown["spending"] == Decimal("3.00")
        assert child2_breakdown["children"] == []
        assert child2_breakdown["total_with_children"] == Decimal("3.00")
    
    def test_get_spending_breakdown_no_registry(self, temp_dir):
        """Test get_spending_breakdown without registry returns basic info."""
        ledger_path = temp_dir / "ledger.jsonl"
        
        writer = LedgerWriter(str(ledger_path))
        base_time = datetime(2024, 1, 15, 10, 0, 0)
        
        writer.append_event(
            agent_id="test-agent",
            resource_type="resource-1",
            quantity=Decimal("100"),
            cost=Decimal("10.00"),
            timestamp=base_time
        )
        
        # Get breakdown without registry
        query = LedgerQuery(str(ledger_path))
        breakdown = query.get_spending_breakdown(
            agent_id="test-agent",
            start_time=base_time - timedelta(hours=1),
            end_time=base_time + timedelta(hours=1),
            agent_registry=None
        )
        
        assert breakdown["agent_id"] == "test-agent"
        assert "agent_name" not in breakdown  # No registry, no name
        assert breakdown["spending"] == Decimal("10.00")
        assert breakdown["children"] == []
        assert breakdown["total_with_children"] == Decimal("10.00")
