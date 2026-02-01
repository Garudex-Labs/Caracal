"""
Policy Cache for Gateway Proxy degraded mode operation.

Provides in-memory caching of policies with TTL-based expiration and
explicit invalidation for operation during policy service outages.

Requirements: 1.8, 16.1, 16.2, 16.3, 16.4
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional
from uuid import UUID

from cachetools import TTLCache

from caracal.core.policy import BudgetPolicy
from caracal.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class CachedPolicy:
    """
    Represents a cached policy with metadata.
    
    Attributes:
        policy: The BudgetPolicy being cached
        cached_at: Timestamp when policy was cached
        expires_at: Timestamp when cache entry expires
        version: Version number for optimistic locking (future use)
    """
    policy: BudgetPolicy
    cached_at: datetime
    expires_at: datetime
    version: int = 1


@dataclass
class PolicyCacheConfig:
    """
    Configuration for PolicyCache.
    
    Attributes:
        ttl_seconds: Time-to-live for cached entries (default 60s)
        max_size: Maximum number of cached policies (default 10000)
        eviction_policy: Eviction strategy (default "LRU")
        invalidation_enabled: Enable explicit invalidation (default True)
    """
    ttl_seconds: int = 60
    max_size: int = 10000
    eviction_policy: str = "LRU"
    invalidation_enabled: bool = True


@dataclass
class CacheStats:
    """
    Cache statistics for monitoring.
    
    Attributes:
        hit_count: Total cache hits
        miss_count: Total cache misses
        hit_rate: Percentage of hits (hits / (hits + misses))
        size: Current number of cached entries
        max_size: Maximum cache capacity
        eviction_count: Total evictions due to size limit
        invalidation_count: Total explicit invalidations
    """
    hit_count: int
    miss_count: int
    hit_rate: float
    size: int
    max_size: int
    eviction_count: int
    invalidation_count: int


class PolicyCache:
    """
    In-memory cache for policies with TTL and LRU eviction.
    
    Provides caching for gateway proxy degraded mode operation when
    policy service is unavailable. Implements TTL-based expiration
    and explicit invalidation for consistency.
    
    Requirements: 1.8, 16.1, 16.2, 16.3, 16.4
    """
    
    def __init__(self, config: PolicyCacheConfig):
        """
        Initialize PolicyCache with configuration.
        
        Args:
            config: PolicyCacheConfig with TTL, max size, etc.
        """
        self.config = config
        
        # Use cachetools TTLCache for automatic TTL-based eviction
        # TTLCache provides LRU eviction when max_size is reached
        self._cache: TTLCache = TTLCache(
            maxsize=config.max_size,
            ttl=config.ttl_seconds
        )
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        # Statistics for monitoring
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._invalidations = 0
        
        logger.info(
            f"Initialized PolicyCache: ttl={config.ttl_seconds}s, "
            f"max_size={config.max_size}, eviction={config.eviction_policy}"
        )
    
    async def get(self, agent_id: str) -> Optional[CachedPolicy]:
        """
        Get cached policy for agent.
        
        Args:
            agent_id: Agent identifier (UUID as string)
            
        Returns:
            CachedPolicy if in cache and not expired, None otherwise
            
        Behavior:
            - Checks TTL expiration (cached_at + ttl_seconds < now)
            - Returns None for expired entries
            - Increments hit/miss counters for monitoring
            
        Requirements: 16.1, 16.2, 16.5
        """
        async with self._lock:
            if agent_id in self._cache:
                cached_policy = self._cache[agent_id]
                
                # Double-check TTL expiration (defense in depth)
                # TTLCache should handle this, but we verify
                if datetime.utcnow() < cached_policy.expires_at:
                    self._hits += 1
                    cache_age_seconds = (datetime.utcnow() - cached_policy.cached_at).total_seconds()
                    logger.debug(
                        f"Cache hit for agent {agent_id}, "
                        f"age={cache_age_seconds:.1f}s"
                    )
                    return cached_policy
                else:
                    # Expired entry, remove it
                    del self._cache[agent_id]
                    self._misses += 1
                    logger.debug(f"Cache expired for agent {agent_id}")
                    return None
            else:
                self._misses += 1
                logger.debug(f"Cache miss for agent {agent_id}")
                return None
    
    async def put(self, agent_id: str, policy: BudgetPolicy) -> None:
        """
        Cache policy for agent with automatic TTL.
        
        Args:
            agent_id: Agent identifier (UUID as string)
            policy: BudgetPolicy to cache
            
        Behavior:
            - Sets cached_at = now()
            - Sets expires_at = now() + ttl_seconds
            - Evicts oldest entries if max_size exceeded (LRU)
            - Increments cache write counter
            
        Requirements: 16.1, 16.2, 16.5, 16.7
        """
        async with self._lock:
            now = datetime.utcnow()
            cached_policy = CachedPolicy(
                policy=policy,
                cached_at=now,
                expires_at=now + timedelta(seconds=self.config.ttl_seconds),
                version=1
            )
            
            # Check if we'll exceed max_size (for eviction tracking)
            if len(self._cache) >= self.config.max_size and agent_id not in self._cache:
                self._evictions += 1
                logger.debug(
                    f"Cache eviction triggered (size={len(self._cache)}, "
                    f"max={self.config.max_size})"
                )
            
            self._cache[agent_id] = cached_policy
            logger.debug(
                f"Cached policy for agent {agent_id}, "
                f"expires at {cached_policy.expires_at}"
            )
    
    async def invalidate(self, agent_id: str) -> None:
        """
        Explicitly invalidate cached policy for agent.
        
        Use cases:
            - Policy updated via admin CLI
            - Policy deactivated
            - Agent deleted
        
        Args:
            agent_id: Agent identifier (UUID as string)
            
        Behavior:
            - Removes entry from cache immediately
            - Idempotent (safe to call multiple times)
            - Logs invalidation event
            
        Requirements: 16.8, 16.9
        """
        if not self.config.invalidation_enabled:
            logger.debug(f"Invalidation disabled, skipping for agent {agent_id}")
            return
        
        async with self._lock:
            if agent_id in self._cache:
                del self._cache[agent_id]
                self._invalidations += 1
                logger.info(f"Invalidated cache for agent {agent_id}")
            else:
                logger.debug(f"Cache invalidation called for non-cached agent {agent_id}")
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate multiple cached policies matching pattern.
        
        Args:
            pattern: Glob pattern for agent IDs (e.g., "parent-*")
        
        Returns:
            Count of invalidated entries
        
        Use cases:
            - Invalidate all child agents when parent policy changes
            - Bulk invalidation during maintenance
            
        Requirements: 16.8, 16.9
        """
        if not self.config.invalidation_enabled:
            logger.debug(f"Invalidation disabled, skipping pattern {pattern}")
            return 0
        
        import fnmatch
        
        async with self._lock:
            matching_keys = [
                key for key in self._cache.keys()
                if fnmatch.fnmatch(key, pattern)
            ]
            
            for key in matching_keys:
                del self._cache[key]
                self._invalidations += 1
            
            if matching_keys:
                logger.info(
                    f"Invalidated {len(matching_keys)} cache entries "
                    f"matching pattern '{pattern}'"
                )
            
            return len(matching_keys)
    
    async def clear(self) -> None:
        """
        Clear entire cache.
        
        Use cases:
            - System maintenance
            - Cache corruption recovery
            - Configuration changes requiring full refresh
        """
        async with self._lock:
            size_before = len(self._cache)
            self._cache.clear()
            logger.info(f"Cleared entire cache ({size_before} entries)")
    
    def get_stats(self) -> CacheStats:
        """
        Get cache statistics for monitoring.
        
        Returns:
            CacheStats with hit/miss counts, hit rate, size, evictions, etc.
            
        Requirements: 16.10
        """
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0
        
        return CacheStats(
            hit_count=self._hits,
            miss_count=self._misses,
            hit_rate=hit_rate,
            size=len(self._cache),
            max_size=self.config.max_size,
            eviction_count=self._evictions,
            invalidation_count=self._invalidations
        )
