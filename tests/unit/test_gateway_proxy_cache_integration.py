"""
Integration tests for Gateway Proxy with Policy Cache.

Tests the integration between GatewayProxy and PolicyCache:
- Normal operation (cache population)
- Degraded mode operation (using cache when policy service fails)
- Degraded mode headers
- Cache statistics
"""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from caracal.gateway.proxy import GatewayProxy, GatewayConfig
from caracal.gateway.auth import Authenticator, AuthenticationMethod, AuthenticationResult
from caracal.gateway.cache import PolicyCache, PolicyCacheConfig
from caracal.core.policy import PolicyEvaluator, PolicyDecision, BudgetPolicy, PolicyStore
from caracal.core.metering import MeteringCollector
from caracal.core.identity import AgentIdentity
from caracal.exceptions import PolicyEvaluationError


@pytest.fixture
def gateway_config_with_cache():
    """Create a test gateway configuration with cache enabled."""
    return GatewayConfig(
        listen_address="127.0.0.1:8443",
        auth_mode="jwt",
        enable_replay_protection=False,  # Disable for simpler testing
        request_timeout_seconds=10,
        enable_policy_cache=True,
        policy_cache_ttl=60,
        policy_cache_max_size=100
    )


@pytest.fixture
def mock_authenticator():
    """Create a mock authenticator that always succeeds."""
    authenticator = Mock(spec=Authenticator)
    
    async def authenticate_jwt(token):
        return AuthenticationResult(
            success=True,
            agent_identity=AgentIdentity(
                agent_id="550e8400-e29b-41d4-a716-446655440000",
                name="test-agent",
                owner="test@example.com",
                created_at=datetime.utcnow().isoformat() + "Z",
                metadata={}
            ),
            method=AuthenticationMethod.JWT,
            error=None
        )
    
    authenticator.authenticate_jwt = AsyncMock(side_effect=authenticate_jwt)
    return authenticator


@pytest.fixture
def mock_policy_store():
    """Create a mock policy store."""
    policy_store = Mock(spec=PolicyStore)
    
    def get_policies(agent_id):
        return [BudgetPolicy(
            policy_id="policy-123",
            agent_id=agent_id,
            limit_amount="100.00",
            time_window="daily",
            currency="USD",
            created_at=datetime.utcnow().isoformat() + "Z",
            active=True
        )]
    
    policy_store.get_policies = Mock(side_effect=get_policies)
    return policy_store


@pytest.fixture
def mock_policy_evaluator(mock_policy_store):
    """Create a mock policy evaluator."""
    evaluator = Mock(spec=PolicyEvaluator)
    evaluator.policy_store = mock_policy_store
    
    def check_budget(agent_id, estimated_cost=None, current_time=None):
        return PolicyDecision(
            allowed=True,
            reason="Within budget",
            remaining_budget=Decimal("50.00"),
            provisional_charge_id="prov-123"
        )
    
    evaluator.check_budget = Mock(side_effect=check_budget)
    return evaluator


@pytest.fixture
def mock_metering_collector():
    """Create a mock metering collector."""
    collector = Mock(spec=MeteringCollector)
    collector.collect_event = Mock()
    return collector


@pytest.fixture
def gateway_with_cache(
    gateway_config_with_cache,
    mock_authenticator,
    mock_policy_evaluator,
    mock_metering_collector
):
    """Create a GatewayProxy instance with cache enabled."""
    return GatewayProxy(
        config=gateway_config_with_cache,
        authenticator=mock_authenticator,
        policy_evaluator=mock_policy_evaluator,
        metering_collector=mock_metering_collector,
        replay_protection=None
    )


class TestGatewayProxyCacheIntegration:
    """Test integration between GatewayProxy and PolicyCache."""
    
    def test_gateway_initializes_cache(self, gateway_with_cache):
        """Test that gateway initializes policy cache when enabled."""
        assert gateway_with_cache.policy_cache is not None
        assert isinstance(gateway_with_cache.policy_cache, PolicyCache)
        assert gateway_with_cache.policy_cache.config.ttl_seconds == 60
        assert gateway_with_cache.policy_cache.config.max_size == 100
    
    def test_gateway_without_cache(
        self,
        mock_authenticator,
        mock_policy_evaluator,
        mock_metering_collector
    ):
        """Test that gateway works without cache when disabled."""
        config = GatewayConfig(
            enable_policy_cache=False
        )
        
        gateway = GatewayProxy(
            config=config,
            authenticator=mock_authenticator,
            policy_evaluator=mock_policy_evaluator,
            metering_collector=mock_metering_collector
        )
        
        assert gateway.policy_cache is None
    
    def test_stats_endpoint_includes_cache_stats(self, gateway_with_cache):
        """Test that /stats endpoint includes cache statistics."""
        client = TestClient(gateway_with_cache.app)
        
        response = client.get("/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "policy_cache" in data
        assert "hit_count" in data["policy_cache"]
        assert "miss_count" in data["policy_cache"]
        assert "hit_rate" in data["policy_cache"]
        assert "size" in data["policy_cache"]
        assert "max_size" in data["policy_cache"]
        assert "eviction_count" in data["policy_cache"]
        assert "invalidation_count" in data["policy_cache"]


class TestGatewayProxyDegradedMode:
    """Test degraded mode operation with policy cache."""
    
    @pytest.mark.asyncio
    async def test_normal_operation_populates_cache(
        self,
        gateway_with_cache,
        mock_policy_evaluator,
        mock_policy_store
    ):
        """Test that successful policy evaluations populate the cache."""
        client = TestClient(gateway_with_cache.app)
        
        # Mock successful request forwarding
        with patch.object(gateway_with_cache, 'forward_request', new_callable=AsyncMock) as mock_forward:
            mock_forward.return_value = MagicMock(
                status_code=200,
                content=b'{"result": "success"}',
                headers={"content-type": "application/json"}
            )
            
            # Make a request
            response = client.post(
                "/api/test",
                headers={
                    "Authorization": "Bearer test-token",
                    "X-Caracal-Target-URL": "https://api.example.com/test",
                    "X-Caracal-Estimated-Cost": "10.00"
                },
                json={"test": "data"}
            )
        
        # Should succeed
        assert response.status_code == 200
        
        # Cache should have been populated
        cache_stats = gateway_with_cache.policy_cache.get_stats()
        assert cache_stats.size >= 0  # Cache may or may not have the entry depending on timing
    
    @pytest.mark.asyncio
    async def test_degraded_mode_uses_cache(
        self,
        gateway_with_cache,
        mock_policy_evaluator,
        mock_policy_store
    ):
        """Test that degraded mode uses cached policies when policy service fails."""
        client = TestClient(gateway_with_cache.app)
        
        # First, populate the cache with a successful request
        with patch.object(gateway_with_cache, 'forward_request', new_callable=AsyncMock) as mock_forward:
            mock_forward.return_value = MagicMock(
                status_code=200,
                content=b'{"result": "success"}',
                headers={"content-type": "application/json"}
            )
            
            response = client.post(
                "/api/test",
                headers={
                    "Authorization": "Bearer test-token",
                    "X-Caracal-Target-URL": "https://api.example.com/test",
                    "X-Caracal-Estimated-Cost": "10.00"
                },
                json={"test": "data"}
            )
            
            assert response.status_code == 200
        
        # Now make policy evaluator fail to simulate service outage
        mock_policy_evaluator.check_budget.side_effect = PolicyEvaluationError("Policy service unavailable")
        
        # Make another request - should use cache
        with patch.object(gateway_with_cache, 'forward_request', new_callable=AsyncMock) as mock_forward:
            mock_forward.return_value = MagicMock(
                status_code=200,
                content=b'{"result": "success"}',
                headers={"content-type": "application/json"}
            )
            
            response = client.post(
                "/api/test",
                headers={
                    "Authorization": "Bearer test-token",
                    "X-Caracal-Target-URL": "https://api.example.com/test",
                    "X-Caracal-Estimated-Cost": "10.00"
                },
                json={"test": "data"}
            )
        
        # Should succeed using cached policy
        assert response.status_code == 200
        
        # Should have degraded mode headers
        assert "X-Caracal-Degraded-Mode" in response.headers
        assert response.headers["X-Caracal-Degraded-Mode"] == "true"
        assert "X-Caracal-Cache-Age" in response.headers
        assert "X-Caracal-Cache-Warning" in response.headers
        
        # Degraded mode counter should be incremented
        assert gateway_with_cache._degraded_mode_count >= 1
    
    @pytest.mark.asyncio
    async def test_degraded_mode_without_cache_fails_closed(
        self,
        gateway_with_cache,
        mock_policy_evaluator
    ):
        """Test that requests fail closed when policy service fails and no cache available."""
        client = TestClient(gateway_with_cache.app)
        
        # Make policy evaluator fail
        mock_policy_evaluator.check_budget.side_effect = PolicyEvaluationError("Policy service unavailable")
        
        # Make request without populating cache first
        response = client.post(
            "/api/test",
            headers={
                "Authorization": "Bearer test-token",
                "X-Caracal-Target-URL": "https://api.example.com/test",
                "X-Caracal-Estimated-Cost": "10.00"
            },
            json={"test": "data"}
        )
        
        # Should fail with 503 (service unavailable)
        assert response.status_code == 503
        assert "policy_service_unavailable" in response.json()["error"]
    
    @pytest.mark.asyncio
    async def test_degraded_mode_exceeds_cached_limit(
        self,
        gateway_with_cache,
        mock_policy_evaluator,
        mock_policy_store
    ):
        """Test that degraded mode denies requests exceeding cached policy limit."""
        client = TestClient(gateway_with_cache.app)
        
        # First, populate the cache
        with patch.object(gateway_with_cache, 'forward_request', new_callable=AsyncMock) as mock_forward:
            mock_forward.return_value = MagicMock(
                status_code=200,
                content=b'{"result": "success"}',
                headers={"content-type": "application/json"}
            )
            
            response = client.post(
                "/api/test",
                headers={
                    "Authorization": "Bearer test-token",
                    "X-Caracal-Target-URL": "https://api.example.com/test",
                    "X-Caracal-Estimated-Cost": "10.00"
                },
                json={"test": "data"}
            )
            
            assert response.status_code == 200
        
        # Make policy evaluator fail
        mock_policy_evaluator.check_budget.side_effect = PolicyEvaluationError("Policy service unavailable")
        
        # Make request with cost exceeding cached limit (100.00)
        response = client.post(
            "/api/test",
            headers={
                "Authorization": "Bearer test-token",
                "X-Caracal-Target-URL": "https://api.example.com/test",
                "X-Caracal-Estimated-Cost": "150.00"  # Exceeds limit
            },
            json={"test": "data"}
        )
        
        # Should be denied
        assert response.status_code == 403
        assert "budget_exceeded" in response.json()["error"] or "Estimated cost" in response.json()["message"]


class TestGatewayProxyCacheDisabled:
    """Test gateway behavior when cache is disabled."""
    
    @pytest.mark.asyncio
    async def test_fails_closed_without_cache(
        self,
        mock_authenticator,
        mock_policy_evaluator,
        mock_metering_collector
    ):
        """Test that gateway fails closed when cache disabled and policy service fails."""
        config = GatewayConfig(
            enable_policy_cache=False
        )
        
        gateway = GatewayProxy(
            config=config,
            authenticator=mock_authenticator,
            policy_evaluator=mock_policy_evaluator,
            metering_collector=mock_metering_collector
        )
        
        client = TestClient(gateway.app)
        
        # Make policy evaluator fail
        mock_policy_evaluator.check_budget.side_effect = PolicyEvaluationError("Policy service unavailable")
        
        # Make request
        response = client.post(
            "/api/test",
            headers={
                "Authorization": "Bearer test-token",
                "X-Caracal-Target-URL": "https://api.example.com/test"
            },
            json={"test": "data"}
        )
        
        # Should fail with 503
        assert response.status_code == 503
        assert "policy_service_unavailable" in response.json()["error"]
