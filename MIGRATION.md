# Migrating from Caracal Core v0.1 to v0.2

This guide explains how to migrate your Caracal Core installation from v0.1 (file-based storage) to v0.2 (PostgreSQL backend).

## Overview

Caracal Core v0.2 introduces PostgreSQL as the primary storage backend, replacing the file-based storage used in v0.1. The migration process is designed to be:

- **Idempotent**: Safe to run multiple times
- **Validated**: Automatic verification of migrated data
- **Selective**: Migrate specific components if needed
- **Reversible**: Original v0.1 data files are preserved

## Prerequisites

### 1. PostgreSQL Installation

Install PostgreSQL 14 or later:

```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS (using Homebrew)
brew install postgresql@14

# Fedora/RHEL
sudo dnf install postgresql-server postgresql-contrib
```

### 2. Database Setup

Create a database and user for Caracal:

```bash
# Start PostgreSQL service
sudo systemctl start postgresql

# Create database and user
sudo -u postgres psql
```

In the PostgreSQL shell:

```sql
CREATE DATABASE caracal;
CREATE USER caracal WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE caracal TO caracal;
\q
```

### 3. Update Configuration

Create or update your configuration file (`~/.caracal/config.yaml`) to include database settings:

```yaml
# File-based storage (v0.1 - for migration source)
storage:
  agent_registry: ~/.caracal/agents.json
  policy_store: ~/.caracal/policies.json
  ledger: ~/.caracal/ledger.jsonl
  pricebook: ~/.caracal/pricebook.csv
  backup_dir: ~/.caracal/backups
  backup_count: 3

# PostgreSQL database (v0.2 - migration target)
database:
  host: localhost
  port: 5432
  database: caracal
  user: caracal
  password: your_secure_password
  pool_size: 10
  max_overflow: 5
  pool_timeout: 30

# Other settings...
defaults:
  currency: USD
  time_window: daily
  default_budget: 100.00

logging:
  level: INFO
  file: ~/.caracal/caracal.log
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

See `examples/migration_config.yaml` for a complete example.

## Migration Process

### Step 1: Backup Your Data

Before migrating, create a backup of your v0.1 data:

```bash
# Create backup directory
mkdir -p ~/caracal-backup

# Copy v0.1 data files
cp ~/.caracal/agents.json ~/caracal-backup/
cp ~/.caracal/policies.json ~/caracal-backup/
cp ~/.caracal/ledger.jsonl ~/caracal-backup/
cp ~/.caracal/pricebook.csv ~/caracal-backup/
```

### Step 2: Dry Run (Recommended)

Perform a dry-run migration to validate your data without writing to the database:

```bash
caracal migrate v0.1-to-v0.2 --dry-run
```

This will:
- Validate source files exist
- Check database connectivity
- Report what would be migrated
- Identify any potential issues

### Step 3: Run Migration

Execute the full migration:

```bash
caracal migrate v0.1-to-v0.2
```

The migration will:
1. **Validate** source files and database connection
2. **Migrate** agents, policies, and ledger events
3. **Validate** migrated data integrity

Example output:

```
Caracal Migration: v0.1 → v0.2
================================

Source Directory: /home/user/.caracal
Target Database: postgresql://localhost/caracal

Phase 1: Validation
-------------------
✓ Found agents.json (15 agents)
✓ Found policies.json (23 policies)
✓ Found ledger.jsonl (1,247 events)
✓ Database connection successful

Phase 2: Migration
------------------
→ Migrating agents... 15/15 (0 skipped, 0 errors) [2.3s]
→ Migrating policies... 23/23 (0 skipped, 0 errors) [1.8s]
→ Migrating ledger... 1,247/1,247 (0 skipped, 0 errors) [8.5s]

Phase 3: Validation
-------------------
✓ Agent count matches: 15
✓ Policy count matches: 23
✓ Ledger event count matches: 1,247
✓ Spot-check validation passed (10 random records)

Migration Summary
-----------------
Total Records: 1,285
Migrated: 1,285
Skipped: 0
Errors: 0
Duration: 12.6 seconds

✓ Migration completed successfully!
```

### Step 4: Validate Migration

After migration, validate the data integrity:

```bash
caracal migrate validate
```

This performs:
- Record count comparison
- Spot-check validation of random records
- Foreign key integrity verification

## Advanced Options

### Selective Migration

Migrate only specific components:

```bash
# Migrate only agents
caracal migrate v0.1-to-v0.2 --agents-only

# Migrate only policies
caracal migrate v0.1-to-v0.2 --policies-only

# Migrate only ledger events
caracal migrate v0.1-to-v0.2 --ledger-only
```

### Custom Source Directory

Specify a custom v0.1 data directory:

```bash
caracal migrate v0.1-to-v0.2 --source-dir /path/to/v01/data
```

### Batch Size Control

Control the number of records processed per batch:

```bash
caracal migrate v0.1-to-v0.2 --batch-size 500
```

### Verbose Output

Enable detailed progress output:

```bash
caracal migrate v0.1-to-v0.2 --verbose
```

## Idempotency

The migration is idempotent and can be safely re-run:

- **Agents**: Duplicate agents are skipped (by agent_id)
- **Policies**: Duplicate policies are skipped (by policy_id)
- **Ledger Events**: Events are append-only (duplicates will be added)

If you need to re-run the migration, agents and policies will be skipped if they already exist, but ledger events will be duplicated. To avoid this, clear the database before re-running:

```sql
-- Connect to PostgreSQL
psql -U caracal -d caracal

-- Clear tables
TRUNCATE TABLE ledger_events CASCADE;
TRUNCATE TABLE budget_policies CASCADE;
TRUNCATE TABLE agent_identities CASCADE;
```

## Troubleshooting

### Database Connection Failed

**Error**: `Database connection failed`

**Solution**:
1. Verify PostgreSQL is running: `sudo systemctl status postgresql`
2. Check database credentials in `config.yaml`
3. Test connection: `psql -U caracal -d caracal -h localhost`

### Foreign Key Violations

**Error**: `Foreign key violation for policy: agent_id not found`

**Solution**:
1. Ensure agents are migrated before policies
2. Check that all agent_ids in policies.json exist in agents.json
3. Run migration with `--agents-only` first, then `--policies-only`

### Missing Source Files

**Error**: `agents.json not found`

**Solution**:
1. Verify v0.1 data directory path: `ls ~/.caracal/`
2. Use `--source-dir` to specify correct path
3. Ensure v0.1 data files exist and are readable

### Validation Failed

**Error**: `Agent count mismatch: source=15, target=10`

**Solution**:
1. Check migration errors in output
2. Review database logs for issues
3. Re-run migration (idempotent)
4. Contact support if issue persists

## Post-Migration

### Update Application Configuration

After successful migration, update your application to use the PostgreSQL backend:

1. Update `config.yaml` to use database settings
2. Restart any running Caracal services
3. Test SDK integration with v0.2 backend

### Verify v0.1 SDK Compatibility

Caracal Core v0.2 maintains backward compatibility with v0.1 SDK:

```python
# v0.1 SDK code works unchanged with v0.2 backend
from caracal.sdk import CaracalClient

client = CaracalClient()
# All v0.1 operations work transparently with PostgreSQL
```

### Archive v0.1 Data

Once migration is validated, you can archive v0.1 data files:

```bash
# Create archive
tar -czf caracal-v01-data-$(date +%Y%m%d).tar.gz ~/.caracal/*.json ~/.caracal/*.jsonl

# Move to backup location
mv caracal-v01-data-*.tar.gz ~/backups/
```

**Important**: Keep v0.1 data files as backup until you're confident in the v0.2 migration.

## Rollback

If you need to rollback to v0.1:

1. Stop all Caracal services
2. Restore v0.1 configuration (remove database section)
3. Restore v0.1 data files from backup
4. Restart services

The original v0.1 data files are never modified by the migration process.

## Support

For migration issues or questions:

- GitHub Issues: https://github.com/Garudex-Labs/caracal/issues
- Documentation: https://github.com/Garudex-Labs/caracal/blob/main/README.md
- Community: https://github.com/Garudex-Labs/caracal/discussions

## Next Steps

After successful migration:

1. Explore v0.2 features:
   - Parent-child agent relationships
   - Delegation tokens
   - Provisional charges
   - Gateway proxy
   - MCP adapter

2. Review v0.2 documentation:
   - `.kiro/specs/caracal-core-v02/requirements.md`
   - `.kiro/specs/caracal-core-v02/design.md`

3. Test new functionality:
   - Create child agents with delegated budgets
   - Use gateway proxy for network enforcement
   - Integrate with MCP protocol
