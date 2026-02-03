"""
Policy versioning manager for Caracal Core v0.3.

This module provides the PolicyVersionManager for tracking policy changes
with complete audit trails, including version history, change tracking,
and Kafka event publishing.

Requirements: 5.1, 5.2, 5.3, 5.6, 5.7, 6.1, 6.2, 6.3, 6.4, 6.5
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from caracal.db.models import BudgetPolicy, PolicyVersion as PolicyVersionModel
from caracal.kafka.producer import KafkaEventProducer
from caracal.logging_config import get_logger
from caracal.exceptions import PolicyNotFoundError, InvalidPolicyError

logger = get_logger(__name__)


@dataclass
class PolicyVersion:
    """
    Represents a policy version snapshot.
    
    Attributes:
        version_id: Unique version identifier
        policy_id: Policy this version belongs to
        version_number: Sequential version number
        agent_id: Agent this policy applies to
        limit_amount: Budget limit amount
        time_window: Time window for budget
        window_type: Window type ('rolling' or 'calendar')
        currency: Currency code
        active: Whether policy is active
        delegated_from_agent_id: Optional parent agent ID
        change_type: Type of change ('created', 'modified', 'deactivated')
        changed_by: User/system identifier who made the change
        changed_at: Timestamp of change
        change_reason: Explanation for the change
    """
    version_id: UUID
    policy_id: UUID
    version_number: int
    agent_id: UUID
    limit_amount: Decimal
    time_window: str
    window_type: str
    currency: str
    active: bool
    delegated_from_agent_id: Optional[UUID]
    change_type: str
    changed_by: str
    changed_at: datetime
    change_reason: str


@dataclass
class PolicyVersionDiff:
    """
    Represents differences between two policy versions.
    
    Attributes:
        version1: First policy version
        version2: Second policy version
        changed_fields: Dictionary of field changes (field_name -> (old_value, new_value))
    """
    version1: PolicyVersion
    version2: PolicyVersion
    changed_fields: Dict[str, Tuple[Any, Any]]


class PolicyVersionManager:
    """
    Manages policy version history with complete audit trails.
    
    Tracks all policy changes including creation, modification, and deactivation.
    Publishes policy change events to Kafka for downstream consumers.
    Provides query methods for policy history and point-in-time policy state.
    
    Requirements: 5.1, 5.2, 5.3, 5.6, 5.7, 6.1, 6.2, 6.3, 6.4, 6.5
    """
    
    def __init__(self, db_session: Session, kafka_producer: Optional[KafkaEventProducer] = None):
        """
        Initialize PolicyVersionManager.
        
        Args:
            db_session: SQLAlchemy database session
            kafka_producer: Optional Kafka producer for publishing events
        """
        self.db_session = db_session
        self.kafka_producer = kafka_producer
        logger.info("PolicyVersionManager initialized")
    
    async def create_policy_version(
        self,
        policy: BudgetPolicy,
        changed_by: str,
        change_reason: str,
        change_type: str
    ) -> PolicyVersion:
        """
        Create a new policy version record.
        
        Steps:
        1. Get current version number for policy (or 1 if new)
        2. Increment version number
        3. Create policy_versions record with all policy fields
        4. Store changed_by, changed_at, change_reason
        5. Publish policy change event to Kafka
        6. Return version record
        
        Args:
            policy: BudgetPolicy object to version
            changed_by: User/system identifier making the change
            change_reason: Explanation for the change
            change_type: Type of change ('created', 'modified', 'deactivated')
            
        Returns:
            PolicyVersion object representing the new version
            
        Raises:
            InvalidPolicyError: If change_type is invalid
            
        Requirements: 5.1, 5.3, 6.5
        """
        # Validate change_type
        valid_change_types = ['created', 'modified', 'deactivated']
        if change_type not in valid_change_types:
            raise InvalidPolicyError(
                f"Invalid change_type '{change_type}'. Must be one of: {valid_change_types}"
            )
        
        # Get current version number for this policy
        stmt = select(PolicyVersionModel).where(
            PolicyVersionModel.policy_id == policy.policy_id
        ).order_by(PolicyVersionModel.version_number.desc()).limit(1)
        
        result = self.db_session.execute(stmt)
        latest_version = result.scalar_one_or_none()
        
        # Increment version number (or start at 1)
        version_number = (latest_version.version_number + 1) if latest_version else 1
        
        # Create version record
        version_id = uuid4()
        changed_at = datetime.utcnow()
        
        version_model = PolicyVersionModel(
            version_id=version_id,
            policy_id=policy.policy_id,
            version_number=version_number,
            agent_id=policy.agent_id,
            limit_amount=policy.limit_amount,
            time_window=policy.time_window,
            window_type=getattr(policy, 'window_type', 'calendar'),  # Default to 'calendar' for v0.2 compatibility
            currency=policy.currency,
            active=policy.active,
            delegated_from_agent_id=policy.delegated_from_agent_id,
            change_type=change_type,
            changed_by=changed_by,
            changed_at=changed_at,
            change_reason=change_reason
        )
        
        # Add to session and commit
        self.db_session.add(version_model)
        self.db_session.commit()
        
        logger.info(
            f"Created policy version: version_id={version_id}, policy_id={policy.policy_id}, "
            f"version_number={version_number}, change_type={change_type}, changed_by={changed_by}"
        )
        
        # Publish policy change event to Kafka
        if self.kafka_producer:
            try:
                await self.kafka_producer.publish_policy_change(
                    agent_id=str(policy.agent_id),
                    policy_id=str(policy.policy_id),
                    change_type=change_type,
                    changed_by=changed_by,
                    change_reason=change_reason,
                    metadata={
                        'version_id': str(version_id),
                        'version_number': str(version_number),
                        'limit_amount': str(policy.limit_amount),
                        'time_window': policy.time_window,
                        'window_type': getattr(policy, 'window_type', 'calendar'),
                        'currency': policy.currency,
                        'active': str(policy.active)
                    },
                    timestamp=changed_at
                )
                logger.debug(f"Published policy change event for version {version_id}")
            except Exception as e:
                # Log error but don't fail the operation
                # Event publishing is best-effort
                logger.error(
                    f"Failed to publish policy change event for version {version_id}: {e}",
                    exc_info=True
                )
        
        # Return PolicyVersion dataclass
        return PolicyVersion(
            version_id=version_id,
            policy_id=policy.policy_id,
            version_number=version_number,
            agent_id=policy.agent_id,
            limit_amount=policy.limit_amount,
            time_window=policy.time_window,
            window_type=getattr(policy, 'window_type', 'calendar'),
            currency=policy.currency,
            active=policy.active,
            delegated_from_agent_id=policy.delegated_from_agent_id,
            change_type=change_type,
            changed_by=changed_by,
            changed_at=changed_at,
            change_reason=change_reason
        )
    
    def get_policy_history(self, policy_id: UUID) -> List[PolicyVersion]:
        """
        Get complete policy history.
        
        Returns all versions for a policy in chronological order.
        
        Args:
            policy_id: Policy identifier
            
        Returns:
            List of PolicyVersion objects ordered by version_number ascending
            
        Requirements: 5.6
        """
        stmt = select(PolicyVersionModel).where(
            PolicyVersionModel.policy_id == policy_id
        ).order_by(PolicyVersionModel.version_number.asc())
        
        result = self.db_session.execute(stmt)
        version_models = result.scalars().all()
        
        versions = [
            PolicyVersion(
                version_id=v.version_id,
                policy_id=v.policy_id,
                version_number=v.version_number,
                agent_id=v.agent_id,
                limit_amount=v.limit_amount,
                time_window=v.time_window,
                window_type=v.window_type or 'calendar',
                currency=v.currency,
                active=v.active,
                delegated_from_agent_id=v.delegated_from_agent_id,
                change_type=v.change_type,
                changed_by=v.changed_by,
                changed_at=v.changed_at,
                change_reason=v.change_reason
            )
            for v in version_models
        ]
        
        logger.debug(f"Retrieved {len(versions)} versions for policy {policy_id}")
        
        return versions
    
    def get_policy_at_time(self, policy_id: UUID, timestamp: datetime) -> Optional[PolicyVersion]:
        """
        Get policy version active at a specific time.
        
        Returns the most recent version before or at the given timestamp.
        
        Args:
            policy_id: Policy identifier
            timestamp: Point in time to query
            
        Returns:
            PolicyVersion object if found, None otherwise
            
        Requirements: 5.7
        """
        stmt = select(PolicyVersionModel).where(
            and_(
                PolicyVersionModel.policy_id == policy_id,
                PolicyVersionModel.changed_at <= timestamp
            )
        ).order_by(PolicyVersionModel.changed_at.desc()).limit(1)
        
        result = self.db_session.execute(stmt)
        version_model = result.scalar_one_or_none()
        
        if version_model is None:
            logger.debug(f"No policy version found for policy {policy_id} at time {timestamp}")
            return None
        
        version = PolicyVersion(
            version_id=version_model.version_id,
            policy_id=version_model.policy_id,
            version_number=version_model.version_number,
            agent_id=version_model.agent_id,
            limit_amount=version_model.limit_amount,
            time_window=version_model.time_window,
            window_type=version_model.window_type or 'calendar',
            currency=version_model.currency,
            active=version_model.active,
            delegated_from_agent_id=version_model.delegated_from_agent_id,
            change_type=version_model.change_type,
            changed_by=version_model.changed_by,
            changed_at=version_model.changed_at,
            change_reason=version_model.change_reason
        )
        
        logger.debug(
            f"Found policy version {version.version_id} (v{version.version_number}) "
            f"for policy {policy_id} at time {timestamp}"
        )
        
        return version
    
    def compare_versions(self, version1_id: UUID, version2_id: UUID) -> PolicyVersionDiff:
        """
        Compare two policy versions.
        
        Identifies all fields that changed between two versions.
        
        Args:
            version1_id: First version identifier
            version2_id: Second version identifier
            
        Returns:
            PolicyVersionDiff object with changed fields
            
        Raises:
            PolicyNotFoundError: If either version is not found
            
        Requirements: 5.6
        """
        # Load both versions
        stmt1 = select(PolicyVersionModel).where(PolicyVersionModel.version_id == version1_id)
        stmt2 = select(PolicyVersionModel).where(PolicyVersionModel.version_id == version2_id)
        
        result1 = self.db_session.execute(stmt1)
        result2 = self.db_session.execute(stmt2)
        
        version1_model = result1.scalar_one_or_none()
        version2_model = result2.scalar_one_or_none()
        
        if version1_model is None:
            raise PolicyNotFoundError(f"Policy version {version1_id} not found")
        if version2_model is None:
            raise PolicyNotFoundError(f"Policy version {version2_id} not found")
        
        # Convert to dataclasses
        version1 = PolicyVersion(
            version_id=version1_model.version_id,
            policy_id=version1_model.policy_id,
            version_number=version1_model.version_number,
            agent_id=version1_model.agent_id,
            limit_amount=version1_model.limit_amount,
            time_window=version1_model.time_window,
            window_type=version1_model.window_type or 'calendar',
            currency=version1_model.currency,
            active=version1_model.active,
            delegated_from_agent_id=version1_model.delegated_from_agent_id,
            change_type=version1_model.change_type,
            changed_by=version1_model.changed_by,
            changed_at=version1_model.changed_at,
            change_reason=version1_model.change_reason
        )
        
        version2 = PolicyVersion(
            version_id=version2_model.version_id,
            policy_id=version2_model.policy_id,
            version_number=version2_model.version_number,
            agent_id=version2_model.agent_id,
            limit_amount=version2_model.limit_amount,
            time_window=version2_model.time_window,
            window_type=version2_model.window_type or 'calendar',
            currency=version2_model.currency,
            active=version2_model.active,
            delegated_from_agent_id=version2_model.delegated_from_agent_id,
            change_type=version2_model.change_type,
            changed_by=version2_model.changed_by,
            changed_at=version2_model.changed_at,
            change_reason=version2_model.change_reason
        )
        
        # Compare fields
        changed_fields = {}
        
        # Compare policy fields (not metadata fields like changed_by, changed_at)
        comparable_fields = [
            'limit_amount', 'time_window', 'window_type', 'currency',
            'active', 'delegated_from_agent_id'
        ]
        
        for field in comparable_fields:
            value1 = getattr(version1, field)
            value2 = getattr(version2, field)
            
            if value1 != value2:
                changed_fields[field] = (value1, value2)
        
        logger.debug(
            f"Compared versions {version1_id} and {version2_id}: "
            f"{len(changed_fields)} fields changed"
        )
        
        return PolicyVersionDiff(
            version1=version1,
            version2=version2,
            changed_fields=changed_fields
        )
