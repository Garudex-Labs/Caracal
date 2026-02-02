"""
Simple integration test for Kafka producer.

This test verifies that the Kafka producer can be instantiated and
basic operations work without errors.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from decimal import Decimal
from datetime import datetime

from caracal.kafka.producer import (
    KafkaEventProducer,
    KafkaConfig,
    ProducerConfig,
)


def test_kafka_producer_initialization():
    """Test that KafkaEventProducer can be initialized."""
    config = KafkaConfig(
        brokers=["localhost:9092"],
        security_protocol="PLAINTEXT",
        producer_config=ProducerConfig(
            acks="all",
            retries=3,
            enable_idempotence=True
        )
    )
    
    producer = KafkaEventProducer(config)
    
    assert producer is not None
    assert producer.config == config
    assert producer._initialized is False
    print("✓ KafkaEventProducer initialization test passed")


def test_event_dataclasses():
    """Test that event dataclasses can be created."""
    from caracal.kafka.producer import (
        MeteringEvent,
        PolicyDecisionEvent,
        AgentLifecycleEvent,
        PolicyChangeEvent,
    )
    
    # Test MeteringEvent
    metering_event = MeteringEvent(
        event_id="test-123",
        schema_version=1,
        timestamp=int(datetime.utcnow().timestamp() * 1000),
        agent_id="agent-123",
        event_type="metering",
        resource_type="api_call",
        quantity=1.0,
        cost=0.5,
        currency="USD",
        provisional_charge_id="charge-123",
        metadata={"test": "value"}
    )
    assert metering_event.event_id == "test-123"
    print("✓ MeteringEvent creation test passed")
    
    # Test PolicyDecisionEvent
    policy_event = PolicyDecisionEvent(
        event_id="test-456",
        schema_version=1,
        timestamp=int(datetime.utcnow().timestamp() * 1000),
        agent_id="agent-123",
        event_type="policy_decision",
        decision="allowed",
        reason="Within budget",
        policy_id="policy-123",
        estimated_cost=0.5,
        remaining_budget=9.5,
        metadata={"test": "value"}
    )
    assert policy_event.decision == "allowed"
    print("✓ PolicyDecisionEvent creation test passed")
    
    # Test AgentLifecycleEvent
    lifecycle_event = AgentLifecycleEvent(
        event_id="test-789",
        schema_version=1,
        timestamp=int(datetime.utcnow().timestamp() * 1000),
        agent_id="agent-123",
        event_type="agent_lifecycle",
        lifecycle_event="created",
        metadata={"test": "value"}
    )
    assert lifecycle_event.lifecycle_event == "created"
    print("✓ AgentLifecycleEvent creation test passed")
    
    # Test PolicyChangeEvent
    change_event = PolicyChangeEvent(
        event_id="test-012",
        schema_version=1,
        timestamp=int(datetime.utcnow().timestamp() * 1000),
        agent_id="agent-123",
        event_type="policy_change",
        policy_id="policy-123",
        change_type="modified",
        changed_by="admin",
        change_reason="Increased budget",
        metadata={"test": "value"}
    )
    assert change_event.change_type == "modified"
    print("✓ PolicyChangeEvent creation test passed")


def test_metadata_serialization():
    """Test metadata serialization."""
    config = KafkaConfig(
        brokers=["localhost:9092"],
        security_protocol="PLAINTEXT"
    )
    
    producer = KafkaEventProducer(config)
    
    metadata = {
        "string": "value",
        "int": 123,
        "decimal": Decimal("1.5"),
        "bool": True
    }
    
    result = producer._serialize_metadata(metadata)
    
    # All values should be strings
    assert all(isinstance(v, str) for v in result.values())
    assert result["string"] == "value"
    assert result["int"] == "123"
    assert result["decimal"] == "1.5"
    assert result["bool"] == "True"
    print("✓ Metadata serialization test passed")


if __name__ == "__main__":
    print("Running Kafka producer integration tests...")
    print()
    
    test_kafka_producer_initialization()
    test_event_dataclasses()
    test_metadata_serialization()
    
    print()
    print("All tests passed! ✓")
