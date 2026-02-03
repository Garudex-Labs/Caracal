"""
Unit tests for Event Replay Manager.

Tests event replay functionality including offset reset, progress tracking,
and event ordering validation.

Requirements: 11.1, 11.2, 11.3, 11.6, 11.7
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, MagicMock, patch, AsyncMock

from caracal.kafka.replay import (
    EventReplayManager,
    ReplayProgress,
    ReplayValidation
)
from caracal.exceptions import EventReplayError


@pytest.fixture
def replay_manager():
    """Create EventReplayManager instance for testing."""
    return EventReplayManager(
        brokers=["localhost:9092"],
        security_protocol="PLAINTEXT"
    )


@pytest.fixture
def mock_consumer():
    """Create mock Kafka consumer."""
    consumer = Mock()
    consumer.list_topics = Mock(return_value=Mock(
        topics={
            'caracal.metering.events': Mock(
                partitions={
                    0: Mock(),
                    1: Mock(),
                    2: Mock()
                }
            )
        }
    ))
    consumer.offsets_for_times = Mock()
    consumer.commit = Mock()
    consumer.close = Mock()
    consumer.subscribe = Mock()
    consumer.poll = Mock()
    return consumer


class TestEventReplayManager:
    """Test EventReplayManager functionality."""
    
    def test_initialization(self, replay_manager):
        """Test EventReplayManager initialization."""
        assert replay_manager.brokers == ["localhost:9092"]
        assert replay_manager.security_protocol == "PLAINTEXT"
        assert len(replay_manager._active_replays) == 0
    
    @pytest.mark.asyncio
    async def test_reset_consumer_group_offset(self, replay_manager, mock_consumer):
        """
        Test resetting consumer group offsets to specific timestamp.
        
        Requirements: 11.1, 11.2
        """
        # Setup
        timestamp = datetime(2024, 1, 15, 10, 0, 0)
        consumer_group = "test-group"
        topics = ["caracal.metering.events"]
        
        # Mock offsets_for_times to return offsets
        from confluent_kafka import TopicPartition
        mock_offsets = [
            TopicPartition("caracal.metering.events", 0, 1000),
            TopicPartition("caracal.metering.events", 1, 2000),
            TopicPartition("caracal.metering.events", 2, 3000)
        ]
        mock_consumer.offsets_for_times.return_value = mock_offsets
        
        # Patch Consumer class
        with patch('caracal.kafka.replay.Consumer', return_value=mock_consumer):
            # Execute
            new_offsets = await replay_manager.reset_consumer_group_offset(
                consumer_group=consumer_group,
                topics=topics,
                timestamp=timestamp
            )
        
        # Verify
        assert "caracal.metering.events" in new_offsets
        assert new_offsets["caracal.metering.events"][0] == 1000
        assert new_offsets["caracal.metering.events"][1] == 2000
        assert new_offsets["caracal.metering.events"][2] == 3000
        
        # Verify consumer methods called
        mock_consumer.list_topics.assert_called_once()
        mock_consumer.offsets_for_times.assert_called_once()
        mock_consumer.commit.assert_called_once()
        mock_consumer.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_reset_consumer_group_offset_topic_not_found(self, replay_manager, mock_consumer):
        """Test reset fails when topic not found."""
        # Setup
        timestamp = datetime(2024, 1, 15, 10, 0, 0)
        consumer_group = "test-group"
        topics = ["nonexistent.topic"]
        
        # Mock list_topics to return empty topics
        mock_consumer.list_topics.return_value = Mock(topics={})
        
        # Patch Consumer class
        with patch('caracal.kafka.replay.Consumer', return_value=mock_consumer):
            # Execute and verify exception
            with pytest.raises(EventReplayError, match="Topic not found"):
                await replay_manager.reset_consumer_group_offset(
                    consumer_group=consumer_group,
                    topics=topics,
                    timestamp=timestamp
                )
    
    @pytest.mark.asyncio
    async def test_start_replay(self, replay_manager, mock_consumer):
        """
        Test starting event replay operation.
        
        Requirements: 11.1, 11.2, 11.7
        """
        # Setup
        timestamp = datetime(2024, 1, 15, 10, 0, 0)
        consumer_group = "test-group"
        topics = ["caracal.metering.events"]
        
        # Mock offsets_for_times
        from confluent_kafka import TopicPartition
        mock_offsets = [
            TopicPartition("caracal.metering.events", 0, 1000),
            TopicPartition("caracal.metering.events", 1, 2000)
        ]
        mock_consumer.offsets_for_times.return_value = mock_offsets
        
        # Patch Consumer class
        with patch('caracal.kafka.replay.Consumer', return_value=mock_consumer):
            # Execute
            replay_id = await replay_manager.start_replay(
                consumer_group=consumer_group,
                topics=topics,
                start_timestamp=timestamp
            )
        
        # Verify
        assert replay_id is not None
        assert replay_id in replay_manager._active_replays
        
        progress = replay_manager._active_replays[replay_id]
        assert progress.consumer_group == consumer_group
        assert progress.topics == topics
        assert progress.start_timestamp == timestamp
        assert progress.status == "running"
        assert progress.events_processed == 0
    
    def test_update_replay_progress(self, replay_manager):
        """
        Test updating replay progress.
        
        Requirements: 11.7
        """
        # Setup - create a replay
        replay_id = uuid4()
        progress = ReplayProgress(
            replay_id=replay_id,
            consumer_group="test-group",
            topics=["test-topic"],
            start_timestamp=datetime.utcnow(),
            start_time=datetime.utcnow()
        )
        replay_manager._active_replays[replay_id] = progress
        
        # Execute
        new_offsets = {"test-topic": {0: 1000, 1: 2000}}
        replay_manager.update_replay_progress(
            replay_id=replay_id,
            events_processed=100,
            current_offsets=new_offsets
        )
        
        # Verify
        updated_progress = replay_manager._active_replays[replay_id]
        assert updated_progress.events_processed == 100
        assert updated_progress.current_offsets == new_offsets
    
    def test_complete_replay(self, replay_manager):
        """
        Test marking replay as completed.
        
        Requirements: 11.7
        """
        # Setup - create a replay
        replay_id = uuid4()
        progress = ReplayProgress(
            replay_id=replay_id,
            consumer_group="test-group",
            topics=["test-topic"],
            start_timestamp=datetime.utcnow(),
            start_time=datetime.utcnow()
        )
        replay_manager._active_replays[replay_id] = progress
        
        # Execute
        replay_manager.complete_replay(replay_id)
        
        # Verify
        completed_progress = replay_manager._active_replays[replay_id]
        assert completed_progress.status == "completed"
        assert completed_progress.end_time is not None
    
    def test_fail_replay(self, replay_manager):
        """
        Test marking replay as failed.
        
        Requirements: 11.7
        """
        # Setup - create a replay
        replay_id = uuid4()
        progress = ReplayProgress(
            replay_id=replay_id,
            consumer_group="test-group",
            topics=["test-topic"],
            start_timestamp=datetime.utcnow(),
            start_time=datetime.utcnow()
        )
        replay_manager._active_replays[replay_id] = progress
        
        # Execute
        error_message = "Test error"
        replay_manager.fail_replay(replay_id, error_message)
        
        # Verify
        failed_progress = replay_manager._active_replays[replay_id]
        assert failed_progress.status == "failed"
        assert failed_progress.end_time is not None
        assert failed_progress.error_message == error_message
    
    def test_get_replay_progress(self, replay_manager):
        """
        Test getting replay progress.
        
        Requirements: 11.7
        """
        # Setup - create a replay
        replay_id = uuid4()
        progress = ReplayProgress(
            replay_id=replay_id,
            consumer_group="test-group",
            topics=["test-topic"],
            start_timestamp=datetime.utcnow(),
            start_time=datetime.utcnow()
        )
        replay_manager._active_replays[replay_id] = progress
        
        # Execute
        retrieved_progress = replay_manager.get_replay_progress(replay_id)
        
        # Verify
        assert retrieved_progress is not None
        assert retrieved_progress.replay_id == replay_id
        assert retrieved_progress.consumer_group == "test-group"
    
    def test_get_replay_progress_not_found(self, replay_manager):
        """Test getting progress for non-existent replay."""
        # Execute
        progress = replay_manager.get_replay_progress(uuid4())
        
        # Verify
        assert progress is None
    
    def test_list_active_replays(self, replay_manager):
        """
        Test listing active replay operations.
        
        Requirements: 11.7
        """
        # Setup - create multiple replays
        replay1_id = uuid4()
        progress1 = ReplayProgress(
            replay_id=replay1_id,
            consumer_group="group1",
            topics=["topic1"],
            start_timestamp=datetime.utcnow(),
            start_time=datetime.utcnow(),
            status="running"
        )
        replay_manager._active_replays[replay1_id] = progress1
        
        replay2_id = uuid4()
        progress2 = ReplayProgress(
            replay_id=replay2_id,
            consumer_group="group2",
            topics=["topic2"],
            start_timestamp=datetime.utcnow(),
            start_time=datetime.utcnow(),
            status="completed"
        )
        replay_manager._active_replays[replay2_id] = progress2
        
        # Execute
        active_replays = replay_manager.list_active_replays()
        
        # Verify - only running replays
        assert len(active_replays) == 1
        assert active_replays[0].replay_id == replay1_id
    
    def test_list_all_replays(self, replay_manager):
        """
        Test listing all replay operations.
        
        Requirements: 11.7
        """
        # Setup - create multiple replays
        replay1_id = uuid4()
        progress1 = ReplayProgress(
            replay_id=replay1_id,
            consumer_group="group1",
            topics=["topic1"],
            start_timestamp=datetime.utcnow(),
            start_time=datetime.utcnow(),
            status="running"
        )
        replay_manager._active_replays[replay1_id] = progress1
        
        replay2_id = uuid4()
        progress2 = ReplayProgress(
            replay_id=replay2_id,
            consumer_group="group2",
            topics=["topic2"],
            start_timestamp=datetime.utcnow(),
            start_time=datetime.utcnow(),
            status="completed"
        )
        replay_manager._active_replays[replay2_id] = progress2
        
        # Execute
        all_replays = replay_manager.list_all_replays()
        
        # Verify - all replays
        assert len(all_replays) == 2
    
    @pytest.mark.asyncio
    async def test_validate_event_ordering_success(self, replay_manager, mock_consumer):
        """
        Test validating event ordering with all events in order.
        
        Requirements: 11.3, 11.6
        """
        # Setup
        consumer_group = "test-group"
        topics = ["caracal.metering.events"]
        
        # Mock poll to return messages in order
        messages = []
        base_timestamp = int(datetime(2024, 1, 15, 10, 0, 0).timestamp() * 1000)
        
        for i in range(5):
            msg = Mock()
            msg.error.return_value = None
            msg.timestamp.return_value = (1, base_timestamp + i * 1000)  # Increasing timestamps
            msg.topic.return_value = "caracal.metering.events"
            msg.partition.return_value = 0
            msg.offset.return_value = i
            messages.append(msg)
        
        # Add None to signal end
        messages.append(None)
        
        mock_consumer.poll.side_effect = messages
        
        # Patch Consumer class
        with patch('caracal.kafka.replay.Consumer', return_value=mock_consumer):
            # Execute
            validation = await replay_manager.validate_event_ordering(
                consumer_group=consumer_group,
                topics=topics,
                max_events=5
            )
        
        # Verify
        assert validation.total_events == 5
        assert validation.ordered_events == 5
        assert validation.out_of_order_events == 0
        assert validation.validation_passed is True
        assert len(validation.out_of_order_details) == 0
    
    @pytest.mark.asyncio
    async def test_validate_event_ordering_out_of_order(self, replay_manager, mock_consumer):
        """
        Test validating event ordering with out-of-order events.
        
        Requirements: 11.3, 11.6
        """
        # Setup
        consumer_group = "test-group"
        topics = ["caracal.metering.events"]
        
        # Mock poll to return messages with one out of order
        messages = []
        base_timestamp = int(datetime(2024, 1, 15, 10, 0, 0).timestamp() * 1000)
        
        # In order: 0, 1, 2
        for i in range(3):
            msg = Mock()
            msg.error.return_value = None
            msg.timestamp.return_value = (1, base_timestamp + i * 1000)
            msg.topic.return_value = "caracal.metering.events"
            msg.partition.return_value = 0
            msg.offset.return_value = i
            messages.append(msg)
        
        # Out of order: timestamp goes back
        msg = Mock()
        msg.error.return_value = None
        msg.timestamp.return_value = (1, base_timestamp + 1000)  # Earlier than previous
        msg.topic.return_value = "caracal.metering.events"
        msg.partition.return_value = 0
        msg.offset.return_value = 3
        messages.append(msg)
        
        # Add None to signal end
        messages.append(None)
        
        mock_consumer.poll.side_effect = messages
        
        # Patch Consumer class
        with patch('caracal.kafka.replay.Consumer', return_value=mock_consumer):
            # Execute
            validation = await replay_manager.validate_event_ordering(
                consumer_group=consumer_group,
                topics=topics,
                max_events=4
            )
        
        # Verify
        assert validation.total_events == 4
        assert validation.ordered_events == 3
        assert validation.out_of_order_events == 1
        assert validation.validation_passed is False
        assert len(validation.out_of_order_details) == 1
        
        # Check out-of-order detail
        detail = validation.out_of_order_details[0]
        assert detail["topic"] == "caracal.metering.events"
        assert detail["partition"] == 0
        assert detail["offset"] == 3


class TestReplayProgress:
    """Test ReplayProgress dataclass."""
    
    def test_replay_progress_initialization(self):
        """Test ReplayProgress initialization."""
        replay_id = uuid4()
        timestamp = datetime.utcnow()
        
        progress = ReplayProgress(
            replay_id=replay_id,
            consumer_group="test-group",
            topics=["topic1", "topic2"],
            start_timestamp=timestamp,
            start_time=timestamp
        )
        
        assert progress.replay_id == replay_id
        assert progress.consumer_group == "test-group"
        assert progress.topics == ["topic1", "topic2"]
        assert progress.start_timestamp == timestamp
        assert progress.start_time == timestamp
        assert progress.end_time is None
        assert progress.events_processed == 0
        assert progress.current_offsets == {}
        assert progress.status == "running"
        assert progress.error_message is None


class TestReplayValidation:
    """Test ReplayValidation dataclass."""
    
    def test_replay_validation_passed(self):
        """Test ReplayValidation with passing validation."""
        validation = ReplayValidation(
            total_events=100,
            ordered_events=100,
            out_of_order_events=0,
            out_of_order_details=[],
            validation_passed=True
        )
        
        assert validation.total_events == 100
        assert validation.ordered_events == 100
        assert validation.out_of_order_events == 0
        assert validation.validation_passed is True
    
    def test_replay_validation_failed(self):
        """Test ReplayValidation with failing validation."""
        validation = ReplayValidation(
            total_events=100,
            ordered_events=95,
            out_of_order_events=5,
            out_of_order_details=[
                {"topic": "test", "partition": 0, "offset": 10}
            ],
            validation_passed=False
        )
        
        assert validation.total_events == 100
        assert validation.ordered_events == 95
        assert validation.out_of_order_events == 5
        assert validation.validation_passed is False
        assert len(validation.out_of_order_details) == 1
