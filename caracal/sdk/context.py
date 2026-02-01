"""
Budget check context manager for Caracal SDK.

Provides a context manager for wrapping agent code with budget checks.
Implements fail-closed semantics: raises BudgetExceededError if budget is exceeded.
"""

from typing import TYPE_CHECKING

from caracal.exceptions import BudgetExceededError, PolicyEvaluationError
from caracal.logging_config import get_logger

if TYPE_CHECKING:
    from caracal.sdk.client import CaracalClient

logger = get_logger(__name__)


class BudgetCheckContext:
    """
    Context manager for budget-checked execution.
    
    Checks budget on context entry and raises BudgetExceededError
    if the agent has exceeded its budget limit.
    
    Implements fail-closed semantics:
    - Raises BudgetExceededError if budget is exceeded
    - Raises BudgetExceededError if policy evaluation fails
    
    Usage:
        >>> client = CaracalClient()
        >>> with client.budget_check(agent_id="my-agent"):
        ...     # Code that incurs costs
        ...     result = call_expensive_api()
    """

    def __init__(self, client: "CaracalClient", agent_id: str):
        """
        Initialize budget check context.
        
        Args:
            client: CaracalClient instance
            agent_id: Agent identifier to check budget for
        """
        self.client = client
        self.agent_id = agent_id

    def __enter__(self):
        """
        Enter context: check budget before allowing execution.
        
        Raises:
            BudgetExceededError: If agent has exceeded budget or check fails
        """
        logger.debug(f"Entering budget check context for agent {self.agent_id}")
        
        try:
            # Check budget using policy evaluator
            decision = self.client.policy_evaluator.check_budget(self.agent_id)
            
            if not decision.allowed:
                # Budget exceeded or denied
                logger.warning(
                    f"Budget check denied for agent {self.agent_id}: {decision.reason}"
                )
                raise BudgetExceededError(
                    f"Budget check failed for agent '{self.agent_id}': {decision.reason}"
                )
            
            # Budget check passed
            logger.info(
                f"Budget check passed for agent {self.agent_id}: "
                f"remaining={decision.remaining_budget}"
            )
            
        except BudgetExceededError:
            # Re-raise BudgetExceededError
            raise
        except PolicyEvaluationError as e:
            # Fail closed: convert policy evaluation error to budget exceeded
            logger.error(
                f"Policy evaluation failed for agent {self.agent_id}: {e}",
                exc_info=True
            )
            raise BudgetExceededError(
                f"Budget check failed for agent '{self.agent_id}': {e}"
            ) from e
        except Exception as e:
            # Fail closed: convert any unexpected error to budget exceeded
            logger.error(
                f"Unexpected error during budget check for agent {self.agent_id}: {e}",
                exc_info=True
            )
            raise BudgetExceededError(
                f"Budget check failed for agent '{self.agent_id}': {e}"
            ) from e
        
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit context: cleanup (no-op in v0.1).
        
        In v0.1, metering events must be emitted manually using
        client.emit_event(). Future versions may support automatic
        event emission on context exit.
        
        Args:
            exc_type: Exception type if exception occurred
            exc_val: Exception value if exception occurred
            exc_tb: Exception traceback if exception occurred
            
        Returns:
            False to propagate any exception that occurred
        """
        logger.debug(f"Exiting budget check context for agent {self.agent_id}")
        
        # Don't suppress exceptions
        return False
