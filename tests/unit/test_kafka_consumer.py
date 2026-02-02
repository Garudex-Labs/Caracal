"""
Unit tests for Kafka BaseKafkaConsumer.

Tests consumer initialization, message processing, error handling,
retry logic, and dead letter queue functionality.

Requirements: 2.4, 2.5, 15.1, 15.2, 1.5, 1.6
"""

import asyncio
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from uuid import uuid4

from caracal.kafka.consumer import (
    BaseKafkaConsumer,
    ConsumerConfig,
    KafkaMessage,
)
from caracal.exceptions import KafkaConsumerError


class TestConsumer(BaseKafkaConsumer):
    """Test consumer implementation for testing."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.processed_messages = []
        self.process_error = None
    
    async def process_message(self, message: KafkaMessage) -> None:
        """Process message - can be configured to raise errors."""
        if self.process_error:
            raise self.process_error
        self.processed_messages.append(message)


class TestBaseKafkaConsumer:
    """Test suite for BaseKafkaConsumer."""
    
    def test_consumer_initialization(self):
        """Test consumer initializes with correct configuration."""
        consumer = TestConsumer(
            brokers=["localhost:9092"],
            topics=["test.topic"],
            consumer_group="test-group",
            security_protocol="PLAINTEXT"
        )
        
        assert consumer.brokers == ["localhost:9092"]
        assert consumer.topics == ["test.topic"]
        assert consumer.consumer_group == "test-group"
        assert consumer.security_protocol == "PLAINTEXT"
        assert not consumer._initialized
        assert not consumer._running
    
    def test_consumer_config_defaults(self):
        """Test consumer config has correct defaults."""
        config = ConsumerConfig()
        
        assert config.auto_offset_reset == "earliest"
        assert config.enable_auto_commit is False  # MUST be False for exactly-once
        assert config.isolation_level == "read_committed"
        assert config.max_poll_records == 500
        assert config.session_timeout_ms == 30000
        assert config.enable_idempotence is True
    
    def test_kafka_message_deserialization(self):
        """Test KafkaMessage JSON deserialization."""
        test_data = {"key": "value", "number": 42}
        message = KafkaMessage(
            topic="test.topic",
            partition=0,
            offset=123,
            key=b"test-key",
            value=json.dumps(test_data).encode('utf-8'),
            timestamp=1234567890
        )
        
        deserialized = message.deserialize_json()
        assert deserialized == test_data
    
    @pytest.mark.asyncio
    async def test_process_with_retry_success(self):
        """Test message processing succeeds on first attempt."""
        consumer = TestConsumer(
            brokers=["localhost:9092"],
            topics=["test.topic"],
            consumer_group="test-group"
        )
        
        message = KafkaMessage(
            topic="test.topic",
            partition=0,
            offset=1,
            key=b"key",
            value=b'{"test": "data"}',
            timestamp=1234567890
        )
        
        await consumer._process_with_retry(message)
        
        assert len(consumer.processed_messages) == 1
        assert consumer.processed_messages[0] == message
        assert len(consumer._retry_counts) == 0
    
    @pytest.mark.asyncio
    async def test_process_with_retry_failure_then_success(self):
        """Test message processing retries on failure then succeeds."""
        consumer = TestConsumer(
            brokers=["localhost:9092"],
            topics=["test.topic"],
            consumer_group="test-group"
        )
        
        message = KafkaMessage(
            topic="test.topic",
            partition=0,
            offset=1,
            key=b"key",
            value=b'{"test": "data"}',
            timestamp=1234567890
        )
        
        # Fail first attempt, succeed on second
        call_count = 0
        
        async def process_with_failure(msg):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Temporary failure")
            consumer.processed_messages.append(msg)
        
        consumer.process_message = process_with_failure
        
        await consumer._process_with_retry(message)
        
        assert call_count == 2
        assert len(consumer.processed_messages) == 1
        assert len(consumer._retry_counts) == 0
    
    @pytest.mark.asyncio
    async def test_process_with_retry_max_retries_exceeded(self):
        """Test message sent to DLQ after max retries exceeded."""
        consumer = TestConsumer(
            brokers=["localhost:9092"],
            topics=["test.topic"],
            consumer_group="test-group"
        )
        
        message = KafkaMessage(
            topic="test.topic",
            partition=0,
            offset=1,
            key=b"key",
            value=b'{"test": "data"}',
            timestamp=1234567890
        )
        
        # Always fail
        consumer.process_error = ValueError("Persistent failure")
        
        # Mock send_to_dlq
        consumer.send_to_dlq = AsyncMock()
        
        await consumer._process_with_retry(message)
        
        # Should have tried MAX_RETRIES times
        assert len(consumer.processed_messages) == 0
        
        # Should have sent to DLQ
        consumer.send_to_dlq.assert_called_once()
        call_args = consumer.send_to_dlq.call_args
        assert call_args[0][0] == message
        assert isinstance(call_args[0][1], ValueError)
    
    @pytest.mark.asyncio
    async def test_send_to_dlq(self):
        """Test sending failed message to DLQ."""
        consumer = TestConsumer(
            brokers=["localhost:9092"],
            topics=["test.topic"],
            consumer_group="test-group"
        )
        
        message = KafkaMessage(
            topic="test.topic",
            partition=0,
            offset=1,
            key=b"key",
            value=b'{"test": "data"}',
            timestamp=1234567890
        )
        
        error = ValueError("Test error")
        
        # Mock Kafka Producer
        with patch('caracal.kafka.consumer.Producer') as mock_producer_class:
            mock_producer = MagicMock()
            mock_producer_class.return_value = mock_producer
            
            # Set retry count
            consumer._retry_counts["test.topic:0:1"] = 3
            
            await consumer.send_to_dlq(message, error)
            
            # Verify producer was created and used
            mock_producer_class.assert_called_once()
            mock_producer.produce.assert_called_once()
            
            # Verify DLQ message structure
            produce_call = mock_producer.produce.call_args
            assert produce_call[1]['topic'] == consumer.DLQ_TOPIC
            assert produce_call[1]['key'] == message.key
            
            # Parse DLQ value
            dlq_value = json.loads(produce_call[1]['value'].decode('utf-8'))
            assert dlq_value['original_topic'] == "test.topic"
            assert dlq_value['original_partition'] == 0
            assert dlq_value['original_offset'] == 1
            assert dlq_value['error_type'] == "ValueError"
            assert dlq_value['error_message'] == "Test error"
            assert dlq_value['retry_count'] == 3
            assert dlq_value['consumer_group'] == "test-group"
            
            # Verify flush was called
            mock_producer.flush.assert_called_once()
    
    def test_on_partitions_assigned(self):
        """Test partition assignment callback."""
        consumer = TestConsumer(
            brokers=["localhost:9092"],
            topics=["test.topic"],
            consumer_group="test-group"
        )
        
        # Mock consumer and partitions
        mock_consumer = MagicMock()
        from confluent_kafka import TopicPartition
        
        partitions = [
            TopicPartition("test.topic", 0, offset=100),
            TopicPartition("test.topic", 1, offset=200),
        ]
        
        # Mock committed offsets
        mock_consumer.committed.return_value = [
            TopicPartition("test.topic", 0, offset=100),
        ]
        
        # Call callback
        consumer._on_partitions_assigned(mock_consumer, partitions)
        
        # Verify committed was called
        mock_consumer.committed.assert_called()
    
    def test_on_partitions_revoked(self):
        """Test partition revocation callback."""
        consumer = TestConsumer(
            brokers=["localhost:9092"],
            topics=["test.topic"],
            consumer_group="test-group"
        )
        
        # Mock consumer and partitions
        mock_consumer = MagicMock()
        from confluent_kafka import TopicPartition
        
        partitions = [
            TopicPartition("test.topic", 0),
            TopicPartition("test.topic", 1),
        ]
        
        # Call callback
        consumer._on_partitions_revoked(mock_consumer, partitions)
        
        # Verify commit was called
        mock_consumer.commit.assert_called_once_with(asynchronous=False)
    
    @pytest.mark.asyncio
    async def test_stop_consumer(self):
        """Test consumer stops gracefully."""
        consumer = TestConsumer(
            brokers=["localhost:9092"],
            topics=["test.topic"],
            consumer_group="test-group"
        )
        
        # Mock consumer and producer
        consumer._consumer = MagicMock()
        consumer._dlq_producer = AsyncMock()
        consumer._running = True
        consumer._initialized = True
        
        await consumer.stop()
        
        # Verify commit and close were called
        consumer._consumer.commit.assert_called_once_with(asynchronous=False)
        consumer._consumer.close.assert_called_once()
        consumer._dlq_producer.close.assert_called_once()
        
        # Verify state
        assert not consumer._running
        assert not consumer._initialized
        assert consumer._consumer is None
        assert consumer._dlq_producer is None
    
    def test_abstract_process_message(self):
        """Test that BaseKafkaConsumer.process_message is abstract."""
        # Create instance without overriding process_message
        consumer = BaseKafkaConsumer(
            brokers=["localhost:9092"],
            topics=["test.topic"],
            consumer_group="test-group"
        )
        
        message = KafkaMessage(
            topic="test.topic",
            partition=0,
            offset=1,
            key=b"key",
            value=b'{"test": "data"}',
            timestamp=1234567890
        )
        
        # Should raise NotImplementedError
        with pytest.raises(NotImplementedError):
            asyncio.run(consumer.process_message(message))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
