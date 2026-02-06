---
sidebar_position: 2
title: Agent Commands
---

# Agent Commands

The `agent` command group manages AI agent identities in Caracal.

```
caracal agent COMMAND [OPTIONS]
```

---

## Commands Overview

| Command | Description |
|---------|-------------|
| [`register`](#register) | Register a new agent |
| [`list`](#list) | List all registered agents |
| [`get`](#get) | Get details for a specific agent |

---

## register

Register a new AI agent.

```
caracal agent register [OPTIONS]
```

### Options

| Option | Short | Required | Default | Description |
|--------|-------|:--------:|---------|-------------|
| `--name` | `-n` | Yes | - | Unique human-readable name |
| `--owner` | `-o` | Yes | - | Owner identifier (email or username) |
| `--parent-id` | `-p` | No | - | Parent agent ID for hierarchical relationships |
| `--delegated-budget` | `-b` | No | - | Budget amount from parent (requires --parent-id) |
| `--currency` | `-c` | No | USD | Currency code |
| `--time-window` | `-w` | No | daily | Budget time window |
| `--metadata` | `-m` | No | - | Key=value pairs (repeatable) |

### Validation Rules

| Rule | Description |
|------|-------------|
| Name uniqueness | Agent names must be unique across the registry |
| Parent validation | If --parent-id specified, parent must exist |
| Budget requirement | --delegated-budget requires --parent-id |

### Examples

<details>
<summary>Basic Registration</summary>

```bash
caracal agent register \
  --name "my-agent" \
  --owner "user@example.com"
```

**Output:**
```
Agent registered successfully!

Agent ID:    550e8400-e29b-41d4-a716-446655440000
Name:        my-agent
Owner:       user@example.com
Created At:  2024-01-15T10:00:00Z
```

</details>

<details>
<summary>Registration with Metadata</summary>

```bash
caracal agent register \
  --name "production-agent" \
  --owner "ops@example.com" \
  --metadata environment=production \
  --metadata team=platform \
  --metadata version=1.0.0
```

**Output:**
```
Agent registered successfully!

Agent ID:    550e8400-e29b-41d4-a716-446655440000
Name:        production-agent
Owner:       ops@example.com
Created At:  2024-01-15T10:00:00Z
Metadata:
  environment: production
  team:        platform
  version:     1.0.0
```

</details>

<details>
<summary>Child Agent with Delegated Budget</summary>

```bash
# First, get the parent agent ID
caracal agent list --format json | jq '.[] | select(.name=="orchestrator") | .agent_id'

# Register child with delegated budget
caracal agent register \
  --name "worker-1" \
  --owner "team@example.com" \
  --parent-id 550e8400-e29b-41d4-a716-446655440000 \
  --delegated-budget 200.00 \
  --time-window daily
```

**Output:**
```
Agent registered successfully!

Agent ID:         7a3b2c1d-e4f5-6789-abcd-ef0123456789
Name:             worker-1
Owner:            team@example.com
Parent Agent:     orchestrator (550e8400-e29b-41d4-a716-446655440000)
Delegated Budget: $200.00 USD / daily
Created At:       2024-01-15T10:00:00Z
```

</details>

### Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| Agent name already exists | Name is not unique | Choose a different name |
| Parent agent not found | Invalid parent ID | Verify parent agent exists |
| Delegated budget requires parent | --delegated-budget without --parent-id | Add --parent-id option |

---

## list

List all registered agents.

```
caracal agent list [OPTIONS]
```

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--format` | `-f` | table | Output format: table or json |

### Examples

<details>
<summary>Table Output</summary>

```bash
caracal agent list
```

**Output:**
```
Agent ID                              Name              Owner              Created            Parent
------------------------------------------------------------------------------------------------------
550e8400-e29b-41d4-a716-446655440000  orchestrator      admin@example.com  2024-01-15T10:00   -
7a3b2c1d-e4f5-6789-abcd-ef0123456789  worker-1          team@example.com   2024-01-15T10:05   orchestrator
8b4c3d2e-f5a6-7890-bcde-f01234567890  worker-2          team@example.com   2024-01-15T10:10   orchestrator

Total: 3 agents
```

</details>

<details>
<summary>JSON Output</summary>

```bash
caracal agent list --format json
```

**Output:**
```json
[
  {
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "orchestrator",
    "owner": "admin@example.com",
    "created_at": "2024-01-15T10:00:00Z",
    "parent_agent_id": null,
    "metadata": {}
  },
  {
    "agent_id": "7a3b2c1d-e4f5-6789-abcd-ef0123456789",
    "name": "worker-1",
    "owner": "team@example.com",
    "created_at": "2024-01-15T10:05:00Z",
    "parent_agent_id": "550e8400-e29b-41d4-a716-446655440000",
    "metadata": {
      "environment": "production"
    }
  }
]
```

</details>

<details>
<summary>Filter with jq</summary>

```bash
# Get only agent names
caracal agent list --format json | jq '.[].name'

# Find agents by owner
caracal agent list --format json | jq '.[] | select(.owner | contains("team"))'

# Get child agents of a parent
caracal agent list --format json | jq '.[] | select(.parent_agent_id != null)'
```

</details>

---

## get

Get detailed information about a specific agent.

```
caracal agent get [OPTIONS]
```

### Options

| Option | Short | Required | Default | Description |
|--------|-------|:--------:|---------|-------------|
| `--agent-id` | `-a` | Yes | - | Agent ID or name |
| `--format` | `-f` | No | table | Output format: table or json |

### Examples

<details>
<summary>Get by ID</summary>

```bash
caracal agent get --agent-id 550e8400-e29b-41d4-a716-446655440000
```

**Output:**
```
Agent Details
=============

Agent ID:      550e8400-e29b-41d4-a716-446655440000
Name:          orchestrator
Owner:         admin@example.com
Created At:    2024-01-15T10:00:00Z
Parent Agent:  None

Metadata:
  environment: production
  team:        platform

Child Agents:
  - worker-1 (7a3b2c1d-e4f5-6789-abcd-ef0123456789)
  - worker-2 (8b4c3d2e-f5a6-7890-bcde-f01234567890)

Active Policies:
  - Policy 001: $1000.00 USD / monthly
```

</details>

<details>
<summary>Get by Name</summary>

```bash
caracal agent get --agent-id orchestrator
```

The system will look up the agent by name if the provided value is not a valid UUID.

</details>

<details>
<summary>JSON Output</summary>

```bash
caracal agent get --agent-id orchestrator --format json
```

**Output:**
```json
{
  "agent_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "orchestrator",
  "owner": "admin@example.com",
  "created_at": "2024-01-15T10:00:00Z",
  "parent_agent_id": null,
  "metadata": {
    "environment": "production",
    "team": "platform"
  },
  "child_agents": [
    {
      "agent_id": "7a3b2c1d-e4f5-6789-abcd-ef0123456789",
      "name": "worker-1"
    },
    {
      "agent_id": "8b4c3d2e-f5a6-7890-bcde-f01234567890",
      "name": "worker-2"
    }
  ],
  "policies": [
    {
      "policy_id": "pol-001-aaaa-bbbb",
      "limit_amount": "1000.00",
      "currency": "USD",
      "time_window": "monthly"
    }
  ]
}
```

</details>

### Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| Agent not found | Invalid ID or name | Verify with `caracal agent list` |

---

## Best Practices

### Naming Conventions

| Pattern | Example | Use Case |
|---------|---------|----------|
| Environment prefix | `prod-agent-1` | Distinguish environments |
| Team prefix | `platform-orchestrator` | Group by team |
| Hierarchy suffix | `main-worker-1` | Show relationships |

### Metadata Organization

| Key | Example Value | Purpose |
|-----|---------------|---------|
| environment | production, staging | Deployment environment |
| team | platform, data | Owning team |
| version | 1.0.0 | Application version |
| cost-center | eng-001 | Billing allocation |

### Hierarchical Agents

```
+----------------------------------+
|          ORCHESTRATOR            |
|      Budget: $1000/month         |
+----------------+-----------------+
                 |
     +-----------+-----------+
     |           |           |
+----v----+ +----v----+ +----v----+
| Worker1 | | Worker2 | | Worker3 |
| $200/d  | | $200/d  | | $100/d  |
+---------+ +---------+ +---------+
```

Benefits:
- Child spending counts against parent budget
- Easy to track team-level spending
- Revoke all children by revoking parent

---

## See Also

- [Policy Commands](./policy) - Create budget policies for agents
- [Delegation Commands](./delegation) - Manage parent-child delegation
- [Ledger Commands](./ledger) - Query agent spending
