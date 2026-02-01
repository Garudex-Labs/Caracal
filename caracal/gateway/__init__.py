"""
Gateway proxy module for Caracal Core v0.2.

This module provides network-enforced policy enforcement through:
- Authentication (mTLS, JWT, API keys)
- Request interception and forwarding
- Policy evaluation before API calls
- Replay protection
"""

from caracal.gateway.auth import Authenticator, AuthenticationMethod
from caracal.gateway.replay_protection import (
    ReplayProtection,
    ReplayProtectionConfig,
    ReplayCheckResult,
)

__all__ = [
    "Authenticator",
    "AuthenticationMethod",
    "ReplayProtection",
    "ReplayProtectionConfig",
    "ReplayCheckResult",
]
