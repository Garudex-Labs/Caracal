"""
Integration tests for MCP Adapter.

Tests the full integration of MCP adapter with policy evaluation and metering.
"""

import pytest
import tempfile
import os
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from caracal.mcp.adapter import MCPAdapter, MCPContext
from caracal.mcp.cost_calculator import MCPCostCalculator
from caracal.core.policy import PolicyStore, PolicyEvaluator
from caracal.core.metering import MeteringCollector
from caracal.core.pricebook import Pricebook
from caracal.core.ledger import LedgerWriter, LedgerQuery
from caracal.core.identity import AgentRegistry
from caracal.exceptions import BudgetExceededError


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def agent_registry(temp_dir):
    """Create an agent registry."""
    agents_path = os.path.join(temp_dir, "agents.json")
    return AgentRegistry(agents_path)


@pytest.fixture
def pricebook(temp_dir):
    """Create a pricebook with test prices."""
    pricebook_path = os.path.join(temp_dir, "pricebook.csv")
    pricebook = Pricebook(pricebook_path)
    
    # Add some test prices
    pricebook.set_price("mcp.tool.default", Decimal("0.01"))
    pricebook.set_price("mcp.resource.default", Decimal("0.001"))
    pricebook.set_price("mcp.llm.gpt-4.input_tokens", Decimal("0.00003"))
    pricebook.set_price("mcp.llm.gpt-4.output_tokens", Decimal("0.00006"))
    
    return pricebook


@pytest.fixture
def ledger_writer(temp_dir):
    """Create a ledger writer."""
    ledger_path = os.path.join(temp_dir, "ledger.jsonl")
    return LedgerWriter(ledger_path)


@pytest.fixture
def ledger_query(temp_dir):
    """Create a ledger query."""
    ledger_path = os.path.join(temp_dir, "ledger.jsonl")
    return LedgerQuery(ledger_path)


@pytest.fixture
def policy_store(temp_dir, agent_registry):
    """Create a policy store."""
    policy_path = os.path.join(temp_dir, "policies.json")
    return PolicyStore(policy_path, agent_registry=agent_registry)


@pytest.fixture
def metering_collector(pricebook, ledger_writer):
    """Create a metering collector."""
    return MeteringCollector(pricebook, ledger_writer)


@pytest.fixture
def policy_evaluator(policy_store, ledger_query):
    """Create a policy evaluator."""
    return PolicyEvaluator(policy_store, ledger_query)


@pytest.fixture
def cost_calculator(pricebook):
    """Create a cost calculator."""
    return MCPCostCalculator(pricebook)


@pytest.fixture
def mcp_adapter(policy_evaluator, metering_collector, cost_calculator):
    """Create an MCP adapter."""
    return MCPAdapter(
        policy_evaluator=policy_evaluator,
        metering_collector=metering_collector,
        cost_calculator=cost_calculator
    )


@pytest.fixture
def test_agent(agent_registry, policy_store):
    """Create a test agent with a budget policy."""
    # Register agent
    agent = agent_registry.register_agent(
        name="test-mcp-agent",
        owner="test-owner"
    )
    
    # Create policy
    policy_store.create_policy(
        agent_id=agent.agent_id,
        limit_amount=Decimal("100.00"),
        time_window="daily"
    )
    
    return agent


class TestMCPIntegration:
    """Integration tests for MCP adapter."""

    @pytest.mark.asyncio
    async def test_tool_call_within_budget(
        self, mcp_adapter, test_agent, ledger_query
    ):
        """Test tool call succeeds when within budget."""
        context = MCPContext(
            agent_id=test_agent.agent_id,
            metadata={"source": "integration_test"}
        )
        
        tool_name = "test_tool"
        tool_args = {"arg1": "value1"}
        
        # Execute tool call
        result = await mcp_adapter.intercept_tool_call(tool_name, tool_args, context)
        
        # Verify success
        assert result.success is True
        assert result.result is not None
        
        # Verify metering event was written to ledger
        from datetime import datetime, timedelta
        events = ledger_query.get_events(
            agent_id=test_agent.agent_id,
            start_time=datetime.utcnow() - timedelta(minutes=1),
            end_time=datetime.utcnow() + timedelta(minutes=1)
        )
        
        assert len(events) == 1
        assert events[0].agent_id == test_agent.agent_id
        assert events[0].resource_type == f"mcp.tool.{tool_name}"

    @pytest.mark.asyncio
    async def test_tool_call_exceeds_budget(
        self, mcp_adapter, test_agent, policy_store, metering_collector, pricebook
    ):
        """Test tool call fails when budget is exceeded."""
        # Set a very high price to exceed budget
        pricebook.set_price("mcp.tool.expensive_tool", Decimal("200.00"))
        
        context = MCPContext(
            agent_id=test_agent.agent_id,
            metadata={"source": "integration_test"}
        )
        
        tool_name = "expensive_tool"
        tool_args = {"arg1": "value1"}
        
        # Execute tool call - should fail
        with pytest.raises(BudgetExceededError):
            await mcp_adapter.intercept_tool_call(tool_name, tool_args, context)

    @pytest.mark.asyncio
    async def test_resource_read_within_budget(
        self, mcp_adapter, test_agent, ledger_query
    ):
        """Test resource read succeeds when within budget."""
        context = MCPContext(
            agent_id=test_agent.agent_id,
            metadata={"source": "integration_test"}
        )
        
        resource_uri = "file:///test/resource.txt"
        
        # Execute resource read
        result = await mcp_adapter.intercept_resource_read(resource_uri, context)
        
        # Verify success
        assert result.success is True
        assert result.result is not None
        
        # Verify metering event was written to ledger
        from datetime import datetime, timedelta
        events = ledger_query.get_events(
            agent_id=test_agent.agent_id,
            start_time=datetime.utcnow() - timedelta(minutes=1),
            end_time=datetime.utcnow() + timedelta(minutes=1)
        )
        
        assert len(events) >= 1
        # Find the resource read event
        resource_events = [e for e in events if "mcp.resource." in e.resource_type]
        assert len(resource_events) >= 1

    @pytest.mark.asyncio
    async def test_multiple_tool_calls_accumulate_spending(
        self, mcp_adapter, test_agent, ledger_query, policy_evaluator
    ):
        """Test that multiple tool calls accumulate spending correctly."""
        context = MCPContext(
            agent_id=test_agent.agent_id,
            metadata={"source": "integration_test"}
        )
        
        tool_name = "test_tool"
        tool_args = {"arg1": "value1"}
        
        # Execute multiple tool calls
        for i in range(3):
            result = await mcp_adapter.intercept_tool_call(tool_name, tool_args, context)
            assert result.success is True
        
        # Verify spending accumulated
        from datetime import datetime, timedelta
        events = ledger_query.get_events(
            agent_id=test_agent.agent_id,
            start_time=datetime.utcnow() - timedelta(minutes=1),
            end_time=datetime.utcnow() + timedelta(minutes=1)
        )
        
        assert len(events) == 3
        
        # Calculate total spending
        total_spending = sum(e.cost for e in events)
        assert total_spending > Decimal("0")
        
        # Verify budget check reflects accumulated spending
        decision = policy_evaluator.check_budget(test_agent.agent_id)
        assert decision.allowed is True
        assert decision.remaining_budget < Decimal("100.00")

    @pytest.mark.asyncio
    async def test_llm_tool_cost_estimation(
        self, mcp_adapter, test_agent, pricebook
    ):
        """Test LLM tool cost estimation."""
        context = MCPContext(
            agent_id=test_agent.agent_id,
            metadata={"source": "integration_test"}
        )
        
        tool_name = "llm_completion"
        tool_args = {
            "prompt": "Test prompt for LLM",
            "max_tokens": 1000,
            "model": "gpt-4"
        }
        
        # Execute LLM tool call
        result = await mcp_adapter.intercept_tool_call(tool_name, tool_args, context)
        
        # Verify success
        assert result.success is True
        
        # Verify cost was calculated based on tokens
        estimated_cost = Decimal(result.metadata["estimated_cost"])
        actual_cost = Decimal(result.metadata["actual_cost"])
        
        assert estimated_cost > Decimal("0")
        assert actual_cost > Decimal("0")
