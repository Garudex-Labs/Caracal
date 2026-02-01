"""
Database module for Caracal Core v0.2.

This module provides PostgreSQL database models and connection management.
"""

from caracal.db.connection import (
    DatabaseConfig,
    DatabaseConnectionManager,
    close_connection_manager,
    get_connection_manager,
    initialize_connection_manager,
)
from caracal.db.models import (
    Base,
    AgentIdentity,
    BudgetPolicy,
    LedgerEvent,
    ProvisionalCharge,
)

__all__ = [
    # Models
    "Base",
    "AgentIdentity",
    "BudgetPolicy",
    "LedgerEvent",
    "ProvisionalCharge",
    # Connection management
    "DatabaseConfig",
    "DatabaseConnectionManager",
    "get_connection_manager",
    "initialize_connection_manager",
    "close_connection_manager",
]
