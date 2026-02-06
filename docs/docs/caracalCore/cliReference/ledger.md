---
sidebar_position: 4
title: Ledger Commands
---

# Ledger Commands

The `ledger` command group queries the immutable spending ledger.

```
caracal ledger COMMAND [OPTIONS]
```

---

## Commands Overview

| Command | Description |
|---------|-------------|
| [`query`](#query) | Query spending events |
| [`summary`](#summary) | Get agent spending summary |
| [`delegation-chain`](#delegation-chain) | Trace delegation for an event |
| [`list-partitions`](#list-partitions) | List ledger partitions |
| [`create-partitions`](#create-partitions) | Create new partitions |
| [`archive-partitions`](#archive-partitions) | Archive old partitions |
| [`refresh-views`](#refresh-views) | Refresh materialized views |

---

## Ledger Properties

| Property | Description |
|----------|-------------|
| Append-only | Events can only be added, never modified |
| Immutable | Historical records cannot be changed |
| Merkle-backed | Cryptographic integrity proofs |
| Partitioned | Monthly partitions for performance |

---

## query

Query spending events with filters.

```
caracal ledger query [OPTIONS]
```

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--agent-id` | `-a` | - | Filter by agent ID |
| `--start-time` | `-s` | - | Start time (ISO 8601) |
| `--end-time` | `-e` | - | End time (ISO 8601) |
| `--min-amount` | | - | Minimum amount filter |
| `--max-amount` | | - | Maximum amount filter |
| `--operation` | `-o` | - | Filter by operation type |
| `--limit` | `-n` | 100 | Maximum results |
| `--offset` | | 0 | Skip this many results |
| `--format` | `-f` | table | Output format |

### Examples

<details>
<summary>Query by Agent</summary>

```bash
caracal ledger query \
  --agent-id 550e8400-e29b-41d4-a716-446655440000 \
  --limit 10
```

**Output:**
```
Event ID                              Timestamp              Amount      Operation
-------------------------------------------------------------------------------------
evt-001-aaaa-bbbb-cccc                2024-01-15T14:30:45Z   $0.0023     gpt-4-completion
evt-002-aaaa-bbbb-cccc                2024-01-15T14:28:12Z   $0.0015     gpt-4-completion
evt-003-aaaa-bbbb-cccc                2024-01-15T14:25:00Z   $0.0008     embedding
...

Showing 10 of 1,234 events
```

</details>

<details>
<summary>Query by Time Range</summary>

```bash
caracal ledger query \
  --agent-id 550e8400-e29b-41d4-a716-446655440000 \
  --start-time 2024-01-15T00:00:00Z \
  --end-time 2024-01-15T23:59:59Z
```

</details>

<details>
<summary>Query by Amount Range</summary>

```bash
# Find expensive operations (> $1)
caracal ledger query \
  --agent-id 550e8400-e29b-41d4-a716-446655440000 \
  --min-amount 1.00
```

</details>

<details>
<summary>Query by Operation Type</summary>

```bash
caracal ledger query \
  --agent-id 550e8400-e29b-41d4-a716-446655440000 \
  --operation gpt-4-completion
```

</details>

<details>
<summary>JSON Output for Scripting</summary>

```bash
caracal ledger query \
  --agent-id 550e8400-e29b-41d4-a716-446655440000 \
  --format json \
  --limit 5
```

**Output:**
```json
{
  "events": [
    {
      "event_id": "evt-001-aaaa-bbbb-cccc",
      "agent_id": "550e8400-e29b-41d4-a716-446655440000",
      "timestamp": "2024-01-15T14:30:45Z",
      "amount": "0.0023",
      "currency": "USD",
      "operation_type": "gpt-4-completion",
      "resource_type": "openai.gpt-4.output_tokens",
      "quantity": 150
    }
  ],
  "total_count": 1234,
  "limit": 5,
  "offset": 0
}
```

</details>

---

## summary

Get spending summary for an agent.

```
caracal ledger summary [OPTIONS]
```

### Options

| Option | Short | Required | Default | Description |
|--------|-------|:--------:|---------|-------------|
| `--agent-id` | `-a` | Yes | - | Agent ID |
| `--time-window` | `-w` | No | daily | Summary window |
| `--format` | `-f` | No | table | Output format |

### Examples

<details>
<summary>Daily Summary</summary>

```bash
caracal ledger summary --agent-id 550e8400-e29b-41d4-a716-446655440000
```

**Output:**
```
Agent Spending Summary
======================

Agent ID:       550e8400-e29b-41d4-a716-446655440000
Agent Name:     orchestrator
Time Window:    daily

Current Period
--------------
Period Start:   2024-01-15T00:00:00Z
Period End:     2024-01-15T23:59:59Z

Budget Status
-------------
Budget Limit:   $100.00 USD
Total Spent:    $23.45 USD
Remaining:      $76.55 USD
Utilization:    23.5%

Breakdown by Operation
----------------------
Operation              Count       Amount        Percentage
-------------------------------------------------------------
gpt-4-completion       156         $18.72        79.8%
embedding              423         $3.38         14.4%
whisper-transcribe     12          $1.35         5.8%

Total:                 591         $23.45        100%
```

</details>

<details>
<summary>Monthly Summary</summary>

```bash
caracal ledger summary \
  --agent-id 550e8400-e29b-41d4-a716-446655440000 \
  --time-window monthly
```

</details>

<details>
<summary>JSON Output</summary>

```bash
caracal ledger summary \
  --agent-id 550e8400-e29b-41d4-a716-446655440000 \
  --format json
```

**Output:**
```json
{
  "agent_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_name": "orchestrator",
  "time_window": "daily",
  "period_start": "2024-01-15T00:00:00Z",
  "period_end": "2024-01-15T23:59:59Z",
  "budget_limit": "100.00",
  "total_spent": "23.45",
  "remaining": "76.55",
  "utilization_percent": 23.45,
  "currency": "USD",
  "breakdown": {
    "gpt-4-completion": "18.72",
    "embedding": "3.38",
    "whisper-transcribe": "1.35"
  }
}
```

</details>

---

## delegation-chain

Trace the delegation chain for an event.

```
caracal ledger delegation-chain [OPTIONS]
```

### Options

| Option | Short | Required | Description |
|--------|-------|:--------:|-------------|
| `--event-id` | `-e` | Yes | Event ID to trace |
| `--format` | `-f` | No | Output format |

### Examples

<details>
<summary>Trace Delegation Chain</summary>

```bash
caracal ledger delegation-chain --event-id evt-001-aaaa-bbbb-cccc
```

**Output:**
```
Delegation Chain for Event: evt-001-aaaa-bbbb-cccc
==================================================

Event Details
-------------
Event ID:     evt-001-aaaa-bbbb-cccc
Amount:       $0.0023 USD
Operation:    gpt-4-completion
Timestamp:    2024-01-15T14:30:45Z

Delegation Chain
----------------

  +-------------------+
  |   orchestrator    |  Budget: $1000/month
  | (Root Principal)  |  Spent: $234.56
  +---------+---------+
            |
            | Delegated $200/day
            v
  +-------------------+
  |     worker-1      |  Budget: $200/day
  | (Delegated Agent) |  Spent: $23.45
  +---------+---------+
            |
            | Spent $0.0023
            v
  +-------------------+
  |    THIS EVENT     |
  |   $0.0023 USD     |
  +-------------------+

Budget Impact
-------------
  worker-1 spending:       $23.45 -> $23.4523
  orchestrator spending:   $234.56 -> $234.5623
```

</details>

---

## list-partitions

List ledger table partitions.

```
caracal ledger list-partitions [OPTIONS]
```

> Note: Requires database backend.

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--format` | `-f` | table | Output format |

### Examples

<details>
<summary>List All Partitions</summary>

```bash
caracal ledger list-partitions
```

**Output:**
```
Ledger Partitions
=================

Partition Name              Range Start         Range End           Rows        Size
---------------------------------------------------------------------------------------
ledger_events_2024_01       2024-01-01          2024-02-01          1,234,567   156 MB
ledger_events_2024_02       2024-02-01          2024-03-01          987,654     124 MB
ledger_events_2024_03       2024-03-01          2024-04-01          (current)   45 MB

Total: 3 partitions, 2,222,221 rows, 325 MB
```

</details>

---

## create-partitions

Create new partitions for future months.

```
caracal ledger create-partitions [OPTIONS]
```

> Note: Requires database backend.

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--months` | `-m` | 3 | Number of months to create |

### Examples

<details>
<summary>Create Partitions</summary>

```bash
caracal ledger create-partitions --months 6
```

**Output:**
```
Creating ledger partitions...

Created: ledger_events_2024_04 (2024-04-01 to 2024-05-01)
Created: ledger_events_2024_05 (2024-05-01 to 2024-06-01)
Created: ledger_events_2024_06 (2024-06-01 to 2024-07-01)
Created: ledger_events_2024_07 (2024-07-01 to 2024-08-01)
Created: ledger_events_2024_08 (2024-08-01 to 2024-09-01)
Created: ledger_events_2024_09 (2024-09-01 to 2024-10-01)

Successfully created 6 partitions.
```

</details>

---

## archive-partitions

Archive old partitions.

```
caracal ledger archive-partitions [OPTIONS]
```

> Note: Requires database backend.

### Options

| Option | Short | Required | Description |
|--------|-------|:--------:|-------------|
| `--before` | `-b` | Yes | Archive partitions before this date |
| `--output` | `-o` | No | Output directory for archives |
| `--delete` | | No | Delete after archiving |

### Examples

<details>
<summary>Archive Old Data</summary>

```bash
caracal ledger archive-partitions \
  --before 2024-01-01 \
  --output /backup/ledger-archives/
```

**Output:**
```
Archiving ledger partitions before 2024-01-01...

Archiving: ledger_events_2023_10
  Rows: 1,123,456
  Exporting to: /backup/ledger-archives/ledger_events_2023_10.parquet
  Done (45.2 MB)

Archiving: ledger_events_2023_11
  Rows: 987,654
  Exporting to: /backup/ledger-archives/ledger_events_2023_11.parquet
  Done (38.7 MB)

Archiving: ledger_events_2023_12
  Rows: 1,234,567
  Exporting to: /backup/ledger-archives/ledger_events_2023_12.parquet
  Done (52.1 MB)

Archived 3 partitions (3,345,677 rows, 136 MB total)
```

</details>

---

## refresh-views

Refresh materialized views.

```
caracal ledger refresh-views [OPTIONS]
```

> Note: Requires database backend.

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--concurrent` | | false | Refresh concurrently (no lock) |

### Examples

<details>
<summary>Refresh Views</summary>

```bash
caracal ledger refresh-views --concurrent
```

**Output:**
```
Refreshing materialized views...

Refreshing: agent_daily_spending_mv
  Mode: concurrent (no lock)
  Duration: 2.3s
  Done

Refreshing: agent_hourly_spending_mv
  Mode: concurrent (no lock)
  Duration: 1.8s
  Done

All views refreshed successfully.
```

</details>

---

## Event Structure

| Field | Type | Description |
|-------|------|-------------|
| event_id | UUID | Unique event identifier |
| agent_id | UUID | Agent that incurred the cost |
| timestamp | ISO 8601 | When the event occurred |
| amount | Decimal | Cost amount |
| currency | String | Currency code (USD) |
| operation_type | String | Type of operation |
| resource_type | String | Pricebook resource type |
| quantity | Decimal | Quantity consumed |
| delegation_chain | Array | Parent agents in delegation |
| request_id | String | Original request identifier |
| metadata | Object | Additional context |

---

## See Also

- [Merkle Commands](./merkle) - Verify ledger integrity
- [Policy Commands](./policy) - Budget limits for agents
- [Summary Commands](./ledger#summary) - Spending summaries
