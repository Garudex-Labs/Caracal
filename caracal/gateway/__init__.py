"""
Gateway proxy module for Caracal Core v0.2.

This module provides network-enforced policy enforcement through:
- Authentication (mTLS, JWT, API keys)
- Request interception and forwarding
- Policy evaluation before API calls
- Replay protection
- Policy caching for degraded mode operation

Authority Enforcement (v0.5+):
- Pre-execution authority validation
- Mandate-based access control
- Gateway proxy for request interception
- Decorator and middleware patterns
- External API adapters
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
from caracal.gateway.authority_proxy import (
    AuthorityGatewayProxy,
    require_authority,
    AuthorityMiddleware,
    AuthorityAdapter,
    OpenAIAdapter,
    AnthropicAdapter,
    Request,
    Response,
)

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
    # Authority enforcement
    "AuthorityGatewayProxy",
    "require_authority",
    "AuthorityMiddleware",
    "AuthorityAdapter",
    "OpenAIAdapter",
    "AnthropicAdapter",
    "Request",
    "Response",
]
