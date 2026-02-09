"""
Compatibility layer for budget-to-authority translation.

This module provides backward compatibility with the v0.2 budget enforcement
system by translating budget check requests to authority check requests.

Requirements: 16.1, 16.2
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from caracal.core.authority import AuthorityEvaluator, AuthorityDecision
from caracal.core.mandate import MandateManager
from caracal.db.models import ExecutionMandate
from caracal.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class BudgetCheckRequest:
    """
    Budget check request structure (v0.2 format).
    
    Represents a request to check if an agent can afford an action.
    """
    agent_id: UUID
    estimated_cost: float
    action: str
    resource: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class BudgetCheckResponse:
    """
    Budget check response structure (v0.2 format).
    
    Represents the result of a budget check.
    """
    allowed: bool
    reason: str
    remaining_budget: Optional[float] = None
    deprecation_warning: Optional[str] = None


class CompatibilityLayer:
    """
    Compatibility layer for budget-to-authority translation.
    
    Translates budget enforcement concepts to authority enforcement concepts
    to maintain backward compatibility during migration.
    
    Supports dual-mode operation where both budget policies and authority
    policies can coexist.
    
    Requirements: 16.1, 16.2, 16.3, 16.7
    """
    
    def __init__(
        self,
        db_session: Session,
        authority_evaluator: AuthorityEvaluator,
        mandate_manager: MandateManager,
        compatibility_logging_enabled: bool = True,
        authority_enforcement_enabled: bool = False,
        rollback_to_budget_mode: bool = False
    ):
        """
        Initialize CompatibilityLayer.
        
        Args:
            db_session: SQLAlchemy database session
            authority_evaluator: AuthorityEvaluator instance for validation
            mandate_manager: MandateManager instance for mandate operations
            compatibility_logging_enabled: Enable compatibility mode logging
            authority_enforcement_enabled: Enable authority enforcement mode
            rollback_to_budget_mode: Rollback to budget enforcement mode
        """
        self.db_session = db_session
        self.authority_evaluator = authority_evaluator
        self.mandate_manager = mandate_manager
        self.compatibility_logging_enabled = compatibility_logging_enabled
        self.authority_enforcement_enabled = authority_enforcement_enabled
        self.rollback_to_budget_mode = rollback_to_budget_mode
        
        # Determine operational mode
        if rollback_to_budget_mode:
            self.mode = "budget"
            logger.warning("CompatibilityLayer initialized in BUDGET MODE (rollback)")
        elif authority_enforcement_enabled:
            self.mode = "authority"
            logger.info("CompatibilityLayer initialized in AUTHORITY MODE")
        else:
            self.mode = "dual"
            logger.info("CompatibilityLayer initialized in DUAL MODE")
    
    def get_operational_mode(self) -> str:
        """
        Get current operational mode.
        
        Returns:
            "budget", "authority", or "dual"
        """
        return self.mode
    
    def should_use_authority_enforcement(self, principal_id: Optional[UUID] = None) -> bool:
        """
        Determine if authority enforcement should be used.
        
        Args:
            principal_id: Optional principal ID for per-principal rollout
        
        Returns:
            True if authority enforcement should be used, False otherwise
        """
        # If rollback flag is set, always use budget mode
        if self.rollback_to_budget_mode:
            return False
        
        # If authority enforcement is globally enabled, use it
        if self.authority_enforcement_enabled:
            return True
        
        # Otherwise, use budget mode
        return False
    
    def translate_budget_check(
        self,
        budget_request: BudgetCheckRequest
    ) -> BudgetCheckResponse:
        """
        Translate budget check request to authority check.
        
        Converts a budget check request (v0.2 format) to an authority check
        by mapping agent_id to principal_id and estimated_cost to resource scope.
        
        Requirements: 16.1
        
        Args:
            budget_request: Budget check request in v0.2 format
        
        Returns:
            BudgetCheckResponse with allow/deny decision and deprecation warning
        """
        if self.compatibility_logging_enabled:
            logger.info(
                f"Translating budget check for agent {budget_request.agent_id}, "
                f"action={budget_request.action}, resource={budget_request.resource}"
            )
        
        try:
            # Map agent_id to principal_id
            principal_id = budget_request.agent_id
            
            # Find an active mandate for this principal
            mandate = self._find_active_mandate(
                principal_id=principal_id,
                action=budget_request.action,
                resource=budget_request.resource
            )
            
            if mandate is None:
                if self.compatibility_logging_enabled:
                    logger.warning(
                        f"No active mandate found for principal {principal_id}, "
                        f"action={budget_request.action}, resource={budget_request.resource}"
                    )
                return BudgetCheckResponse(
                    allowed=False,
                    reason="No active mandate found for requested action and resource",
                    remaining_budget=None,
                    deprecation_warning=self._get_deprecation_warning()
                )
            
            # Validate mandate using authority evaluator
            decision = self.authority_evaluator.validate_mandate(
                mandate=mandate,
                requested_action=budget_request.action,
                requested_resource=budget_request.resource,
                current_time=datetime.utcnow()
            )
            
            # Translate authority decision to budget check response
            response = BudgetCheckResponse(
                allowed=decision.allowed,
                reason=decision.reason,
                remaining_budget=None,  # Not applicable in authority model
                deprecation_warning=self._get_deprecation_warning()
            )
            
            if self.compatibility_logging_enabled:
                logger.info(
                    f"Budget check translated: allowed={response.allowed}, "
                    f"reason={response.reason}"
                )
            
            return response
            
        except Exception as e:
            logger.error(
                f"Failed to translate budget check for agent {budget_request.agent_id}: {e}",
                exc_info=True
            )
            # Fail-closed: deny on error
            return BudgetCheckResponse(
                allowed=False,
                reason=f"Error during budget check translation: {str(e)}",
                remaining_budget=None,
                deprecation_warning=self._get_deprecation_warning()
            )
    
    def _find_active_mandate(
        self,
        principal_id: UUID,
        action: str,
        resource: str
    ) -> Optional[ExecutionMandate]:
        """
        Find an active mandate for the given principal, action, and resource.
        
        Args:
            principal_id: The principal ID to find mandate for
            action: The requested action
            resource: The requested resource
        
        Returns:
            ExecutionMandate if found and valid, None otherwise
        """
        try:
            # Query for mandates that:
            # 1. Belong to the principal
            # 2. Are not revoked
            # 3. Are currently valid (not expired)
            current_time = datetime.utcnow()
            
            mandates = self.db_session.query(ExecutionMandate).filter(
                ExecutionMandate.subject_id == principal_id,
                ExecutionMandate.revoked == False,
                ExecutionMandate.valid_from <= current_time,
                ExecutionMandate.valid_until >= current_time
            ).all()
            
            # Find a mandate that covers the requested action and resource
            for mandate in mandates:
                if self._mandate_covers_request(mandate, action, resource):
                    return mandate
            
            return None
            
        except Exception as e:
            logger.error(
                f"Failed to find active mandate for principal {principal_id}: {e}",
                exc_info=True
            )
            return None
    
    def _mandate_covers_request(
        self,
        mandate: ExecutionMandate,
        action: str,
        resource: str
    ) -> bool:
        """
        Check if mandate covers the requested action and resource.
        
        Args:
            mandate: The mandate to check
            action: The requested action
            resource: The requested resource
        
        Returns:
            True if mandate covers the request, False otherwise
        """
        # Check if action is in mandate's action scope
        if action not in mandate.action_scope:
            return False
        
        # Check if resource matches any pattern in mandate's resource scope
        for pattern in mandate.resource_scope:
            if self._match_pattern(resource, pattern):
                return True
        
        return False
    
    def _match_pattern(self, value: str, pattern: str) -> bool:
        """
        Check if value matches pattern (supports wildcards).
        
        Args:
            value: The value to match
            pattern: The pattern to match against (supports * wildcard)
        
        Returns:
            True if value matches pattern, False otherwise
        """
        import re
        
        # Convert glob pattern to regex
        regex_pattern = pattern.replace("*", ".*")
        regex_pattern = f"^{regex_pattern}$"
        
        try:
            return bool(re.match(regex_pattern, value))
        except Exception as e:
            logger.error(f"Failed to match pattern {pattern}: {e}")
            return False
    
    def _get_deprecation_warning(self) -> str:
        """
        Get deprecation warning message for budget-focused endpoints.
        
        Returns:
            Deprecation warning message
        """
        return (
            "DEPRECATION WARNING: Budget-focused endpoints are deprecated. "
            "Please migrate to authority-focused endpoints. "
            "See documentation for migration guide."
        )
    
    def maintain_budget_endpoints(self) -> Dict[str, str]:
        """
        Get information about maintained budget endpoints.
        
        Returns a dictionary mapping old endpoint paths to their status
        and recommended replacements.
        
        Requirements: 16.2, 16.6
        
        Returns:
            Dictionary with endpoint information
        """
        return {
            "/budget/check": {
                "status": "deprecated",
                "replacement": "/authority/validate",
                "message": "Use /authority/validate with execution mandate instead"
            },
            "/budget/policy": {
                "status": "deprecated",
                "replacement": "/authority/policy",
                "message": "Use /authority/policy to manage authority policies"
            }
        }
    
    def enable_rollback_to_budget_mode(self) -> None:
        """
        Enable rollback to budget enforcement mode.
        
        Disables authority enforcement and re-enables budget enforcement.
        Logs rollback action for audit trail.
        
        Requirements: 16.9
        """
        self.rollback_to_budget_mode = True
        self.mode = "budget"
        logger.warning(
            "ROLLBACK: Authority enforcement disabled, budget enforcement re-enabled"
        )
        
        if self.compatibility_logging_enabled:
            logger.info("Rollback to budget mode completed")
    
    def disable_rollback(self) -> None:
        """
        Disable rollback mode and restore authority enforcement.
        
        Re-enables authority enforcement if it was previously enabled.
        Logs restoration action for audit trail.
        
        Requirements: 16.9
        """
        self.rollback_to_budget_mode = False
        
        if self.authority_enforcement_enabled:
            self.mode = "authority"
            logger.info(
                "RESTORE: Rollback disabled, authority enforcement re-enabled"
            )
        else:
            self.mode = "dual"
            logger.info(
                "RESTORE: Rollback disabled, dual mode re-enabled"
            )
        
        if self.compatibility_logging_enabled:
            logger.info("Rollback disabled, normal operation restored")
