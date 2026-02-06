---
slug: /
sidebar_position: 1
title: Welcome to Caracal
---

# Caracal

<p align="center">
  <img src="/img/caracal_inverted.png" width="200" alt="Caracal Logo" className="logo-dark" />
  <img src="/img/caracal.png" width="200" alt="Caracal Logo" className="logo-light" />
</p>

**Network-enforced policy enforcement and metering for AI agents.**

Caracal ensures your AI agents operate within defined economic boundaries with cryptographic proof of all spending events.

## Products

<div className="row">
  <div className="col col--6">
    <div className="card">
      <div className="card__header">
        <h3>Caracal Core</h3>
      </div>
      <div className="card__body">
        <p>The policy enforcement engine. Includes Gateway Proxy, Ledger, SDK, and CLI tools.</p>
      </div>
      <div className="card__footer">
        <a className="button button--primary button--block" href="/caracalCore">Get Started</a>
      </div>
    </div>
  </div>
  <div className="col col--6">
    <div className="card">
      <div className="card__header">
        <h3>Caracal Flow</h3>
      </div>
      <div className="card__body">
        <p>Terminal UI for managing Caracal. Configure agents, policies, and view spending interactively.</p>
      </div>
      <div className="card__footer">
        <a className="button button--secondary button--block" href="/caracalFlow">Explore</a>
      </div>
    </div>
  </div>
</div>

---

## Core vs Flow Comparison

| Feature | Caracal Core | Caracal Flow |
|---------|:------------:|:------------:|
| **Interface** | CLI + SDK | Terminal UI |
| **Best For** | Automation, scripts, CI/CD | Interactive management |
| **Agent Registration** | Yes | Yes |
| **Policy Creation** | Yes | Yes |
| **Spending Queries** | Yes | Yes |
| **Merkle Verification** | Yes | No |
| **Key Rotation** | Yes | No |
| **Event Replay** | Yes | No |
| **DLQ Management** | Yes | No |
| **Batch Operations** | Yes | No |
| **Onboarding Wizard** | No | Yes |
| **Visual Menus** | No | Yes |

**Rule:** Use Flow for interactive work, use Core CLI for automation or advanced operations.

---

## Architecture Overview

```
+------------------------------------------------------------------+
|                       AI AGENT APPLICATIONS                      |
+------------------------------------------------------------------+
                               |
                               | HTTP Requests
                               v
+------------------------------------------------------------------+
|                     CARACAL GATEWAY PROXY                        |
|                                                                  |
|  +----------------+  +----------------+  +------------------+    |
|  | Authenticate   |->| Evaluate       |->| Record Spending  |    |
|  | Request        |  | Policy         |  | to Ledger        |    |
|  +----------------+  +----------------+  +------------------+    |
+------------------------------------------------------------------+
                               |
         +---------------------+---------------------+
         |                     |                     |
         v                     v                     v
+----------------+   +------------------+   +----------------+
|    POLICY      |   |     LEDGER       |   |    MERKLE      |
|    ENGINE      |   |   (Immutable)    |   |     TREE       |
+----------------+   +------------------+   +----------------+
         |                     |                     |
         +---------------------+---------------------+
                               |
                               v
                     +------------------+
                     |    PostgreSQL    |
                     +------------------+
```

---

## CLI Quick Reference

| Task | Command |
|------|---------|
| Initialize Caracal | `caracal init` |
| Register agent | `caracal agent register --name NAME --owner OWNER` |
| List agents | `caracal agent list` |
| Create policy | `caracal policy create --agent-id ID --limit 100.00` |
| Query ledger | `caracal ledger query --agent-id ID` |
| Spending summary | `caracal ledger summary --agent-id ID` |
| Database status | `caracal db status` |
| Verify integrity | `caracal merkle verify` |

See [CLI Reference](/caracalCore/cliReference/) for complete documentation.

---

## SDK Quick Start

```python
from decimal import Decimal
from caracal.sdk.client import CaracalClient

# Initialize client
client = CaracalClient()

# Check budget before expensive operation
if client.check_budget("my-agent-id"):
    result = call_ai_api()
    
    # Record the spending
    client.emit_event(
        agent_id="my-agent-id",
        resource_type="openai.gpt-4.output_tokens",
        quantity=Decimal("500")
    )
```

See [SDK Reference](/caracalCore/apiReference/sdkClient) for complete documentation.

---

## Quick Links

| Category | Links |
|----------|-------|
| Getting Started | [Installation](/caracalCore/gettingStarted/installation) - [Quickstart](/caracalCore/gettingStarted/quickstart) |
| CLI Reference | [Commands](/caracalCore/cliReference/) - [Agent](/caracalCore/cliReference/agent) - [Policy](/caracalCore/cliReference/policy) |
| API Reference | [SDK](/caracalCore/apiReference/sdkClient) - [MCP](/caracalCore/apiReference/mcpIntegration) |
| Deployment | [Docker Compose](/caracalCore/deployment/dockerCompose) - [Kubernetes](/caracalCore/deployment/kubernetes) |
| Development | [Contributing](/development/contributing) - [FAQ](/faq) |

---

## Community

| Resource | Link |
|----------|------|
| GitHub | [Garudex-Labs/Caracal](https://github.com/Garudex-Labs/Caracal) |
| Discord | [Join Community](https://discord.gg/d32UBmsK7A) |
