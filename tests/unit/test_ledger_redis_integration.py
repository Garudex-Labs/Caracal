"""
Unit tests for LedgerQuery Redis cache integration.

Tests the integration between LedgerQuery and RedisSpendingCache for
fast recent spending queries.

Requirements: 20.3, 20.4
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, MagicMock
import tempfile
import os

from caracal.core.ledger import LedgerWriter, LedgerQuery
from caracal.redis.spending_cache import RedisSpendingCache


@pytest.fixture
def temp_ledger():
    """Create temporary ledger file."""
    fd, path = tempfile.mkstemp(suffix='.jsonl')
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def mock_redis_cache():
    """Create mock Redis cache."""
    cache = Mock(spec=RedisSpendingCache)
    cache.get_spending_in_range = Mock(return_value=Decimal('100.50'))
    cache.update_spending = Mock()
    return cache


def test_ledger_writer_updates_cache(temp_ledger, mock_redis_cache):
    """Test that LedgerWriter updates Redis cache on write."""
    writer = LedgerWriter(temp_ledger, redis_cache=mock_redis_cache)
    
    # Write event
    event = writer.append_event(
        agent_id='agent-123',
        resource_type='api_call',
        quantity=Decimal('1'),
        cost=Decimal('10.50'),
        currency='USD'
    )
    
    # Verify cache was updated
    mock_redis_cache.update_spending.assert_called_once()
    call_args = mock_redis_cache.update_spending.call_args
    assert call_args[1]['agent_id'] == 'agent-123'
    assert call_args[1]['cost'] == Decimal('10.50')
    assert call_args[1]['event_id'] == str(event.event_id)


def test_ledger_writer_without_cache(temp_ledger):
    """Test that LedgerWriter works without Redis cache (v0.1/v0.2 mode)."""
    writer = LedgerWriter(temp_ledger, redis_cache=None)
    
    # Write event should succeed without cache
    event = writer.append_event(
        agent_id='agent-123',
        resource_type='api_call',
        quantity=Decimal('1'),
        cost=Decimal('10.50'),
        currency='USD'
    )
    
    assert event.event_id == 1
    assert event.agent_id == 'agent-123'
    assert event.cost == '10.50'


def test_ledger_query_cache_hit_recent_data(temp_ledger, mock_redis_cache):
    """Test LedgerQuery uses cache for recent data (last 24 hours)."""
    query = LedgerQuery(temp_ledger, redis_cache=mock_redis_cache)
    
    # Query recent data (within last 24 hours)
    now = datetime.utcnow()
    start_time = now - timedelta(hours=2)
    end_time = now
    
    spending = query.sum_spending('agent-123', start_time, end_time)
    
    # Verify cache was queried
    mock_redis_cache.get_spending_in_range.assert_called_once_with(
        'agent-123',
        start_time,
        end_time
    )
    
    # Verify result from cache
    assert spending == Decimal('100.50')


def test_ledger_query_cache_miss_old_data(temp_ledger, mock_redis_cache):
    """Test LedgerQuery falls back to database for old data (>24 hours)."""
    # Write some old events to ledger
    writer = LedgerWriter(temp_ledger, redis_cache=None)
    old_time = datetime.utcnow() - timedelta(days=2)
    
    writer.append_event(
        agent_id='agent-123',
        resource_type='api_call',
        quantity=Decimal('1'),
        cost=Decimal('50.00'),
        currency='USD',
        timestamp=old_time
    )
    
    # Query old data
    query = LedgerQuery(temp_ledger, redis_cache=mock_redis_cache)
    start_time = old_time - timedelta(hours=1)
    end_time = old_time + timedelta(hours=1)
    
    spending = query.sum_spending('agent-123', start_time, end_time)
    
    # Verify cache was NOT queried (data too old)
    mock_redis_cache.get_spending_in_range.assert_not_called()
    
    # Verify result from database
    assert spending == Decimal('50.00')


def test_ledger_query_hybrid_cache_and_db(temp_ledger, mock_redis_cache):
    """Test LedgerQuery combines cache and database for queries spanning both."""
    # Write old event to ledger
    writer = LedgerWriter(temp_ledger, redis_cache=None)
    old_time = datetime.utcnow() - timedelta(days=2)
    
    writer.append_event(
        agent_id='agent-123',
        resource_type='api_call',
        quantity=Decimal('1'),
        cost=Decimal('50.00'),
        currency='USD',
        timestamp=old_time
    )
    
    # Mock cache to return recent spending
    mock_redis_cache.get_spending_in_range.return_value = Decimal('100.50')
    
    # Query spanning old and recent data
    query = LedgerQuery(temp_ledger, redis_cache=mock_redis_cache)
    start_time = old_time - timedelta(hours=1)
    end_time = datetime.utcnow()
    
    spending = query.sum_spending('agent-123', start_time, end_time)
    
    # Verify cache was queried for recent data
    mock_redis_cache.get_spending_in_range.assert_called_once()
    
    # Verify result combines cache (100.50) and database (50.00)
    assert spending == Decimal('150.50')


def test_ledger_query_cache_failure_fallback(temp_ledger, mock_redis_cache):
    """Test LedgerQuery falls back to database when cache fails."""
    # Write event to ledger
    writer = LedgerWriter(temp_ledger, redis_cache=None)
    now = datetime.utcnow()
    
    writer.append_event(
        agent_id='agent-123',
        resource_type='api_call',
        quantity=Decimal('1'),
        cost=Decimal('75.00'),
        currency='USD',
        timestamp=now
    )
    
    # Mock cache to raise exception
    mock_redis_cache.get_spending_in_range.side_effect = Exception("Redis connection failed")
    
    # Query recent data
    query = LedgerQuery(temp_ledger, redis_cache=mock_redis_cache)
    start_time = now - timedelta(hours=1)
    end_time = now + timedelta(hours=1)
    
    spending = query.sum_spending('agent-123', start_time, end_time)
    
    # Verify cache was attempted
    mock_redis_cache.get_spending_in_range.assert_called_once()
    
    # Verify fallback to database succeeded
    assert spending == Decimal('75.00')


def test_ledger_query_without_cache(temp_ledger):
    """Test LedgerQuery works without Redis cache (v0.1/v0.2 mode)."""
    # Write event to ledger
    writer = LedgerWriter(temp_ledger, redis_cache=None)
    now = datetime.utcnow()
    
    writer.append_event(
        agent_id='agent-123',
        resource_type='api_call',
        quantity=Decimal('1'),
        cost=Decimal('75.00'),
        currency='USD',
        timestamp=now
    )
    
    # Query without cache
    query = LedgerQuery(temp_ledger, redis_cache=None)
    start_time = now - timedelta(hours=1)
    end_time = now + timedelta(hours=1)
    
    spending = query.sum_spending('agent-123', start_time, end_time)
    
    # Verify result from database
    assert spending == Decimal('75.00')


def test_cache_update_failure_does_not_fail_write(temp_ledger, mock_redis_cache):
    """Test that cache update failures don't prevent ledger writes."""
    # Mock cache to raise exception on update
    mock_redis_cache.update_spending.side_effect = Exception("Redis connection failed")
    
    writer = LedgerWriter(temp_ledger, redis_cache=mock_redis_cache)
    
    # Write should succeed despite cache failure
    event = writer.append_event(
        agent_id='agent-123',
        resource_type='api_call',
        quantity=Decimal('1'),
        cost=Decimal('10.50'),
        currency='USD'
    )
    
    # Verify event was written
    assert event.event_id == 1
    assert event.agent_id == 'agent-123'
    
    # Verify cache update was attempted
    mock_redis_cache.update_spending.assert_called_once()
