#!/usr/bin/env python3
"""Simple gateway check script"""
import sys
sys.path.insert(0, '.')

print("Testing gateway imports...")

try:
    from caracal.gateway.proxy import GatewayProxy, GatewayConfig
    print("✓ GatewayProxy imported")
except Exception as e:
    print(f"✗ Failed to import GatewayProxy: {e}")
    sys.exit(1)

try:
    from caracal.gateway.auth import Authenticator
    print("✓ Authenticator imported")
except Exception as e:
    print(f"✗ Failed to import Authenticator: {e}")
    sys.exit(1)

try:
    from caracal.gateway.replay_protection import ReplayProtection
    print("✓ ReplayProtection imported")
except Exception as e:
    print(f"✗ Failed to import ReplayProtection: {e}")
    sys.exit(1)

try:
    from caracal.gateway.cache import PolicyCache
    print("✓ PolicyCache imported")
except Exception as e:
    print(f"✗ Failed to import PolicyCache: {e}")
    sys.exit(1)

print("\n✅ All gateway modules imported successfully!")
print("\nChecking if tests exist...")

import os
test_files = [
    "tests/unit/test_gateway_proxy.py",
    "tests/unit/test_gateway_auth.py",
    "tests/unit/test_gateway_replay_protection.py",
    "tests/unit/test_gateway_cache.py",
    "tests/unit/test_gateway_proxy_cache_integration.py"
]

for test_file in test_files:
    if os.path.exists(test_file):
        print(f"✓ {test_file} exists")
    else:
        print(f"✗ {test_file} NOT FOUND")

print("\n✅ Gateway implementation checkpoint complete!")
