"""
Unit tests for migration functionality.

Tests the MigrationManager for migrating v0.1 data to v0.2 PostgreSQL.
"""

import json
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from caracal.core.migration import MigrationManager, MigrationResult, ValidationResult
from caracal.db.models import Base, AgentIdentity, BudgetPolicy, LedgerEvent


@pytest.fixture
def temp_v01_data_dir():
    """Create temporary v0.1 data directory with sample data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        
        # Create sample agents.json
        agents = [
            {
                "agent_id": str(uuid4()),
                "name": "test-agent-1",
                "owner": "user@example.com",
                "created_at": "2024-01-15T10:00:00Z",
                "metadata": {"key": "value"}
            },
            {
                "agent_id": str(uuid4()),
                "name": "test-agent-2",
                "owner": "user@example.com",
                "created_at": "2024-01-16T10:00:00Z",
                "metadata": None
            }
        ]
        
        with open(data_dir / "agents.json", 'w') as f:
            json.dump(agents, f)
        
        # Create sample policies.json
        policies = [
            {
                "policy_id": str(uuid4()),
                "agent_id": agents[0]["agent_id"],
                "limit_amount": "100.00",
                "time_window": "daily",
                "currency": "USD",
                "created_at": "2024-01-15T10:00:00Z",
                "active": True
            }
        ]
        
        with open(data_dir / "policies.json", 'w') as f:
            json.dump(policies, f)
        
        # Create sample ledger.jsonl
        ledger_events = [
            {
                "agent_id": agents[0]["agent_id"],
                "timestamp": "2024-01-15T11:00:00Z",
                "resource_type": "openai.gpt4.input_tokens",
                "quantity": "1000",
                "cost": "0.03",
                "currency": "USD",
                "metadata": {"model": "gpt-4"}
            },
            {
                "agent_id": agents[0]["agent_id"],
                "timestamp": "2024-01-15T12:00:00Z",
                "resource_type": "openai.gpt4.output_tokens",
                "quantity": "500",
                "cost": "0.03",
                "currency": "USD",
                "metadata": {"model": "gpt-4"}
            }
        ]
        
        with open(data_dir / "ledger.jsonl", 'w') as f:
            for event in ledger_events:
                f.write(json.dumps(event) + '\n')
        
        yield data_dir


@pytest.fixture
def in_memory_db():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()
    engine.dispose()


def test_migrate_agents(temp_v01_data_dir, in_memory_db):
    """Test agent migration from v0.1 to v0.2."""
    migration_manager = MigrationManager(in_memory_db, str(temp_v01_data_dir))
    
    result = migration_manager.migrate_agents()
    
    assert result.migrated_count == 2
    assert result.skipped_count == 0
    assert result.error_count == 0
    assert len(result.errors) == 0
    
    # Verify agents in database
    agents = in_memory_db.query(AgentIdentity).all()
    assert len(agents) == 2
    assert agents[0].name == "test-agent-1"
    assert agents[1].name == "test-agent-2"


def test_migrate_policies(temp_v01_data_dir, in_memory_db):
    """Test policy migration from v0.1 to v0.2."""
    migration_manager = MigrationManager(in_memory_db, str(temp_v01_data_dir))
    
    # Migrate agents first (foreign key dependency)
    migration_manager.migrate_agents()
    
    result = migration_manager.migrate_policies()
    
    assert result.migrated_count == 1
    assert result.skipped_count == 0
    assert result.error_count == 0
    assert len(result.errors) == 0
    
    # Verify policies in database
    policies = in_memory_db.query(BudgetPolicy).all()
    assert len(policies) == 1
    assert policies[0].limit_amount == Decimal("100.00")
    assert policies[0].time_window == "daily"


def test_migrate_ledger(temp_v01_data_dir, in_memory_db):
    """Test ledger migration from v0.1 to v0.2."""
    migration_manager = MigrationManager(in_memory_db, str(temp_v01_data_dir))
    
    # Migrate agents first (foreign key dependency)
    migration_manager.migrate_agents()
    
    result = migration_manager.migrate_ledger()
    
    assert result.migrated_count == 2
    assert result.skipped_count == 0
    assert result.error_count == 0
    assert len(result.errors) == 0
    
    # Verify ledger events in database
    events = in_memory_db.query(LedgerEvent).all()
    assert len(events) == 2
    assert events[0].resource_type == "openai.gpt4.input_tokens"
    assert events[1].resource_type == "openai.gpt4.output_tokens"


def test_migrate_all(temp_v01_data_dir, in_memory_db):
    """Test full migration from v0.1 to v0.2."""
    migration_manager = MigrationManager(in_memory_db, str(temp_v01_data_dir))
    
    summary = migration_manager.migrate_all()
    
    assert summary.agents.migrated_count == 2
    assert summary.policies.migrated_count == 1
    assert summary.ledger.migrated_count == 2
    assert summary.total_duration_seconds > 0
    
    # Verify all data in database
    assert in_memory_db.query(AgentIdentity).count() == 2
    assert in_memory_db.query(BudgetPolicy).count() == 1
    assert in_memory_db.query(LedgerEvent).count() == 2


def test_idempotent_migration(temp_v01_data_dir, in_memory_db):
    """Test that migration is idempotent (can be run multiple times)."""
    migration_manager = MigrationManager(in_memory_db, str(temp_v01_data_dir))
    
    # Run migration twice
    summary1 = migration_manager.migrate_all()
    summary2 = migration_manager.migrate_all()
    
    # First run should migrate all records
    assert summary1.agents.migrated_count == 2
    assert summary1.policies.migrated_count == 1
    
    # Second run should skip duplicates (for agents and policies)
    # Note: Ledger events will be duplicated since they don't have unique constraints
    assert summary2.agents.skipped_count == 2
    assert summary2.policies.skipped_count == 1
    
    # Verify no duplicate agents or policies
    assert in_memory_db.query(AgentIdentity).count() == 2
    assert in_memory_db.query(BudgetPolicy).count() == 1


def test_validate_migration(temp_v01_data_dir, in_memory_db):
    """Test migration validation."""
    migration_manager = MigrationManager(in_memory_db, str(temp_v01_data_dir))
    
    # Run migration
    migration_manager.migrate_all()
    
    # Validate migration
    validation_result = migration_manager.validate_migration(spot_check_count=2)
    
    assert validation_result.valid is True
    assert validation_result.agent_count_match is True
    assert validation_result.policy_count_match is True
    assert validation_result.ledger_count_match is True
    assert validation_result.spot_check_passed is True
    assert len(validation_result.errors) == 0
    
    assert validation_result.source_counts['agents'] == 2
    assert validation_result.target_counts['agents'] == 2


def test_missing_source_files(in_memory_db):
    """Test migration with missing source files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        migration_manager = MigrationManager(in_memory_db, tmpdir)
        
        result = migration_manager.migrate_agents()
        
        assert result.migrated_count == 0
        assert result.error_count == 1
        assert len(result.errors) > 0
        assert "not found" in result.errors[0].lower()


def test_foreign_key_violation(temp_v01_data_dir, in_memory_db):
    """Test policy migration with invalid agent_id (foreign key violation)."""
    # Add policy with non-existent agent_id
    policies_file = temp_v01_data_dir / "policies.json"
    with open(policies_file, 'r') as f:
        policies = json.load(f)
    
    policies.append({
        "policy_id": str(uuid4()),
        "agent_id": str(uuid4()),  # Non-existent agent
        "limit_amount": "50.00",
        "time_window": "daily",
        "currency": "USD",
        "created_at": "2024-01-15T10:00:00Z",
        "active": True
    })
    
    with open(policies_file, 'w') as f:
        json.dump(policies, f)
    
    migration_manager = MigrationManager(in_memory_db, str(temp_v01_data_dir))
    
    # Migrate agents first
    migration_manager.migrate_agents()
    
    # Migrate policies - should have one error for foreign key violation
    result = migration_manager.migrate_policies()
    
    assert result.migrated_count == 1  # First policy should succeed
    assert result.error_count == 1  # Second policy should fail
    assert len(result.errors) > 0
