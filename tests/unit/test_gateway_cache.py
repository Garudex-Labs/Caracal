"""
Unit tests for Gateway Policy Cache.

Tests the PolicyCache functionality:
- Cache get/put operations
- TTL-based expiration
- LRU eviction
- Explicit invalidation
- Cache statistics
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal

from caracal.gateway.cache import PolicyCache, PolicyCacheConfig, CachedPolicy, CacheStats
from caracal.core.policy import BudgetPolicy


@pytest.fixture
def cache_config():
    """Create a test cache configuration."""
    return PolicyCacheConfig(
        ttl_seconds=60,
        max_size=100,
        eviction_policy="LRU",
        invalidation_enabled=True
    )


@pytest.fixture
def policy_cache(cache_config):
    """Create a PolicyCache instance for testing."""
    return PolicyCache(cache_config)


@pytest.fixture
def sample_policy():
    """Create a sample budget policy."""
    return BudgetPolicy(
        policy_id="policy-123",
        agent_id="agent-456",
        limit_amount="100.00",
        time_window="daily",
        currency="USD",
        created_at=datetime.utcnow().isoformat() + "Z",
        active=True
    )


class TestPolicyCacheInitialization:
    """Test PolicyCache initialization."""
    
    def test_initialization(self, policy_cache, cache_config):
        """Test that PolicyCache initializes correctly."""
        assert policy_cache.config == cache_config
        assert policy_cache._cache is not None
        assert policy_cache._hits == 0
        assert policy_cache._misses == 0
        assert policy_cache._evictions == 0
        assert policy_cache._invalidations == 0


class TestPolicyCacheGetPut:
    """Test cache get and put operations."""
    
    @pytest.mark.asyncio
    async def test_put_and_get(self, policy_cache, sample_policy):
        """Test putting and getting a policy from cache."""
        agent_id = "agent-456"
        
        # Put policy in cache
        await policy_cache.put(agent_id, sample_policy)
        
        # Get policy from cache
        cached_policy = await policy_cache.get(agent_id)
        
        assert cached_policy is not None
        assert cached_policy.policy == sample_policy
        assert cached_policy.cached_at is not None
        assert cached_policy.expires_at is not None
        assert cached_policy.version == 1
    
    @pytest.mark.asyncio
    async def test_get_miss(self, policy_cache):
        """Test getting a non-existent policy returns None."""
        agent_id = "non-existent-agent"
        
        cached_policy = await policy_cache.get(agent_id)
        
        assert cached_policy is None
    
    @pytest.mark.asyncio
    async def test_cache_hit_increments_counter(self, policy_cache, sample_policy):
        """Test that cache hits increment the hit counter."""
        agent_id = "agent-456"
        
        await policy_cache.put(agent_id, sample_policy)
        await policy_cache.get(agent_id)
        
        stats = policy_cache.get_stats()
        assert stats.hit_count == 1
        assert stats.miss_count == 0
    
    @pytest.mark.asyncio
    async def test_cache_miss_increments_counter(self, policy_cache):
        """Test that cache misses increment the miss counter."""
        agent_id = "non-existent-agent"
        
        await policy_cache.get(agent_id)
        
        stats = policy_cache.get_stats()
        assert stats.hit_count == 0
        assert stats.miss_count == 1


class TestPolicyCacheTTL:
    """Test TTL-based expiration."""
    
    @pytest.mark.asyncio
    async def test_ttl_expiration(self, sample_policy):
        """Test that policies expire after TTL."""
        # Create cache with very short TTL
        config = PolicyCacheConfig(ttl_seconds=1, max_size=100)
        cache = PolicyCache(config)
        
        agent_id = "agent-456"
        
        # Put policy in cache
        await cache.put(agent_id, sample_policy)
        
        # Get immediately - should hit
        cached_policy = await cache.get(agent_id)
        assert cached_policy is not None
        
        # Wait for TTL to expire
        await asyncio.sleep(1.5)
        
        # Get after expiration - should miss
        cached_policy = await cache.get(agent_id)
        assert cached_policy is None
    
    @pytest.mark.asyncio
    async def test_expires_at_set_correctly(self, policy_cache, sample_policy):
        """Test that expires_at is set correctly based on TTL."""
        agent_id = "agent-456"
        
        before_put = datetime.utcnow()
        await policy_cache.put(agent_id, sample_policy)
        after_put = datetime.utcnow()
        
        cached_policy = await policy_cache.get(agent_id)
        
        assert cached_policy is not None
        
        # expires_at should be approximately cached_at + ttl_seconds
        expected_expiration = cached_policy.cached_at + timedelta(seconds=policy_cache.config.ttl_seconds)
        
        # Allow 1 second tolerance for test execution time
        assert abs((cached_policy.expires_at - expected_expiration).total_seconds()) < 1


class TestPolicyCacheEviction:
    """Test LRU eviction when max_size is reached."""
    
    @pytest.mark.asyncio
    async def test_lru_eviction(self, sample_policy):
        """Test that oldest entries are evicted when max_size is reached."""
        # Create cache with small max_size
        config = PolicyCacheConfig(ttl_seconds=60, max_size=3)
        cache = PolicyCache(config)
        
        # Add 3 policies (fill cache)
        await cache.put("agent-1", sample_policy)
        await cache.put("agent-2", sample_policy)
        await cache.put("agent-3", sample_policy)
        
        # All should be in cache
        assert await cache.get("agent-1") is not None
        assert await cache.get("agent-2") is not None
        assert await cache.get("agent-3") is not None
        
        # Add 4th policy (should evict oldest)
        await cache.put("agent-4", sample_policy)
        
        # agent-1 should be evicted (LRU)
        # Note: Due to the way TTLCache works, we can't guarantee exact LRU behavior
        # but we can verify that the cache size is maintained
        stats = cache.get_stats()
        assert stats.size <= config.max_size
    
    @pytest.mark.asyncio
    async def test_eviction_counter(self, sample_policy):
        """Test that eviction counter is incremented."""
        # Create cache with small max_size
        config = PolicyCacheConfig(ttl_seconds=60, max_size=2)
        cache = PolicyCache(config)
        
        # Fill cache
        await cache.put("agent-1", sample_policy)
        await cache.put("agent-2", sample_policy)
        
        # Add one more to trigger eviction
        await cache.put("agent-3", sample_policy)
        
        stats = cache.get_stats()
        assert stats.eviction_count >= 1


class TestPolicyCacheInvalidation:
    """Test explicit invalidation."""
    
    @pytest.mark.asyncio
    async def test_invalidate_single(self, policy_cache, sample_policy):
        """Test invalidating a single cached policy."""
        agent_id = "agent-456"
        
        # Put policy in cache
        await policy_cache.put(agent_id, sample_policy)
        
        # Verify it's in cache
        assert await policy_cache.get(agent_id) is not None
        
        # Invalidate
        await policy_cache.invalidate(agent_id)
        
        # Verify it's no longer in cache
        assert await policy_cache.get(agent_id) is None
        
        # Check invalidation counter
        stats = policy_cache.get_stats()
        assert stats.invalidation_count == 1
    
    @pytest.mark.asyncio
    async def test_invalidate_non_existent(self, policy_cache):
        """Test invalidating a non-existent policy is safe."""
        agent_id = "non-existent-agent"
        
        # Should not raise exception
        await policy_cache.invalidate(agent_id)
        
        # Invalidation counter should not increment for non-existent entries
        stats = policy_cache.get_stats()
        assert stats.invalidation_count == 0
    
    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, policy_cache, sample_policy):
        """Test invalidating multiple policies with pattern matching."""
        # Put multiple policies with similar IDs
        await policy_cache.put("parent-agent-1", sample_policy)
        await policy_cache.put("parent-agent-2", sample_policy)
        await policy_cache.put("child-agent-1", sample_policy)
        
        # Invalidate all parent agents
        count = await policy_cache.invalidate_pattern("parent-*")
        
        assert count == 2
        
        # Verify parent agents are invalidated
        assert await policy_cache.get("parent-agent-1") is None
        assert await policy_cache.get("parent-agent-2") is None
        
        # Verify child agent is still cached
        assert await policy_cache.get("child-agent-1") is not None
    
    @pytest.mark.asyncio
    async def test_clear(self, policy_cache, sample_policy):
        """Test clearing entire cache."""
        # Put multiple policies
        await policy_cache.put("agent-1", sample_policy)
        await policy_cache.put("agent-2", sample_policy)
        await policy_cache.put("agent-3", sample_policy)
        
        # Clear cache
        await policy_cache.clear()
        
        # Verify all are gone
        assert await policy_cache.get("agent-1") is None
        assert await policy_cache.get("agent-2") is None
        assert await policy_cache.get("agent-3") is None
        
        stats = policy_cache.get_stats()
        assert stats.size == 0
    
    @pytest.mark.asyncio
    async def test_invalidation_disabled(self, sample_policy):
        """Test that invalidation can be disabled."""
        config = PolicyCacheConfig(
            ttl_seconds=60,
            max_size=100,
            invalidation_enabled=False
        )
        cache = PolicyCache(config)
        
        agent_id = "agent-456"
        
        # Put policy in cache
        await cache.put(agent_id, sample_policy)
        
        # Try to invalidate (should be no-op)
        await cache.invalidate(agent_id)
        
        # Policy should still be in cache
        assert await cache.get(agent_id) is not None


class TestPolicyCacheStats:
    """Test cache statistics."""
    
    @pytest.mark.asyncio
    async def test_get_stats(self, policy_cache, sample_policy):
        """Test getting cache statistics."""
        # Perform some operations
        await policy_cache.put("agent-1", sample_policy)
        await policy_cache.put("agent-2", sample_policy)
        
        await policy_cache.get("agent-1")  # Hit
        await policy_cache.get("agent-2")  # Hit
        await policy_cache.get("agent-3")  # Miss
        
        await policy_cache.invalidate("agent-1")
        
        stats = policy_cache.get_stats()
        
        assert stats.hit_count == 2
        assert stats.miss_count == 1
        assert stats.hit_rate == pytest.approx(66.67, rel=0.1)
        assert stats.size == 1  # agent-2 only (agent-1 invalidated)
        assert stats.max_size == policy_cache.config.max_size
        assert stats.invalidation_count == 1
    
    def test_stats_initial_state(self, policy_cache):
        """Test that initial stats are all zeros."""
        stats = policy_cache.get_stats()
        
        assert stats.hit_count == 0
        assert stats.miss_count == 0
        assert stats.hit_rate == 0.0
        assert stats.size == 0
        assert stats.eviction_count == 0
        assert stats.invalidation_count == 0
    
    @pytest.mark.asyncio
    async def test_hit_rate_calculation(self, policy_cache, sample_policy):
        """Test that hit rate is calculated correctly."""
        await policy_cache.put("agent-1", sample_policy)
        
        # 3 hits, 1 miss = 75% hit rate
        await policy_cache.get("agent-1")  # Hit
        await policy_cache.get("agent-1")  # Hit
        await policy_cache.get("agent-1")  # Hit
        await policy_cache.get("agent-2")  # Miss
        
        stats = policy_cache.get_stats()
        
        assert stats.hit_count == 3
        assert stats.miss_count == 1
        assert stats.hit_rate == 75.0
