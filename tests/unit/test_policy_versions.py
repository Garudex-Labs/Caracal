"""
Unit tests for PolicyVersionManager.

Tests policy versioning functionality including version creation,
history queries, and version comparison.

Requirements: 5.1, 5.2, 5.3, 5.6, 5.7, 6.1, 6.2, 6.3, 6.4, 6.5
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from caracal.db.models import Base, BudgetPolicy, AgentIdentity
from caracal.core.policy_versions import PolicyVersionManager, PolicyVersion
from caracal.exceptions import PolicyNotFoundError


@pytest.fixture
def db_session(tmp_path):
    """Create in-memory SQLite database session for testing."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Create in-memory SQLite database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    # Create session
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()


@pytest.fixture
def agent(db_session):
    """Create test agent."""
    agent = AgentIdentity(
        agent_id=uuid4(),
        name="test-agent",
        owner="test-owner"
    )
    db_session.add(agent)
    db_session.commit()
    return agent


@pytest.fixture
def policy(db_session, agent):
    """Create test policy."""
    policy = BudgetPolicy(
        policy_id=uuid4(),
        agent_id=agent.agent_id,
        limit_amount=Decimal("100.00"),
        time_window="daily",
        currency="USD",
        active=True
    )
    # Add window_type attribute for v0.3
    policy.window_type = "calendar"
    
    db_session.add(policy)
    db_session.commit()
    return policy


@pytest.fixture
def version_manager(db_session):
    """Create PolicyVersionManager instance."""
    return PolicyVersionManager(db_session)


class TestPolicyVersionManager:
    """Test suite for PolicyVersionManager."""
    
    @pytest.mark.asyncio
    async def test_create_policy_version(self, version_manager, policy):
        """Test creating a policy version."""
        # Create version
        version = await version_manager.create_policy_version(
            policy=policy,
            changed_by="test-user",
            change_reason="Initial policy creation",
            change_type="created"
        )
        
        # Verify version
        assert version.version_id is not None
        assert version.policy_id == policy.policy_id
        assert version.version_number == 1
        assert version.agent_id == policy.agent_id
        assert version.limit_amount == policy.limit_amount
        assert version.time_window == policy.time_window
        assert version.window_type == "calendar"
        assert version.currency == policy.currency
        assert version.active == policy.active
        assert version.change_type == "created"
        assert version.changed_by == "test-user"
        assert version.change_reason == "Initial policy creation"
    
    @pytest.mark.asyncio
    async def test_create_multiple_versions(self, version_manager, policy):
        """Test creating multiple versions increments version number."""
        # Create first version
        version1 = await version_manager.create_policy_version(
            policy=policy,
            changed_by="test-user",
            change_reason="Initial creation",
            change_type="created"
        )
        assert version1.version_number == 1
        
        # Modify policy
        policy.limit_amount = Decimal("200.00")
        
        # Create second version
        version2 = await version_manager.create_policy_version(
            policy=policy,
            changed_by="test-user",
            change_reason="Increased limit",
            change_type="modified"
        )
        assert version2.version_number == 2
        assert version2.limit_amount == Decimal("200.00")
        
        # Deactivate policy
        policy.active = False
        
        # Create third version
        version3 = await version_manager.create_policy_version(
            policy=policy,
            changed_by="test-user",
            change_reason="Policy deactivated",
            change_type="deactivated"
        )
        assert version3.version_number == 3
        assert version3.active == False
    
    @pytest.mark.asyncio
    async def test_get_policy_history(self, version_manager, policy):
        """Test retrieving policy history."""
        # Create multiple versions
        await version_manager.create_policy_version(
            policy=policy,
            changed_by="user1",
            change_reason="Created",
            change_type="created"
        )
        
        policy.limit_amount = Decimal("200.00")
        await version_manager.create_policy_version(
            policy=policy,
            changed_by="user2",
            change_reason="Modified",
            change_type="modified"
        )
        
        policy.active = False
        await version_manager.create_policy_version(
            policy=policy,
            changed_by="user3",
            change_reason="Deactivated",
            change_type="deactivated"
        )
        
        # Get history
        history = version_manager.get_policy_history(policy.policy_id)
        
        # Verify history
        assert len(history) == 3
        assert history[0].version_number == 1
        assert history[0].change_type == "created"
        assert history[1].version_number == 2
        assert history[1].change_type == "modified"
        assert history[2].version_number == 3
        assert history[2].change_type == "deactivated"
    
    @pytest.mark.asyncio
    async def test_get_policy_at_time(self, version_manager, policy):
        """Test retrieving policy version at specific time."""
        # Create versions at different times
        time1 = datetime.utcnow()
        version1 = await version_manager.create_policy_version(
            policy=policy,
            changed_by="user1",
            change_reason="Created",
            change_type="created"
        )
        
        # Wait a bit and create second version
        time2 = datetime.utcnow() + timedelta(seconds=1)
        policy.limit_amount = Decimal("200.00")
        version2 = await version_manager.create_policy_version(
            policy=policy,
            changed_by="user2",
            change_reason="Modified",
            change_type="modified"
        )
        
        # Query version at time1 (should get version1)
        version_at_time1 = version_manager.get_policy_at_time(
            policy.policy_id,
            time1 + timedelta(milliseconds=500)
        )
        assert version_at_time1 is not None
        assert version_at_time1.version_number == 1
        
        # Query version at time2 (should get version2)
        version_at_time2 = version_manager.get_policy_at_time(
            policy.policy_id,
            time2 + timedelta(milliseconds=500)
        )
        assert version_at_time2 is not None
        assert version_at_time2.version_number == 2
        
        # Query version before any changes (should get None)
        version_before = version_manager.get_policy_at_time(
            policy.policy_id,
            time1 - timedelta(seconds=1)
        )
        assert version_before is None
    
    @pytest.mark.asyncio
    async def test_compare_versions(self, version_manager, policy):
        """Test comparing two policy versions."""
        # Create first version
        version1 = await version_manager.create_policy_version(
            policy=policy,
            changed_by="user1",
            change_reason="Created",
            change_type="created"
        )
        
        # Modify policy
        policy.limit_amount = Decimal("200.00")
        policy.time_window = "weekly"
        
        # Create second version
        version2 = await version_manager.create_policy_version(
            policy=policy,
            changed_by="user2",
            change_reason="Modified",
            change_type="modified"
        )
        
        # Compare versions
        diff = version_manager.compare_versions(
            version1.version_id,
            version2.version_id
        )
        
        # Verify diff
        assert diff.version1.version_id == version1.version_id
        assert diff.version2.version_id == version2.version_id
        assert len(diff.changed_fields) == 2
        assert "limit_amount" in diff.changed_fields
        assert diff.changed_fields["limit_amount"] == (Decimal("100.00"), Decimal("200.00"))
        assert "time_window" in diff.changed_fields
        assert diff.changed_fields["time_window"] == ("daily", "weekly")
    
    @pytest.mark.asyncio
    async def test_compare_versions_not_found(self, version_manager):
        """Test comparing versions when one doesn't exist."""
        with pytest.raises(PolicyNotFoundError):
            version_manager.compare_versions(uuid4(), uuid4())
    
    @pytest.mark.asyncio
    async def test_invalid_change_type(self, version_manager, policy):
        """Test creating version with invalid change type."""
        from caracal.exceptions import InvalidPolicyError
        
        with pytest.raises(InvalidPolicyError):
            await version_manager.create_policy_version(
                policy=policy,
                changed_by="user1",
                change_reason="Test",
                change_type="invalid_type"
            )
