---
sidebar_position: 3
title: Policy Commands
---

# Policy Commands

The `policy` command group manages budget policies for agents.

```
caracal policy COMMAND [OPTIONS]
```

---

## Commands Overview

| Command | Description |
|---------|-------------|
| [`create`](#create) | Create a new budget policy |
| [`list`](#list) | List all policies |
| [`get`](#get) | Get policy details |
| [`history`](#history) | View policy change history |
| [`version-at`](#version-at) | Get policy version at timestamp |
| [`compare-versions`](#compare-versions) | Compare two policy versions |

---

## Time Windows

| Window | Description | Reset |
|--------|-------------|-------|
| `hourly` | Budget resets every hour | On the hour |
| `daily` | Budget resets every day | Midnight UTC |
| `weekly` | Budget resets every week | Monday 00:00 UTC |
| `monthly` | Budget resets every month | 1st of month 00:00 UTC |

### Window Types

| Type | Description |
|------|-------------|
| `calendar` | Aligned to calendar boundaries (default) |
| `rolling` | Sliding window from current time |

---

## create

Create a new budget policy.

```
caracal policy create [OPTIONS]
```

### Options

| Option | Short | Required | Default | Description |
|--------|-------|:--------:|---------|-------------|
| `--agent-id` | `-a` | Yes | - | Agent ID this policy applies to |
| `--limit` | `-l` | Yes | - | Maximum spending limit |
| `--time-window` | `-w` | No | daily | Time window (hourly, daily, weekly, monthly) |
| `--window-type` | `-t` | No | calendar | Window type (rolling, calendar) |
| `--currency` | `-c` | No | USD | Currency code |

### Examples

<details>
<summary>Basic Daily Policy</summary>

```bash
caracal policy create \
  --agent-id 550e8400-e29b-41d4-a716-446655440000 \
  --limit 100.00
```

**Output:**
```
Policy created successfully!

Policy ID:    pol-001-aaaa-bbbb-cccc
Agent ID:     550e8400-e29b-41d4-a716-446655440000
Limit:        $100.00 USD
Time Window:  daily (calendar)
Created At:   2024-01-15T10:00:00Z
```

</details>

<details>
<summary>Monthly Policy</summary>

```bash
caracal policy create \
  --agent-id 550e8400-e29b-41d4-a716-446655440000 \
  --limit 1000.00 \
  --time-window monthly \
  --currency USD
```

**Output:**
```
Policy created successfully!

Policy ID:    pol-002-aaaa-bbbb-cccc
Agent ID:     550e8400-e29b-41d4-a716-446655440000
Limit:        $1000.00 USD
Time Window:  monthly (calendar)
Created At:   2024-01-15T10:00:00Z
```

</details>

<details>
<summary>Rolling Window Policy</summary>

```bash
caracal policy create \
  --agent-id 550e8400-e29b-41d4-a716-446655440000 \
  --limit 50.00 \
  --time-window hourly \
  --window-type rolling
```

Rolling windows are useful for rate limiting without waiting for calendar boundaries.

</details>

---

## list

List all policies.

```
caracal policy list [OPTIONS]
```

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--agent-id` | `-a` | - | Filter by agent ID |
| `--format` | `-f` | table | Output format: table or json |

### Examples

<details>
<summary>List All Policies</summary>

```bash
caracal policy list
```

**Output:**
```
Policy ID                             Agent              Limit           Window     Type
-------------------------------------------------------------------------------------------
pol-001-aaaa-bbbb-cccc                orchestrator       $1000.00 USD    monthly    calendar
pol-002-aaaa-bbbb-cccc                worker-1           $200.00 USD     daily      calendar
pol-003-aaaa-bbbb-cccc                worker-2           $200.00 USD     daily      calendar

Total: 3 policies
```

</details>

<details>
<summary>Filter by Agent</summary>

```bash
caracal policy list --agent-id 550e8400-e29b-41d4-a716-446655440000
```

</details>

<details>
<summary>JSON Output</summary>

```bash
caracal policy list --format json
```

**Output:**
```json
[
  {
    "policy_id": "pol-001-aaaa-bbbb-cccc",
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
    "limit_amount": "1000.00",
    "currency": "USD",
    "time_window": "monthly",
    "window_type": "calendar",
    "created_at": "2024-01-15T10:00:00Z"
  }
]
```

</details>

---

## get

Get details for a specific policy.

```
caracal policy get [OPTIONS]
```

### Options

| Option | Short | Required | Description |
|--------|-------|:--------:|-------------|
| `--policy-id` | `-p` | Yes | Policy ID |
| `--format` | `-f` | No | Output format: table or json |

### Examples

<details>
<summary>Get Policy Details</summary>

```bash
caracal policy get --policy-id pol-001-aaaa-bbbb-cccc
```

**Output:**
```
Policy Details
==============

Policy ID:     pol-001-aaaa-bbbb-cccc
Agent ID:      550e8400-e29b-41d4-a716-446655440000
Agent Name:    orchestrator
Limit:         $1000.00 USD
Time Window:   monthly (calendar)
Created At:    2024-01-15T10:00:00Z
Last Modified: 2024-01-15T10:00:00Z
Version:       1

Current Period
--------------
Period Start:  2024-01-01T00:00:00Z
Period End:    2024-01-31T23:59:59Z
Spent:         $234.56
Remaining:     $765.44
Utilization:   23.5%
```

</details>

---

## history

View policy change history.

```
caracal policy history [OPTIONS]
```

> Note: Requires database backend (not available with file-based storage).

### Options

| Option | Short | Required | Default | Description |
|--------|-------|:--------:|---------|-------------|
| `--policy-id` | `-p` | Yes | - | Policy ID |
| `--agent-id` | `-a` | No | - | Filter by agent ID |
| `--change-type` | | No | - | Filter by change type |
| `--start-time` | `-s` | No | - | Start time (ISO 8601) |
| `--end-time` | `-e` | No | - | End time (ISO 8601) |
| `--format` | `-f` | No | table | Output format |

### Change Types

| Type | Description |
|------|-------------|
| `created` | Policy was created |
| `updated` | Policy was modified |
| `limit_changed` | Limit amount was changed |
| `window_changed` | Time window was changed |

### Examples

<details>
<summary>View Full History</summary>

```bash
caracal policy history --policy-id pol-001-aaaa-bbbb-cccc
```

**Output:**
```
Policy History: pol-001-aaaa-bbbb-cccc
======================================

Version  Change Type     Changed At              Changed By       Details
----------------------------------------------------------------------------------
3        limit_changed   2024-01-20T14:30:00Z    admin           $500 -> $1000
2        limit_changed   2024-01-10T09:15:00Z    admin           $100 -> $500
1        created         2024-01-01T10:00:00Z    admin           Initial: $100

Total: 3 versions
```

</details>

<details>
<summary>Filter by Time Range</summary>

```bash
caracal policy history \
  --policy-id pol-001-aaaa-bbbb-cccc \
  --start-time 2024-01-15T00:00:00Z \
  --end-time 2024-01-31T23:59:59Z
```

</details>

---

## version-at

Get policy version at a specific timestamp.

```
caracal policy version-at [OPTIONS]
```

> Note: Requires database backend.

### Options

| Option | Short | Required | Description |
|--------|-------|:--------:|-------------|
| `--policy-id` | `-p` | Yes | Policy ID |
| `--timestamp` | `-t` | Yes | Timestamp (ISO 8601) |
| `--format` | `-f` | No | Output format |

### Examples

<details>
<summary>Get Historical Version</summary>

```bash
caracal policy version-at \
  --policy-id pol-001-aaaa-bbbb-cccc \
  --timestamp 2024-01-15T12:00:00Z
```

**Output:**
```
Policy Version at 2024-01-15T12:00:00Z
======================================

Version:       2
Policy ID:     pol-001-aaaa-bbbb-cccc
Agent ID:      550e8400-e29b-41d4-a716-446655440000
Limit:         $500.00 USD
Time Window:   monthly (calendar)
Valid From:    2024-01-10T09:15:00Z
Valid Until:   2024-01-20T14:30:00Z
```

</details>

---

## compare-versions

Compare two policy versions.

```
caracal policy compare-versions [OPTIONS]
```

> Note: Requires database backend.

### Options

| Option | Short | Required | Description |
|--------|-------|:--------:|-------------|
| `--version1` | `-v1` | Yes | First version ID |
| `--version2` | `-v2` | Yes | Second version ID |
| `--format` | `-f` | No | Output format |

### Examples

<details>
<summary>Compare Two Versions</summary>

```bash
caracal policy compare-versions \
  --version1 ver-001-aaaa \
  --version2 ver-002-aaaa
```

**Output:**
```
Policy Version Comparison
=========================

Field            Version 1           Version 2
-------------------------------------------------
limit_amount     $500.00             $1000.00
changed_at       2024-01-10          2024-01-20
changed_by       admin               admin

Changes:
  - limit_amount: increased from $500.00 to $1000.00
```

</details>

---

## Best Practices

### Multiple Policies Per Agent

An agent can have multiple active policies:

```
+----------------------------------+
|        AGENT: orchestrator       |
+----------------------------------+
|                                  |
|  Policy 1: $100/hour (burst)     |
|  Policy 2: $1000/month (overall) |
|                                  |
+----------------------------------+
```

All policies must pass for spending to be allowed.

### Policy Design

| Scenario | Recommended Setup |
|----------|-------------------|
| Prevent runaway costs | Hourly + monthly limits |
| Team budget allocation | Monthly per-agent limits |
| Rate limiting | Hourly rolling window |
| Cost center tracking | Monthly calendar aligned |

---

## See Also

- [Agent Commands](./agent) - Register agents for policies
- [Ledger Commands](./ledger) - View spending against policies
