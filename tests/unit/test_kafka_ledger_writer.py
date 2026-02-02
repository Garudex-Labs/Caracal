"""
Unit tests for LedgerWriterConsumer.

Tests the Kafka consumer that writes metering events to PostgreSQL ledger.
"""

import json
import pytest
from datetime import datetime
from decimal import Decimal
from uuid import uuid4
from unittest.mock import Mock, MagicMock, patch, AsyncMock

from caracal.kafka.ledger_writer import LedgerWriterConsumer
from caracal.kafka.consumer import KafkaMessage
from caracal.db.models import LedgerEvent, ProvisionalCharge
from caracal.exceptions import InvalidLedgerEventError


class TestLedgerWriterConsumer:
    """Test suite for LedgerWriterConsumer."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        session = Mock()
        session.query = Mock()
        session.add = Mock()
        session.flush = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        session.close = Mock()
        return session
    
    @pytest.fixture
    def mock_db_session_factory(self, mock_db_session):
        """Create mock database session factory."""
        return Mock(return_value=mock_db_session)
    
    @pytest.fixture
    def mock_merkle_batcher(self):
        """Create mock Merkle batcher."""
        batcher = Mock()
        batcher.add_event = AsyncMock()
        return batcher
    
    @pytest.fixture
    def consumer(self, mock_db_session_factory, mock_merkle_batcher):
        """Create LedgerWriterConsumer instance."""
        return LedgerWriterConsumer(
            brokers=["localhost:9092"],
            db_session_factory=mock_db_session_factory,
            merkle_batcher=mock_merkle_batcher
        )
    
    def test_consumer_initialization(self, consumer):
        """Test consumer initializes with correct configuration."""
        assert consumer.TOPIC == "caracal.metering.events"
        assert consumer.CONSUMER_GROUP == "ledger-writer-group"
        assert consumer.topics == ["caracal.metering.events"]
        assert consumer.consumer_group == "ledger-writer-group"
    
    @pytest.mark.asyncio
    async def test_process_message_success(
        self,
        consumer,
        mock_db_session,
        mock_merkle_batcher
    ):
        """Test successful processing of metering event."""
        # Create test event
        agent_id = str(uuid4())
        provisional_charge_id = str(uuid4())
        event_data = {
            "event_id": str(uuid4()),
            "schema_version": 1,
            "timestamp": int(datetime.utcnow().timestamp() * 1000),
            "agent_id": agent_id,
            "event_type": "metering",
            "resource_type": "openai.gpt-4",
            "quantity": 1000.0,
            "cost": 0.03,
            "currency": "USD",
            "provisional_charge_id": provisional_charge_id,
            "metadata": {"model": "gpt-4"}
        }
        
        # Create Kafka message
        message = KafkaMessage(
            topic="caracal.metering.events",
            partition=0,
            offset=123,
            key=agent_id.encode('utf-8'),
            value=json.dumps(event_data).encode('utf-8'),
            timestamp=event_data["timestamp"]
        )
        
        # Mock ledger event with event_id
        mock_ledger_event = Mock(spec=LedgerEvent)
        mock_ledger_event.event_id = 1
        mock_ledger_event.agent_id = agent_id
        mock_ledger_event.resource_type = "openai.gpt-4"
        mock_ledger_event.cost = Decimal("0.03")
        
        # Mock session.add to capture the ledger event
        def capture_ledger_event(event):
            # Copy attributes from captured event to mock
            mock_ledger_event.event_id = 1
            mock_ledger_event.agent_id = event.agent_id
            mock_ledger_event.resource_type = event.resource_type
            mock_ledger_event.cost = event.cost
        
        mock_db_session.add.side_effect = capture_ledger_event
        
        # Mock provisional charge query
        mock_charge = Mock(spec=ProvisionalCharge)
        mock_charge.charge_id = provisional_charge_id
        mock_charge.released = False
        mock_charge.amount = Decimal("0.03")
        mock_charge.currency = "USD"
        
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_charge
        mock_db_session.query.return_value = mock_query
        
        # Process message
        await consumer.process_message(message)
        
        # Verify database operations
        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_called_once()
        mock_db_session.commit.assert_called_once()
        
        # Verify provisional charge was released
        assert mock_charge.released is True
        assert mock_charge.final_charge_event_id == 1
        
        # Verify Merkle batcher was called
        mock_merkle_batcher.add_event.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_message_invalid_json(self, consumer):
        """Test processing message with invalid JSON."""
        # Create message with invalid JSON
        message = KafkaMessage(
            topic="caracal.metering.events",
            partition=0,
            offset=123,
            key=b"test-agent",
            value=b"invalid json {",
            timestamp=int(datetime.utcnow().timestamp() * 1000)
        )
        
        # Should raise InvalidLedgerEventError
        with pytest.raises(InvalidLedgerEventError):
            await consumer.process_message(message)
    
    @pytest.mark.asyncio
    async def test_process_message_missing_required_field(self, consumer):
        """Test processing message with missing required field."""
        # Create event missing agent_id
        event_data = {
            "event_id": str(uuid4()),
            "schema_version": 1,
            "timestamp": int(datetime.utcnow().timestamp() * 1000),
            # Missing agent_id
            "event_type": "metering",
            "resource_type": "openai.gpt-4",
            "quantity": 1000.0,
            "cost": 0.03,
            "currency": "USD"
        }
        
        message = KafkaMessage(
            topic="caracal.metering.events",
            partition=0,
            offset=123,
            key=b"test-agent",
            value=json.dumps(event_data).encode('utf-8'),
            timestamp=event_data["timestamp"]
        )
        
        # Should raise InvalidLedgerEventError
        with pytest.raises(InvalidLedgerEventError, match="Missing required field: agent_id"):
            await consumer.process_message(message)
    
    @pytest.mark.asyncio
    async def test_process_message_invalid_event_type(self, consumer):
        """Test processing message with invalid event_type."""
        # Create event with wrong event_type
        event_data = {
            "event_id": str(uuid4()),
            "schema_version": 1,
            "timestamp": int(datetime.utcnow().timestamp() * 1000),
            "agent_id": str(uuid4()),
            "event_type": "policy_decision",  # Wrong type
            "resource_type": "openai.gpt-4",
            "quantity": 1000.0,
            "cost": 0.03,
            "currency": "USD"
        }
        
        message = KafkaMessage(
            topic="caracal.metering.events",
            partition=0,
            offset=123,
            key=b"test-agent",
            value=json.dumps(event_data).encode('utf-8'),
            timestamp=event_data["timestamp"]
        )
        
        # Should raise InvalidLedgerEventError
        with pytest.raises(InvalidLedgerEventError, match="Invalid event_type"):
            await consumer.process_message(message)
    
    @pytest.mark.asyncio
    async def test_process_message_negative_cost(self, consumer):
        """Test processing message with negative cost."""
        # Create event with negative cost
        event_data = {
            "event_id": str(uuid4()),
            "schema_version": 1,
            "timestamp": int(datetime.utcnow().timestamp() * 1000),
            "agent_id": str(uuid4()),
            "event_type": "metering",
            "resource_type": "openai.gpt-4",
            "quantity": 1000.0,
            "cost": -0.03,  # Negative cost
            "currency": "USD"
        }
        
        message = KafkaMessage(
            topic="caracal.metering.events",
            partition=0,
            offset=123,
            key=b"test-agent",
            value=json.dumps(event_data).encode('utf-8'),
            timestamp=event_data["timestamp"]
        )
        
        # Should raise InvalidLedgerEventError
        with pytest.raises(InvalidLedgerEventError, match="cost must be non-negative"):
            await consumer.process_message(message)
    
    @pytest.mark.asyncio
    async def test_process_message_without_provisional_charge(
        self,
        consumer,
        mock_db_session,
        mock_merkle_batcher
    ):
        """Test processing message without provisional charge."""
        # Create event without provisional_charge_id
        agent_id = str(uuid4())
        event_data = {
            "event_id": str(uuid4()),
            "schema_version": 1,
            "timestamp": int(datetime.utcnow().timestamp() * 1000),
            "agent_id": agent_id,
            "event_type": "metering",
            "resource_type": "openai.gpt-4",
            "quantity": 1000.0,
            "cost": 0.03,
            "currency": "USD"
            # No provisional_charge_id
        }
        
        message = KafkaMessage(
            topic="caracal.metering.events",
            partition=0,
            offset=123,
            key=agent_id.encode('utf-8'),
            value=json.dumps(event_data).encode('utf-8'),
            timestamp=event_data["timestamp"]
        )
        
        # Process message
        await consumer.process_message(message)
        
        # Verify database operations
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        
        # Verify provisional charge query was NOT called
        mock_db_session.query.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_message_database_error_rollback(
        self,
        consumer,
        mock_db_session
    ):
        """Test that database errors trigger rollback."""
        # Create valid event
        event_data = {
            "event_id": str(uuid4()),
            "schema_version": 1,
            "timestamp": int(datetime.utcnow().timestamp() * 1000),
            "agent_id": str(uuid4()),
            "event_type": "metering",
            "resource_type": "openai.gpt-4",
            "quantity": 1000.0,
            "cost": 0.03,
            "currency": "USD"
        }
        
        message = KafkaMessage(
            topic="caracal.metering.events",
            partition=0,
            offset=123,
            key=b"test-agent",
            value=json.dumps(event_data).encode('utf-8'),
            timestamp=event_data["timestamp"]
        )
        
        # Make commit raise an error
        mock_db_session.commit.side_effect = Exception("Database error")
        
        # Should raise exception
        with pytest.raises(Exception, match="Database error"):
            await consumer.process_message(message)
        
        # Verify rollback was called
        mock_db_session.rollback.assert_called_once()
        mock_db_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_release_provisional_charge_not_found(
        self,
        consumer,
        mock_db_session
    ):
        """Test releasing provisional charge that doesn't exist."""
        # Mock query to return None
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query
        
        # Should not raise exception (logs warning instead)
        await consumer._release_provisional_charge(
            mock_db_session,
            uuid4(),
            123
        )
    
    @pytest.mark.asyncio
    async def test_release_provisional_charge_already_released(
        self,
        consumer,
        mock_db_session
    ):
        """Test releasing provisional charge that's already released."""
        # Mock charge that's already released
        mock_charge = Mock(spec=ProvisionalCharge)
        mock_charge.released = True
        
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_charge
        mock_db_session.query.return_value = mock_query
        
        # Should not raise exception (logs warning instead)
        await consumer._release_provisional_charge(
            mock_db_session,
            uuid4(),
            123
        )
        
        # Charge should still be marked as released
        assert mock_charge.released is True
    
    @pytest.mark.asyncio
    async def test_merkle_batcher_error_does_not_fail_processing(
        self,
        consumer,
        mock_db_session,
        mock_merkle_batcher
    ):
        """Test that Merkle batcher errors don't fail event processing."""
        # Create valid event
        event_data = {
            "event_id": str(uuid4()),
            "schema_version": 1,
            "timestamp": int(datetime.utcnow().timestamp() * 1000),
            "agent_id": str(uuid4()),
            "event_type": "metering",
            "resource_type": "openai.gpt-4",
            "quantity": 1000.0,
            "cost": 0.03,
            "currency": "USD"
        }
        
        message = KafkaMessage(
            topic="caracal.metering.events",
            partition=0,
            offset=123,
            key=b"test-agent",
            value=json.dumps(event_data).encode('utf-8'),
            timestamp=event_data["timestamp"]
        )
        
        # Make Merkle batcher raise error
        mock_merkle_batcher.add_event.side_effect = Exception("Merkle error")
        
        # Should NOT raise exception (error is logged but not propagated)
        await consumer.process_message(message)
        
        # Verify database commit still happened
        mock_db_session.commit.assert_called_once()
