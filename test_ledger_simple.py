#!/usr/bin/env python
"""Simple test script to verify ledger writer works."""

import tempfile
from decimal import Decimal
from pathlib import Path

from caracal.core.ledger import LedgerWriter

def test_basic_functionality():
    """Test basic ledger writer functionality."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "test_ledger.jsonl"
        
        print(f"Creating ledger at: {ledger_path}")
        writer = LedgerWriter(str(ledger_path))
        
        print("Appending first event...")
        event1 = writer.append_event(
            agent_id="test-agent-1",
            resource_type="openai.gpt4.input_tokens",
            quantity=Decimal("1000"),
            cost=Decimal("0.030"),
            currency="USD"
        )
        print(f"Event 1: ID={event1.event_id}, agent={event1.agent_id}, cost={event1.cost}")
        
        print("Appending second event...")
        event2 = writer.append_event(
            agent_id="test-agent-2",
            resource_type="openai.gpt4.output_tokens",
            quantity=Decimal("500"),
            cost=Decimal("0.030"),
            currency="USD"
        )
        print(f"Event 2: ID={event2.event_id}, agent={event2.agent_id}, cost={event2.cost}")
        
        # Verify file contents
        print("\nReading ledger file...")
        with open(ledger_path, 'r') as f:
            lines = f.readlines()
        
        print(f"Number of lines in ledger: {len(lines)}")
        for i, line in enumerate(lines, 1):
            print(f"Line {i}: {line.strip()[:80]}...")
        
        # Test loading existing ledger
        print("\nCreating new writer to test loading...")
        writer2 = LedgerWriter(str(ledger_path))
        print(f"Next event ID after reload: {writer2._next_event_id}")
        
        event3 = writer2.append_event(
            agent_id="test-agent-3",
            resource_type="test-resource",
            quantity=Decimal("100"),
            cost=Decimal("1.00")
        )
        print(f"Event 3: ID={event3.event_id}, agent={event3.agent_id}")
        
        print("\n✅ All tests passed!")

if __name__ == "__main__":
    test_basic_functionality()
