"""
Mandate management for authority enforcement.

This module provides the MandateManager class for managing execution mandate
lifecycle including issuance, revocation, and delegation.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.9, 5.10, 7.1, 7.2, 7.3, 7.4,
7.5, 7.7, 7.8, 7.9, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from caracal.core.crypto import sign_mandate
from caracal.core.intent import Intent
from caracal.db.models import ExecutionMandate, AuthorityPolicy, Principal
from caracal.logging_config import get_logger

logger = get_logger(__name__)


class MandateManager:
    """
    Manages execution mandate lifecycle.
    
    Handles mandate issuance, revocation, and delegation with validation
    against authority policies and fail-closed semantics.
    
    Requirements: 5.1, 5.2, 5.3
    """
    
    def __init__(self, db_session: Session, ledger_writer=None):
        """
        Initialize MandateManager.
        
        Args:
            db_session: SQLAlchemy database session
            ledger_writer: AuthorityLedgerWriter instance (optional, for recording events)
        """
        self.db_session = db_session
        self.ledger_writer = ledger_writer
        logger.info("MandateManager initialized")
    
    def _get_active_policy(self, principal_id: UUID) -> Optional[AuthorityPolicy]:
        """
        Get active authority policy for a principal.
        
        Args:
            principal_id: The principal ID to get policy for
        
        Returns:
            AuthorityPolicy if found and active, None otherwise
        """
        try:
            policy = self.db_session.query(AuthorityPolicy).filter(
                AuthorityPolicy.principal_id == principal_id,
                AuthorityPolicy.active == True
            ).first()
            
            return policy
        except Exception as e:
            logger.error(f"Failed to get active policy for principal {principal_id}: {e}", exc_info=True)
            return None
    
    def _get_principal(self, principal_id: UUID) -> Optional[Principal]:
        """
        Get principal by ID.
        
        Args:
            principal_id: The principal ID to get
        
        Returns:
            Principal if found, None otherwise
        """
        try:
            principal = self.db_session.query(Principal).filter(
                Principal.principal_id == principal_id
            ).first()
            
            return principal
        except Exception as e:
            logger.error(f"Failed to get principal {principal_id}: {e}", exc_info=True)
            return None
    
    def _validate_scope_subset(
        self,
        child_scope: List[str],
        parent_scope: List[str]
    ) -> bool:
        """
        Validate that child scope is a subset of parent scope.
        
        Args:
            child_scope: The child scope to validate
            parent_scope: The parent scope to validate against
        
        Returns:
            True if child is subset of parent, False otherwise
        """
        # Every item in child_scope must match at least one pattern in parent_scope
        for child_item in child_scope:
            match_found = False
            for parent_item in parent_scope:
                if self._match_pattern(child_item, parent_item):
                    match_found = True
                    break
            
            if not match_found:
                return False
        
        return True
    
    def _match_pattern(self, value: str, pattern: str) -> bool:
        """
        Check if value matches pattern (supports wildcards).
        
        Args:
            value: The value to match
            pattern: The pattern to match against (supports * wildcard)
        
        Returns:
            True if value matches pattern, False otherwise
        """
        # Exact match
        if value == pattern:
            return True
        
        # Wildcard match
        if '*' in pattern:
            import re
            regex_pattern = pattern.replace('*', '.*')
            regex_pattern = f"^{regex_pattern}$"
            if re.match(regex_pattern, value):
                return True
        
        return False
    
    def _record_ledger_event(
        self,
        event_type: str,
        principal_id: UUID,
        mandate_id: Optional[UUID] = None,
        decision: Optional[str] = None,
        denial_reason: Optional[str] = None,
        requested_action: Optional[str] = None,
        requested_resource: Optional[str] = None,
        metadata: Optional[dict] = None
    ):
        """
        Record an authority ledger event.
        
        Args:
            event_type: Type of event (issued, validated, denied, revoked)
            principal_id: Principal ID associated with the event
            mandate_id: Mandate ID if applicable
            decision: Decision outcome (allowed/denied) for validation events
            denial_reason: Reason for denial if applicable
            requested_action: Requested action for validation events
            requested_resource: Requested resource for validation events
            metadata: Additional metadata
        """
        if self.ledger_writer:
            try:
                if event_type == "issued":
                    self.ledger_writer.record_issuance(
                        mandate_id=mandate_id,
                        principal_id=principal_id,
                        metadata=metadata
                    )
                elif event_type == "revoked":
                    self.ledger_writer.record_revocation(
                        mandate_id=mandate_id,
                        principal_id=principal_id,
                        reason=denial_reason,
                        metadata=metadata
                    )
                else:
                    logger.warning(f"Unknown event type for ledger recording: {event_type}")
            except Exception as e:
                logger.error(f"Failed to record ledger event: {e}", exc_info=True)
        else:
            logger.debug(f"No ledger writer configured, skipping event recording for {event_type}")

