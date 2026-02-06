---
sidebar_position: 7
title: Delegation Commands
---

# Delegation Commands

The `delegation` command group manages budget delegation between parent and child agents.

```
caracal delegation COMMAND [OPTIONS]
```

---

## Overview

Delegation allows a parent agent to share budget with child agents.

```
+-------------------------------+
|        ORCHESTRATOR           |
|     Budget: $1000/month       |
+---------------+---------------+
                |
        Delegates Budget
                |
     +----------+----------+
     |          |          |
     v          v          v
+--------+ +--------+ +--------+
|Worker-1| |Worker-2| |Worker-3|
|$200/day| |$200/day| |$100/day|
+--------+ +--------+ +--------+

Child spending counts against parent budget
```

### Properties

| Property | Description |
|----------|-------------|
| Hierarchical | Multi-level delegation chains supported |
| Time-limited | Tokens can have expiration dates |
| Revocable | Parent can revoke at any time |
| Constrained | Optional operation restrictions |

---

## Commands Overview

| Command | Description |
|---------|-------------|
| [`generate`](#generate) | Generate a delegation token |
| [`list`](#list) | List all delegations |
| [`validate`](#validate) | Validate a delegation token |
| [`revoke`](#revoke) | Revoke a delegation |

---

## generate

Generate a delegation token.

```
caracal delegation generate [OPTIONS]
```

### Options

| Option | Short | Required | Default | Description |
|--------|-------|:--------:|---------|-------------|
| `--parent-id` | `-p` | Yes | - | Parent agent ID |
| `--child-id` | `-c` | Yes | - | Child agent ID |
| `--budget` | `-b` | Yes | - | Delegated budget amount |
| `--currency` | | No | USD | Currency code |
| `--time-window` | `-w` | No | daily | Budget time window |
| `--expires` | `-e` | No | - | Expiration date (ISO 8601) |
| `--constraints` | | No | - | Additional constraints (JSON) |
| `--output` | `-o` | No | stdout | Output file path |

### Examples

<details>
<summary>Basic Delegation</summary>

```bash
caracal delegation generate \
  --parent-id 550e8400-e29b-41d4-a716-446655440000 \
  --child-id 7a3b2c1d-e4f5-6789-abcd-ef0123456789 \
  --budget 100.00
```

**Output:**
```
Delegation Token Generated
==========================

Token ID:     tok-001-aaaa-bbbb-cccc
Parent:       550e8400-... (orchestrator)
Child:        7a3b2c1d-... (worker-1)
Budget:       $100.00 USD / daily
Expires:      Never

Token (JWT):
eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJjYXJhY2FsLWNv
cmUiLCJzdWIiOiI3YTNiMmMxZC1lNGY1LTY3ODktYWJjZC1lZjAxMjM0NTY3
ODkiLCJhdWQiOiJjYXJhY2FsLWdhdGV3YXkiLC...

Usage:
  1. Store this token securely
  2. Child agent includes token in X-Caracal-Delegation header
  3. Gateway validates and tracks spending against parent
```

</details>

<details>
<summary>Delegation with Expiration</summary>

```bash
caracal delegation generate \
  --parent-id 550e8400-e29b-41d4-a716-446655440000 \
  --child-id 7a3b2c1d-e4f5-6789-abcd-ef0123456789 \
  --budget 500.00 \
  --time-window weekly \
  --expires 2024-12-31T23:59:59Z
```

</details>

<details>
<summary>Delegation with Constraints</summary>

```bash
caracal delegation generate \
  --parent-id 550e8400-e29b-41d4-a716-446655440000 \
  --child-id 7a3b2c1d-e4f5-6789-abcd-ef0123456789 \
  --budget 50.00 \
  --constraints '{
    "allowed_operations": ["gpt-4-completion", "embedding"],
    "max_single_request": 5.00,
    "rate_limit_per_minute": 10
  }'
```

</details>

<details>
<summary>Save Token to File</summary>

```bash
caracal delegation generate \
  --parent-id 550e8400-e29b-41d4-a716-446655440000 \
  --child-id 7a3b2c1d-e4f5-6789-abcd-ef0123456789 \
  --budget 100.00 \
  --output delegation-token.jwt
```

</details>

---

## list

List all delegations.

```
caracal delegation list [OPTIONS]
```

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--parent-id` | `-p` | - | Filter by parent agent |
| `--child-id` | `-c` | - | Filter by child agent |
| `--status` | `-s` | active | Status: active, expired, revoked, all |
| `--format` | `-f` | table | Output format |

### Examples

<details>
<summary>List Active Delegations</summary>

```bash
caracal delegation list
```

**Output:**
```
Active Delegations
==================

Token ID           Parent         Child          Budget         Window    Expires
------------------------------------------------------------------------------------
tok-001-aaaa-...   orchestrator   worker-1       $100.00/day    daily     Never
tok-002-aaaa-...   orchestrator   worker-2       $200.00/day    daily     2024-12-31
tok-003-aaaa-...   orchestrator   worker-3       $50.00/day     daily     Never

Total: 3 active delegations
Combined budget exposure: $350.00/day
```

</details>

<details>
<summary>Filter by Parent</summary>

```bash
caracal delegation list --parent-id 550e8400-e29b-41d4-a716-446655440000
```

</details>

<details>
<summary>Include All Statuses</summary>

```bash
caracal delegation list --status all
```

**Output:**
```
All Delegations
===============

Token ID       Parent        Child         Budget        Status     Reason
--------------------------------------------------------------------------------
tok-001-...    orchestrator  worker-1      $100.00/day   active     -
tok-002-...    orchestrator  worker-2      $200.00/day   expired    Date passed
tok-003-...    orchestrator  worker-3      $50.00/day    revoked    Budget exceeded

Total: 3 delegations (1 active, 1 expired, 1 revoked)
```

</details>

---

## validate

Validate a delegation token.

```
caracal delegation validate [OPTIONS]
```

### Options

| Option | Short | Required | Description |
|--------|-------|:--------:|-------------|
| `--token` | `-t` | Yes | JWT token string or path to file |
| `--verbose` | `-v` | No | Show detailed validation steps |

### Examples

<details>
<summary>Validate Token</summary>

```bash
caracal delegation validate --token "eyJhbGciOiJFZERTQSIs..."
```

**Output:**
```
Token Validation
================

  Signature:        [OK] Valid (Ed25519)
  Not Expired:      [OK] No expiration set
  Not Revoked:      [OK] Token is active
  Parent Exists:    [OK] orchestrator (550e8400-...)
  Child Exists:     [OK] worker-1 (7a3b2c1d-...)
  Budget Valid:     [OK] $100.00 within parent limit

Result: [OK] Token is valid

Token Details
-------------
  Token ID:     tok-001-aaaa-bbbb-cccc
  Issued:       2024-01-15T10:00:00Z
  Budget:       $100.00 USD / daily
  Remaining:    $76.55 USD (current period)
```

</details>

<details>
<summary>Verbose Validation</summary>

```bash
caracal delegation validate --token ./delegation-token.jwt --verbose
```

**Output:**
```
Token Validation (Verbose)
==========================

Step 1: Parse JWT
  [OK] Valid JWT structure
  [OK] Algorithm: EdDSA
  [OK] Type: JWT

Step 2: Verify Signature
  [OK] Key ID: key-001-aaaa-bbbb
  [OK] Signature verified with public key
  [OK] Signature algorithm: Ed25519

Step 3: Check Claims
  [OK] Issuer: caracal-core
  [OK] Subject: 7a3b2c1d-e4f5-6789-abcd-ef0123456789
  [OK] Audience: caracal-gateway
  [OK] Issued At: 2024-01-15T10:00:00Z
  [OK] Expiration: None (no expiry)

Step 4: Verify Agents
  [OK] Parent agent exists: orchestrator
  [OK] Child agent exists: worker-1
  [OK] Parent-child relationship valid

Step 5: Check Revocation
  [OK] Token not in revocation list
  [OK] Parent delegation not revoked

Step 6: Verify Budget
  [OK] Delegated: $100.00 USD / daily
  [OK] Parent budget: $1000.00 USD / monthly
  [OK] Child spending: $23.45 (current period)
  [OK] Remaining: $76.55

Result: [OK] Token is valid and can be used
```

</details>

### Invalid Token Examples

| Error | Cause |
|-------|-------|
| Token has expired | Expiration date has passed |
| Token was revoked | Parent revoked the delegation |
| Parent agent not found | Parent was deleted |
| Budget exceeded | Child has exceeded delegated amount |

---

## revoke

Revoke a delegation.

```
caracal delegation revoke [OPTIONS]
```

### Options

| Option | Short | Required | Description |
|--------|-------|:--------:|-------------|
| `--token-id` | `-t` | Yes | Token ID to revoke |
| `--reason` | `-r` | No | Reason for revocation |
| `--force` | | No | Skip confirmation prompt |

### Examples

<details>
<summary>Revoke with Reason</summary>

```bash
caracal delegation revoke \
  --token-id tok-001-aaaa-bbbb-cccc \
  --reason "Budget exceeded - security measure"
```

**Output:**
```
[WARNING] Are you sure you want to revoke this delegation?

  Token ID:  tok-001-aaaa-bbbb-cccc
  Parent:    orchestrator
  Child:     worker-1
  Budget:    $100.00/day

  This action cannot be undone.
  Type 'revoke' to confirm: revoke

[OK] Delegation revoked successfully

  Token ID:       tok-001-aaaa-bbbb-cccc
  Revoked At:     2024-01-15T16:30:00Z
  Reason:         Budget exceeded - security measure
  
  The child agent can no longer use this delegation.
```

</details>

<details>
<summary>Force Revoke</summary>

```bash
caracal delegation revoke \
  --token-id tok-001-aaaa-bbbb-cccc \
  --reason "Automated security response" \
  --force
```

</details>

---

## Spending Tracking

When a child agent spends using a delegation:

| Step | Description |
|------|-------------|
| 1 | Child's spending is recorded in the ledger |
| 2 | Parent's budget is decremented by the same amount |
| 3 | Delegation chain is recorded for audit |
| 4 | Both limits are enforced (child AND parent) |

### Related Commands

```bash
# See spending by child agent
caracal ledger summary --agent-id <child-id>

# See delegation chain for an event
caracal ledger delegation-chain --event-id <event-id>

# See parent's total spending
caracal ledger summary --agent-id <parent-id>
```

---

## Best Practices

### Security

| Practice | Description |
|----------|-------------|
| Short-lived tokens | Use expiration for temporary delegations |
| Revoke immediately | When access is no longer needed |
| Least privilege | Delegate minimum required budget |
| Monitor spending | Set up alerts for unusual patterns |

### Automation Script

<details>
<summary>Provision Worker Script</summary>

```bash
#!/bin/bash
# provision-worker.sh - Provision new worker with delegation

PARENT_ID="550e8400-e29b-41d4-a716-446655440000"
WORKER_NAME="$1"
BUDGET="$2"

# Register worker agent
WORKER_ID=$(caracal agent register \
  --name "$WORKER_NAME" \
  --owner "ops@company.com" \
  --parent-id "$PARENT_ID" \
  --format json | jq -r '.agent_id')

# Generate delegation
caracal delegation generate \
  --parent-id "$PARENT_ID" \
  --child-id "$WORKER_ID" \
  --budget "$BUDGET" \
  --output "$WORKER_NAME-delegation.jwt"

echo "Worker provisioned: $WORKER_ID"
echo "Delegation saved to: $WORKER_NAME-delegation.jwt"
```

</details>

---

## See Also

- [Agent Commands](./agent) - Register parent and child agents
- [Policy Commands](./policy) - Set budget policies
- [Ledger Commands](./ledger) - View delegation chain
