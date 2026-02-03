"""
Integration tests for Redis spending cache.

Tests the complete Redis spending cache integration including:
- RedisClient connection
- RedisSpendingCache operations
- LedgerWriter cache updates
- LedgerQuery cache queries

Requirements: 20.3, 20.4, 16.4, 21.4, 25.6
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
import tempfile
import os
import time

from caracal.redis.client import RedisClient
from caracal.redis.spending_cache import RedisSpendingCache
from caracal.core.ledger import LedgerWriter, LedgerQuery


# Skip tests if Redis is not available
pytest_plugins = []

def is_redis_available():
    """Check if Redis is available for testing."""
    try:
        client = RedisClient(host='localhost', port=6379, password=None)
        return client.ping()
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not is_redis_available(),
    reason="Redis not available for integration testing"
)


@pytest.fixture
def redis_client():
    """Create Redis client for testing."""
    client = RedisClient(
        host='localhost',
        port=6379,
        password=None,
        db=15  # Use separate DB for testing
    )
    yield client
    # Cleanup: flush test database
    try:
        client._client.flushdb()
    except Exception:
        pass
    client.close()


@pytest.fixture
def redis_cache(redis_client):
    """Create Redis spending cache for testing."""
    return RedisSpendingCache(redis_client, ttl_seconds=3600)


@pytest.fixture
def temp_ledger():
    """Create temporary ledger file."""
    fd, path = tempfile.mkstemp(suffix='.jsonl')
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


def test_redis_client_connection(redis_client):
    """Test Redis client can connect and ping."""
    assert redis_client.ping() is True


def test_redis_spending_cache_update_and_get(redis_cache):
    """Test updating and retrieving spending from cache."""
    agent_id = 'test-agent-001'
    now = datetime.utcnow()
    
    # Update spending
    redis_cache.update_spending(
        agent_id=agent_id,
        cost=Decimal('10.50'),
        timestamp=now,
        event_id='event-001'
    )
    
    redis_cache.update_spending(
        agent_id=agent_id,
        cost=Decimal('5.25'),
        timestamp=now + timedelta(minutes=5),
        event_id='event-002'
    )
    
    # Get total spending
    total = redis_cache.get_total_spending(agent_id)
    assert total == Decimal('15.75')
    
    # Get spending in range
    start_time = now - timedelta(minutes=1)
    end_time = now + timedelta(minutes=10)
    range_spending = redis_cache.get_spending_in_range(agent_id, start_time, end_time)
    assert range_spending == Decimal('15.75')


def test_redis_spending_cache_time_range_query(redis_cache):
    """Test time-range spending queries."""
    agent_id = 'test-agent-002'
    now = datetime.utcnow()
    
    # Add events at different times
    redis_cache.update_spending(
        agent_id=agent_id,
        cost=Decimal('10.00'),
        timestamp=now - timedelta(hours=2),
        event_id='event-001'
    )
    
    redis_cache.update_spending(
        agent_id=agent_id,
        cost=Decimal('20.00'),
        timestamp=now - timedelta(hours=1),
        event_id='event-002'
    )
    
    redis_cache.update_spending(
        agent_id=agent_id,
        cost=Decimal('30.00'),
        timestamp=now,
        event_id='event-003'
    )
    
    # Query last hour only
    start_time = now - timedelta(hours=1, minutes=5)
    end_time = now + timedelta(minutes=5)
    recent_spending = redis_cache.get_spending_in_range(agent_id, start_time, end_time)
    assert recent_spending == Decimal('50.00')  # Last two events
    
    # Query all events
    start_time = now - timedelta(hours=3)
    end_time = now + timedelta(minutes=5)
    all_spending = redis_cache.get_spending_in_range(agent_id, start_time, end_time)
    assert all_spending == Decimal('60.00')  # All three events


def test_redis_spending_trend_storage(redis_cache):
    """Test storing and retrieving spending trends."""
    agent_id = 'test-agent-003'
    now = datetime.utcnow()
    
    # Store hourly trends
    redis_cache.store_spending_trend(
        agent_id=agent_id,
        window='hourly',
        timestamp=now - timedelta(hours=2),
        spending=Decimal('10.00')
    )
    
    redis_cache.store_spending_trend(
        agent_id=agent_id,
        window='hourly',
        timestamp=now - timedelta(hours=1),
        spending=Decimal('15.00')
    )
    
    redis_cache.store_spending_trend(
        agent_id=agent_id,
        window='hourly',
        timestamp=now,
        spending=Decimal('20.00')
    )
    
    # Get trends
    start_time = now - timedelta(hours=3)
    end_time = now + timedelta(minutes=5)
    trends = redis_cache.get_spending_trend(agent_id, 'hourly', start_time, end_time)
    
    assert len(trends) == 3
    assert trends[0][1] == Decimal('10.00')
    assert trends[1][1] == Decimal('15.00')
    assert trends[2][1] == Decimal('20.00')


def test_ledger_writer_updates_redis_cache(temp_ledger, redis_cache):
    """Test LedgerWriter updates Redis cache on write."""
    writer = LedgerWriter(temp_ledger, redis_cache=redis_cache)
    agent_id = 'test-agent-004'
    
    # Write events
    event1 = writer.append_event(
        agent_id=agent_id,
        resource_type='api_call',
        quantity=Decimal('1'),
        cost=Decimal('10.50'),
        currency='USD'
    )
    
    event2 = writer.append_event(
        agent_id=agent_id,
        resource_type='api_call',
        quantity=Decimal('1'),
        cost=Decimal('5.25'),
        currency='USD'
    )
    
    # Verify cache was updated
    total = redis_cache.get_total_spending(agent_id)
    assert total == Decimal('15.75')


def test_ledger_query_uses_redis_cache(temp_ledger, redis_cache):
    """Test LedgerQuery uses Redis cache for recent data."""
    # Write events to ledger with cache
    writer = LedgerWriter(temp_ledger, redis_cache=redis_cache)
    agent_id = 'test-agent-005'
    now = datetime.utcnow()
    
    writer.append_event(
        agent_id=agent_id,
        resource_type='api_call',
        quantity=Decimal('1'),
        cost=Decimal('10.00'),
        currency='USD',
        timestamp=now
    )
    
    writer.append_event(
        agent_id=agent_id,
        resource_type='api_call',
        quantity=Decimal('1'),
        cost=Decimal('20.00'),
        currency='USD',
        timestamp=now + timedelta(minutes=5)
    )
    
    # Query recent data (should use cache)
    query = LedgerQuery(temp_ledger, redis_cache=redis_cache)
    start_time = now - timedelta(minutes=1)
    end_time = now + timedelta(minutes=10)
    
    spending = query.sum_spending(agent_id, start_time, end_time)
    assert spending == Decimal('30.00')


def test_ledger_query_hybrid_cache_and_db(temp_ledger, redis_cache):
    """Test LedgerQuery combines cache and database for queries spanning both."""
    agent_id = 'test-agent-006'
    now = datetime.utcnow()
    old_time = now - timedelta(days=2)
    
    # Write old event to ledger (no cache)
    writer = LedgerWriter(temp_ledger, redis_cache=None)
    writer.append_event(
        agent_id=agent_id,
        resource_type='api_call',
        quantity=Decimal('1'),
        cost=Decimal('50.00'),
        currency='USD',
        timestamp=old_time
    )
    
    # Write recent event with cache
    writer_with_cache = LedgerWriter(temp_ledger, redis_cache=redis_cache)
    writer_with_cache.append_event(
        agent_id=agent_id,
        resource_type='api_call',
        quantity=Decimal('1'),
        cost=Decimal('100.00'),
        currency='USD',
        timestamp=now
    )
    
    # Query spanning old and recent data
    query = LedgerQuery(temp_ledger, redis_cache=redis_cache)
    start_time = old_time - timedelta(hours=1)
    end_time = now + timedelta(hours=1)
    
    spending = query.sum_spending(agent_id, start_time, end_time)
    assert spending == Decimal('150.00')  # 50 from DB + 100 from cache


def test_redis_cache_ttl_expiration(redis_cache):
    """Test that cache entries expire after TTL."""
    # Create cache with short TTL
    short_ttl_cache = RedisSpendingCache(redis_cache.redis, ttl_seconds=2)
    agent_id = 'test-agent-007'
    now = datetime.utcnow()
    
    # Update spending
    short_ttl_cache.update_spending(
        agent_id=agent_id,
        cost=Decimal('10.00'),
        timestamp=now,
        event_id='event-001'
    )
    
    # Verify data exists
    total = short_ttl_cache.get_total_spending(agent_id)
    assert total == Decimal('10.00')
    
    # Wait for TTL to expire
    time.sleep(3)
    
    # Verify data expired
    total_after_expiry = short_ttl_cache.get_total_spending(agent_id)
    assert total_after_expiry is None


def test_redis_cache_cleanup_old_events(redis_cache):
    """Test cleaning up old events from cache."""
    agent_id = 'test-agent-008'
    now = datetime.utcnow()
    
    # Add old and recent events
    redis_cache.update_spending(
        agent_id=agent_id,
        cost=Decimal('10.00'),
        timestamp=now - timedelta(hours=5),
        event_id='event-001'
    )
    
    redis_cache.update_spending(
        agent_id=agent_id,
        cost=Decimal('20.00'),
        timestamp=now,
        event_id='event-002'
    )
    
    # Cleanup events older than 2 hours
    cutoff = now - timedelta(hours=2)
    removed = redis_cache.cleanup_old_events(agent_id, cutoff)
    assert removed == 1
    
    # Verify only recent event remains
    start_time = now - timedelta(hours=6)
    end_time = now + timedelta(hours=1)
    spending = redis_cache.get_spending_in_range(agent_id, start_time, end_time)
    assert spending == Decimal('20.00')


def test_redis_cache_clear_agent(redis_cache):
    """Test clearing all cached data for an agent."""
    agent_id = 'test-agent-009'
    now = datetime.utcnow()
    
    # Add spending and trends
    redis_cache.update_spending(
        agent_id=agent_id,
        cost=Decimal('10.00'),
        timestamp=now,
        event_id='event-001'
    )
    
    redis_cache.store_spending_trend(
        agent_id=agent_id,
        window='hourly',
        timestamp=now,
        spending=Decimal('10.00')
    )
    
    # Verify data exists
    total = redis_cache.get_total_spending(agent_id)
    assert total == Decimal('10.00')
    
    # Clear cache
    redis_cache.clear_agent_cache(agent_id)
    
    # Verify data cleared
    total_after_clear = redis_cache.get_total_spending(agent_id)
    assert total_after_clear is None
    
    trends = redis_cache.get_spending_trend(
        agent_id, 'hourly',
        now - timedelta(hours=1),
        now + timedelta(hours=1)
    )
    assert len(trends) == 0


def test_multiple_agents_isolation(redis_cache):
    """Test that spending for different agents is isolated."""
    agent1 = 'test-agent-010'
    agent2 = 'test-agent-011'
    now = datetime.utcnow()
    
    # Add spending for agent1
    redis_cache.update_spending(
        agent_id=agent1,
        cost=Decimal('10.00'),
        timestamp=now,
        event_id='event-001'
    )
    
    # Add spending for agent2
    redis_cache.update_spending(
        agent_id=agent2,
        cost=Decimal('20.00'),
        timestamp=now,
        event_id='event-002'
    )
    
    # Verify isolation
    total1 = redis_cache.get_total_spending(agent1)
    total2 = redis_cache.get_total_spending(agent2)
    
    assert total1 == Decimal('10.00')
    assert total2 == Decimal('20.00')
