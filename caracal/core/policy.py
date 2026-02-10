"""
Policy evaluation for Caracal Core.

This module provides the AuthorityEvaluator (previously PolicyEvaluator) for
validating execution mandates.
"""

from caracal.logging_config import get_logger

logger = get_logger(__name__)

# AuthorityEvaluator is now located in caracal.core.authority
# This file is kept for backward compatibility if needed, or can be fully deprecated.
# For now, we'll expose AuthorityEvaluator if it was here, but in v0.5 it's in authority.py.
# The previous PolicyStore and BudgetPolicy are removed.

# Re-export AuthorityEvaluator and AuthorityPolicy for convenience if desired,
# but main.py uses cli.authority_policy which uses db.models directly.

# We will just leave this empty or minimal to avoid ImportErrors if anyone imports caracal.core.policy
# without using it for budget stuff.
