"""
Gateway proxy module for Caracal Core v0.2.

This module provides network-enforced policy enforcement through:
- Authentication (mTLS, JWT, API keys)
- Request interception and forwarding
- Policy evaluation before API calls
- Replay protection
- Policy caching for degraded mode operation
"""

from caracal.gateway.auth import Authenticator, AuthenticationMethod
from caracal.gateway.replay_protection import (
    ReplayProtection,
    ReplayProtectionConfig,
    ReplayCheckResult,
)
from caracal.gateway.cache import (
    PolicyCache,
    PolicyCacheConfig,
    CachedPolicy,
    CacheStats,
)
from caracal.gateway.proxy import GatewayProxy, GatewayConfig

__all__ = [
    "Authenticator",
    "AuthenticationMethod",
    "ReplayProtection",
    "ReplayProtectionConfig",
    "ReplayCheckResult",
    "PolicyCache",
    "PolicyCacheConfig",
    "CachedPolicy",
    "CacheStats",
    "GatewayProxy",
    "GatewayConfig",
]
