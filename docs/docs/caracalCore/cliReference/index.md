---
sidebar_position: 1
title: CLI Reference
---

# Caracal CLI Reference

Complete reference for all Caracal Core command-line interface commands.

```
caracal [GLOBAL OPTIONS] COMMAND [COMMAND OPTIONS]
```

---

## Global Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--config` | `-c` | `~/.caracal/config.yaml` | Path to configuration file |
| `--log-level` | `-l` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `--verbose` | `-v` | false | Enable verbose output |
| `--version` | | | Show version and exit |
| `--help` | | | Show help message |

---

## Command Groups

```
caracal
  |
  +-- agent           Manage AI agent identities
  |     +-- register      Register new agent
  |     +-- list          List all agents
  |     +-- get           Get agent details
  |
  +-- policy          Manage budget policies
  |     +-- create        Create policy
  |     +-- list          List policies
  |     +-- get           Get policy details
  |     +-- history       View change history
  |     +-- version-at    Get version at timestamp
  |     +-- compare       Compare versions
  |
  +-- ledger          Query spending events
  |     +-- query         Query events
  |     +-- summary       Agent spending summary
  |     +-- delegation-chain   Trace delegation
  |     +-- list-partitions    List partitions
  |     +-- create-partitions  Create partitions
  |     +-- archive-partitions Archive old data
  |     +-- refresh-views      Refresh materialized views
  |
  +-- pricebook       Manage resource pricing
  |     +-- list          List prices
  |     +-- get           Get price for resource
  |     +-- set           Set price
  |     +-- import        Import from CSV
  |
  +-- delegation      Manage budget delegation
  |     +-- generate      Generate delegation token
  |     +-- list          List delegations
  |     +-- validate      Validate token
  |     +-- revoke        Revoke delegation
  |
  +-- db              Database management
  |     +-- init-db       Initialize schema
  |     +-- migrate       Run migrations
  |     +-- status        Check connection
  |
  +-- merkle          Cryptographic integrity
  |     +-- status        Tree status
  |     +-- proof         Generate proof
  |     +-- verify        Verify integrity
  |     +-- root          Get root hash
  |     +-- export-proofs Export proofs
  |
  +-- backup          Backup and restore
  |     +-- create        Create backup
  |     +-- restore       Restore from backup
  |     +-- list          List backups
  |
  +-- kafka           Kafka management
  |     +-- status        Check Kafka connection
  |     +-- topics        List topics
  |     +-- consumers     List consumer groups
  |
  +-- keys            Key management
        +-- list          List keys
        +-- rotate        Rotate keys
        +-- export        Export public key
```

---

## Command Reference

| Command Group | Description | Documentation |
|--------------|-------------|---------------|
| agent | Register and manage AI agent identities | [Agent Commands](./agent) |
| policy | Create and manage budget policies | [Policy Commands](./policy) |
| ledger | Query the immutable spending ledger | [Ledger Commands](./ledger) |
| pricebook | Manage resource pricing | [Pricebook Commands](./pricebook) |
| delegation | Manage parent-child budget sharing | [Delegation Commands](./delegation) |
| db | Database schema and migrations | [Database Commands](./database) |
| merkle | Cryptographic integrity verification | [Merkle Commands](./merkle) |
| backup | Backup and restore operations | [Backup Commands](./backup) |
| kafka | Kafka event stream management | [Kafka Commands](./kafka) |
| keys | Cryptographic key management | [Key Commands](./keys) |

---

## Quick Start Examples

<details>
<summary>Register an agent and create a policy</summary>

```bash
# Register a new agent
caracal agent register \
  --name "my-agent" \
  --owner "user@example.com"

# Output:
# Agent registered successfully!
# Agent ID: 550e8400-e29b-41d4-a716-446655440000

# Create a budget policy
caracal policy create \
  --agent-id 550e8400-e29b-41d4-a716-446655440000 \
  --limit 100.00 \
  --time-window daily

# Output:
# Policy created successfully!
# Policy ID: 7a3b2c1d-e4f5-6789-abcd-ef0123456789
```

</details>

<details>
<summary>Query spending and check budget</summary>

```bash
# Get spending summary
caracal ledger summary \
  --agent-id 550e8400-e29b-41d4-a716-446655440000

# Output:
# Agent Spending Summary
# ----------------------
# Agent ID:     550e8400-e29b-41d4-a716-446655440000
# Time Window:  daily
# Period:       2024-01-15 00:00:00 to 2024-01-15 23:59:59
# 
# Total Spent:  $23.45 USD
# Budget Limit: $100.00 USD
# Remaining:    $76.55 USD
# Utilization:  23.5%

# Query detailed events
caracal ledger query \
  --agent-id 550e8400-e29b-41d4-a716-446655440000 \
  --limit 5 \
  --format table
```

</details>

<details>
<summary>Verify ledger integrity</summary>

```bash
# Check Merkle tree status
caracal merkle status

# Verify recent events
caracal merkle verify

# Full verification (for audits)
caracal merkle verify --full --parallel 8
```

</details>

<details>
<summary>Database operations</summary>

```bash
# Initialize database schema
caracal db init-db

# Check database status
caracal db status

# Apply migrations
caracal db migrate up
```

</details>

---

## Configuration

### Configuration File

Default location: `~/.caracal/config.yaml`

```yaml
storage:
  agent_registry: ~/.caracal/agents.json
  policy_store: ~/.caracal/policies.json
  ledger: ~/.caracal/ledger.jsonl
  pricebook: ~/.caracal/pricebook.csv
  backup_dir: ~/.caracal/backups
  backup_count: 3

defaults:
  currency: USD
  time_window: daily

logging:
  level: INFO
  file: ~/.caracal/caracal.log

database:
  type: postgres
  host: localhost
  port: 5432
  database: caracal
  user: caracal
  password: "${DB_PASSWORD}"
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `CARACAL_CONFIG` | Override default config path |
| `CARACAL_LOG_LEVEL` | Override log level |
| `DB_PASSWORD` | Database password |
| `CARACAL_MASTER_PASSWORD` | Password for config encryption |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Configuration error |
| 3 | Database connection error |
| 4 | Authentication error |
| 5 | Budget exceeded |
| 6 | Resource not found |

---

## Output Formats

Most commands support multiple output formats:

| Format | Option | Description |
|--------|--------|-------------|
| Table | `--format table` | Human-readable table (default) |
| JSON | `--format json` | Machine-readable JSON |

<details>
<summary>Example: Table vs JSON output</summary>

**Table format (default):**
```bash
caracal agent list
```
```
Agent ID                              Name           Owner              Created
-------------------------------------------------------------------------------------
550e8400-e29b-41d4-a716-446655440000  my-agent       user@example.com   2024-01-15
7a3b2c1d-e4f5-6789-abcd-ef0123456789  worker-1       team@example.com   2024-01-15
```

**JSON format:**
```bash
caracal agent list --format json
```
```json
[
  {
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "my-agent",
    "owner": "user@example.com",
    "created_at": "2024-01-15T10:00:00Z"
  },
  {
    "agent_id": "7a3b2c1d-e4f5-6789-abcd-ef0123456789",
    "name": "worker-1",
    "owner": "team@example.com",
    "created_at": "2024-01-15T11:00:00Z"
  }
]
```

</details>

---

## See Also

- [SDK Client Reference](/caracalCore/apiReference/sdkClient) - Python SDK documentation
- [MCP Integration](/caracalCore/apiReference/mcpIntegration) - Model Context Protocol
- [Core vs Flow](/caracalCore/concepts/coreVsFlow) - When to use each tool
