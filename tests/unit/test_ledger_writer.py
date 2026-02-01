"""
Unit tests for LedgerWriter.

Tests the core functionality of appending events to the immutable ledger.
"""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from caracal.core.ledger import LedgerEvent, LedgerWriter
from caracal.exceptions import InvalidLedgerEventError, LedgerWriteError


class TestLedgerEvent:
    """Tests for LedgerEvent dataclass."""
    
    def test_ledger_event_creation(self):
        """Test creating a ledger event."""
        event = LedgerEvent(
            event_id=1,
            agent_id="test-agent-123",
            timestamp="2024-01-15T10:30:00Z",
            resource_type="openai.gpt4.input_tokens",
            quantity="1000",
            cost="0.030",
            currency="USD",
            metadata={"model": "gpt-4"}
        )
        
        assert event.event_id == 1
        assert event.agent_id == "test-agent-123"
        assert event.resource_type == "openai.gpt4.input_tokens"
        assert event.quantity == "1000"
        assert event.cost == "0.030"
        assert event.currency == "USD"
        assert event.metadata == {"model": "gpt-4"}
    
    def test_ledger_event_to_dict(self):
        """Test converting ledger event to dictionary."""
        event = LedgerEvent(
            event_id=1,
            agent_id="test-agent-123",
            timestamp="2024-01-15T10:30:00Z",
            resource_type="openai.gpt4.input_tokens",
            quantity="1000",
            cost="0.030",
            currency="USD",
            metadata=None
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["event_id"] == 1
        assert event_dict["agent_id"] == "test-agent-123"
        assert "metadata" not in event_dict  # None metadata should be removed
    
    def test_ledger_event_to_json_line(self):
        """Test converting ledger event to JSON line format."""
        event = LedgerEvent(
            event_id=1,
            agent_id="test-agent-123",
            timestamp="2024-01-15T10:30:00Z",
            resource_type="openai.gpt4.input_tokens",
            quantity="1000",
            cost="0.030",
            currency="USD",
            metadata=None
        )
        
        json_line = event.to_json_line()
        
        # Should be valid JSON
        parsed = json.loads(json_line)
        assert parsed["event_id"] == 1
        assert parsed["agent_id"] == "test-agent-123"
        
        # Should not contain newlines (single line)
        assert '\n' not in json_line


class TestLedgerWriter:
    """Tests for LedgerWriter."""
    
    def test_ledger_writer_initialization(self, temp_dir):
        """Test initializing ledger writer creates file if not exists."""
        ledger_path = temp_dir / "ledger.jsonl"
        
        writer = LedgerWriter(str(ledger_path))
        
        assert ledger_path.exists()
        assert writer._next_event_id == 1
    
    def test_append_event(self, temp_dir):
        """Test appending an event to the ledger."""
        ledger_path = temp_dir / "ledger.jsonl"
        writer = LedgerWriter(str(ledger_path))
        
        event = writer.append_event(
            agent_id="test-agent-123",
            resource_type="openai.gpt4.input_tokens",
            quantity=Decimal("1000"),
            cost=Decimal("0.030"),
            currency="USD",
            metadata={"model": "gpt-4"}
        )
        
        assert event.event_id == 1
        assert event.agent_id == "test-agent-123"
        assert event.resource_type == "openai.gpt4.input_tokens"
        assert event.quantity == "1000"
        assert event.cost == "0.030"
        
        # Verify event was written to file
        with open(ledger_path, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["event_id"] == 1
        assert parsed["agent_id"] == "test-agent-123"
    
    def test_append_multiple_events(self, temp_dir):
        """Test appending multiple events maintains monotonic IDs."""
        ledger_path = temp_dir / "ledger.jsonl"
        writer = LedgerWriter(str(ledger_path))
        
        # Append three events
        event1 = writer.append_event(
            agent_id="agent-1",
            resource_type="resource-1",
            quantity=Decimal("100"),
            cost=Decimal("1.00")
        )
        
        event2 = writer.append_event(
            agent_id="agent-2",
            resource_type="resource-2",
            quantity=Decimal("200"),
            cost=Decimal("2.00")
        )
        
        event3 = writer.append_event(
            agent_id="agent-3",
            resource_type="resource-3",
            quantity=Decimal("300"),
            cost=Decimal("3.00")
        )
        
        # Verify monotonic IDs
        assert event1.event_id == 1
        assert event2.event_id == 2
        assert event3.event_id == 3
        
        # Verify all events written to file
        with open(ledger_path, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) == 3
    
    def test_ledger_writer_loads_existing_ledger(self, temp_dir):
        """Test that ledger writer continues event IDs from existing ledger."""
        ledger_path = temp_dir / "ledger.jsonl"
        
        # Create first writer and add events
        writer1 = LedgerWriter(str(ledger_path))
        writer1.append_event(
            agent_id="agent-1",
            resource_type="resource-1",
            quantity=Decimal("100"),
            cost=Decimal("1.00")
        )
        writer1.append_event(
            agent_id="agent-2",
            resource_type="resource-2",
            quantity=Decimal("200"),
            cost=Decimal("2.00")
        )
        
        # Create second writer (simulating restart)
        writer2 = LedgerWriter(str(ledger_path))
        
        # Should continue from event ID 3
        assert writer2._next_event_id == 3
        
        event3 = writer2.append_event(
            agent_id="agent-3",
            resource_type="resource-3",
            quantity=Decimal("300"),
            cost=Decimal("3.00")
        )
        
        assert event3.event_id == 3
    
    def test_invalid_agent_id(self, temp_dir):
        """Test that empty agent_id raises error."""
        ledger_path = temp_dir / "ledger.jsonl"
        writer = LedgerWriter(str(ledger_path))
        
        with pytest.raises(InvalidLedgerEventError, match="agent_id cannot be empty"):
            writer.append_event(
                agent_id="",
                resource_type="resource-1",
                quantity=Decimal("100"),
                cost=Decimal("1.00")
            )
    
    def test_invalid_resource_type(self, temp_dir):
        """Test that empty resource_type raises error."""
        ledger_path = temp_dir / "ledger.jsonl"
        writer = LedgerWriter(str(ledger_path))
        
        with pytest.raises(InvalidLedgerEventError, match="resource_type cannot be empty"):
            writer.append_event(
                agent_id="agent-1",
                resource_type="",
                quantity=Decimal("100"),
                cost=Decimal("1.00")
            )
    
    def test_negative_quantity(self, temp_dir):
        """Test that negative quantity raises error."""
        ledger_path = temp_dir / "ledger.jsonl"
        writer = LedgerWriter(str(ledger_path))
        
        with pytest.raises(InvalidLedgerEventError, match="quantity must be non-negative"):
            writer.append_event(
                agent_id="agent-1",
                resource_type="resource-1",
                quantity=Decimal("-100"),
                cost=Decimal("1.00")
            )
    
    def test_negative_cost(self, temp_dir):
        """Test that negative cost raises error."""
        ledger_path = temp_dir / "ledger.jsonl"
        writer = LedgerWriter(str(ledger_path))
        
        with pytest.raises(InvalidLedgerEventError, match="cost must be non-negative"):
            writer.append_event(
                agent_id="agent-1",
                resource_type="resource-1",
                quantity=Decimal("100"),
                cost=Decimal("-1.00")
            )
    
    def test_backup_creation(self, temp_dir):
        """Test that backup is created on first write."""
        ledger_path = temp_dir / "ledger.jsonl"
        
        # Create ledger with some initial data
        with open(ledger_path, 'w') as f:
            f.write('{"event_id":1,"agent_id":"old-agent","timestamp":"2024-01-01T00:00:00Z","resource_type":"test","quantity":"100","cost":"1.00","currency":"USD"}\n')
        
        # Create writer (should create backup on first write)
        writer = LedgerWriter(str(ledger_path))
        
        # Append event (triggers backup)
        writer.append_event(
            agent_id="new-agent",
            resource_type="resource-1",
            quantity=Decimal("100"),
            cost=Decimal("1.00")
        )
        
        # Verify backup was created
        backup_path = Path(f"{ledger_path}.bak.1")
        assert backup_path.exists()
        
        # Verify backup contains original data
        with open(backup_path, 'r') as f:
            backup_content = f.read()
        
        assert "old-agent" in backup_content
    
    def test_json_lines_format(self, temp_dir):
        """Test that ledger uses JSON Lines format (one JSON per line)."""
        ledger_path = temp_dir / "ledger.jsonl"
        writer = LedgerWriter(str(ledger_path))
        
        # Append multiple events
        for i in range(3):
            writer.append_event(
                agent_id=f"agent-{i}",
                resource_type="resource-1",
                quantity=Decimal("100"),
                cost=Decimal("1.00")
            )
        
        # Read file and verify format
        with open(ledger_path, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) == 3
        
        # Each line should be valid JSON
        for line in lines:
            parsed = json.loads(line)
            assert "event_id" in parsed
            assert "agent_id" in parsed
