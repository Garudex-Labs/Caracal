#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from caracal.core.ledger import LedgerQuery, LedgerWriter
from decimal import Decimal
from datetime import datetime
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmpdir:
    ledger_path = Path(tmpdir) / "test.jsonl"
    
    # Write some events
    writer = LedgerWriter(str(ledger_path))
    writer.append_event("agent-1", "resource-1", Decimal("100"), Decimal("1.00"))
    writer.append_event("agent-2", "resource-2", Decimal("200"), Decimal("2.00"))
    
    # Query events
    query = LedgerQuery(str(ledger_path))
    events = query.get_events()
    
    print(f"Found {len(events)} events")
    print(f"Event 1: agent={events[0].agent_id}, cost={events[0].cost}")
    print(f"Event 2: agent={events[1].agent_id}, cost={events[1].cost}")
    
    # Test sum_spending
    total = query.sum_spending("agent-1", datetime(2020, 1, 1), datetime(2030, 1, 1))
    print(f"Total spending for agent-1: {total}")
    
    # Test aggregate
    agg = query.aggregate_by_agent(datetime(2020, 1, 1), datetime(2030, 1, 1))
    print(f"Aggregation: {agg}")
    
    print("\nAll tests passed!")
