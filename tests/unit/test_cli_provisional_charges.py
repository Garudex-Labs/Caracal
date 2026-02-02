"""
Unit tests for CLI provisional charge commands.

Tests provisional charge list and cleanup commands.
"""

import json
import tempfile
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from click.testing import CliRunner

from caracal.cli.main import cli


class TestProvisionalChargesCLI:
    """Test CLI provisional charge commands."""
    
    @pytest.fixture
    def temp_config(self):
        """Create a temporary config file with database configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
storage:
  agent_registry: /tmp/agents.json
  policy_store: /tmp/policies.json
  ledger: /tmp/ledger.jsonl
  pricebook: /tmp/pricebook.csv
  backup_dir: /tmp/backups
  backup_count: 3

database:
  host: localhost
  port: 5432
  database: caracal_test
  user: caracal
  password: caracal
  pool_size: 5
  max_overflow: 2
  pool_timeout: 30

ase:
  provisional_charges:
    default_expiration_seconds: 300
    timeout_minutes: 60
    cleanup_interval_seconds: 60
    cleanup_batch_size: 1000

defaults:
  currency: USD
  time_window: daily

logging:
  level: INFO
  file: /tmp/caracal.log
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
""")
            config_path = f.name
        
        yield config_path
        
        # Cleanup
        Path(config_path).unlink(missing_ok=True)
    
    def test_provisional_charges_list_help(self):
        """Test provisional charges list help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ['provisional-charges', 'list', '--help'])
        
        assert result.exit_code == 0
        assert 'List provisional charges' in result.output
        assert '--agent-id' in result.output
        assert '--show-expired' in result.output
        assert '--format' in result.output
    
    def test_provisional_charges_cleanup_help(self):
        """Test provisional charges cleanup help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ['provisional-charges', 'cleanup', '--help'])
        
        assert result.exit_code == 0
        assert 'Manually trigger cleanup' in result.output
        assert '--dry-run' in result.output
    
    def test_provisional_charges_group_help(self):
        """Test provisional charges group help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ['provisional-charges', '--help'])
        
        assert result.exit_code == 0
        assert 'Manage provisional charges' in result.output
        assert 'list' in result.output
        assert 'cleanup' in result.output
    
    def test_provisional_charges_in_main_help(self):
        """Test that provisional-charges appears in main help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert 'provisional-charges' in result.output
