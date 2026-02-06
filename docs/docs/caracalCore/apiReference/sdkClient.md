---
sidebar_position: 1
title: SDK Client
---

# Caracal SDK

Python SDK for integrating budget checks and metering into AI agent applications.

---

## Installation

```bash
pip install caracal-core
```

Or with UV:

```bash
uv pip install caracal-core
```

---

## Quick Start

```python
from decimal import Decimal
from caracal.sdk.client import CaracalClient

# Initialize client
client = CaracalClient()

# Check budget before operation
if client.check_budget("my-agent-id"):
    result = call_ai_api()
    
    # Record the spending
    client.emit_event(
        agent_id="my-agent-id",
        resource_type="openai.gpt-4.output_tokens",
        quantity=Decimal("500")
    )
```

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
```

### Custom Configuration Path

```python
client = CaracalClient(config_path="/etc/caracal/config.yaml")
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `CARACAL_CONFIG` | Override default config path |
| `DB_PASSWORD` | Database password |

---

## API Reference

### CaracalClient

Main SDK client class.

#### Constructor

```python
CaracalClient(config_path: Optional[str] = None)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config_path` | str | `~/.caracal/config.yaml` | Path to configuration file |

**Raises:**
- `SDKConfigurationError` - Configuration is invalid
- `ConnectionError` - Initialization fails (fail-closed)

---

### Methods Overview

| Method | Description | Returns |
|--------|-------------|---------|
| `emit_event()` | Record spending event | None |
| `check_budget()` | Check if within budget | bool |
| `get_remaining_budget()` | Get remaining budget | Decimal |
| `budget_check()` | Context manager for budget checking | BudgetCheckContext |
| `create_child_agent()` | Create child agent with delegation | Dict |
| `get_delegation_token()` | Generate delegation token | str |
| `query_spending_with_children()` | Aggregate spending with children | Dict |

---

### emit_event

Record a spending event.

```python
emit_event(
    agent_id: str,
    resource_type: str,
    quantity: Decimal,
    metadata: Optional[Dict] = None
) -> None
```

| Parameter | Type | Required | Description |
|-----------|------|:--------:|-------------|
| `agent_id` | str | Yes | Agent identifier |
| `resource_type` | str | Yes | Resource type (e.g., `openai.gpt-4.output_tokens`) |
| `quantity` | Decimal | Yes | Amount consumed |
| `metadata` | Dict | No | Additional context |

**Raises:**
- `ConnectionError` - Event emission fails (fail-closed)

<details>
<summary>Example</summary>

```python
from decimal import Decimal
from caracal.sdk.client import CaracalClient

client = CaracalClient()

client.emit_event(
    agent_id="my-agent-id",
    resource_type="openai.gpt-4.output_tokens",
    quantity=Decimal("500"),
    metadata={
        "model": "gpt-4",
        "request_id": "req_123",
        "user": "user@example.com"
    }
)
```

</details>

---

### check_budget

Check if an agent is within budget.

```python
check_budget(agent_id: str) -> bool
```

| Parameter | Type | Required | Description |
|-----------|------|:--------:|-------------|
| `agent_id` | str | Yes | Agent identifier |

**Returns:** `True` if within budget, `False` otherwise.

**Fail-Closed Behavior:**
- Returns `False` if check fails
- Returns `False` if no policy exists
- Returns `False` on any error

<details>
<summary>Example</summary>

```python
client = CaracalClient()

if client.check_budget("my-agent-id"):
    # Agent is within budget
    result = call_expensive_api()
else:
    # Budget exceeded or check failed
    print("Budget exceeded")
```

</details>

---

### get_remaining_budget

Get remaining budget for an agent.

```python
get_remaining_budget(agent_id: str) -> Optional[Decimal]
```

| Parameter | Type | Required | Description |
|-----------|------|:--------:|-------------|
| `agent_id` | str | Yes | Agent identifier |

**Returns:** Remaining budget as `Decimal`, or `None` if check fails.

<details>
<summary>Example</summary>

```python
from decimal import Decimal

client = CaracalClient()

remaining = client.get_remaining_budget("my-agent-id")

if remaining and remaining > Decimal("10.00"):
    # Sufficient budget
    result = call_expensive_api()
else:
    print(f"Insufficient budget: {remaining}")
```

</details>

---

### budget_check

Context manager for budget checking.

```python
budget_check(agent_id: str) -> BudgetCheckContext
```

| Parameter | Type | Required | Description |
|-----------|------|:--------:|-------------|
| `agent_id` | str | Yes | Agent identifier |

**Returns:** `BudgetCheckContext` context manager.

**Raises:**
- `BudgetExceededError` - On context entry if budget exceeded

<details>
<summary>Example</summary>

```python
from decimal import Decimal
from caracal.exceptions import BudgetExceededError

client = CaracalClient()

try:
    with client.budget_check(agent_id="my-agent"):
        # Code that incurs costs
        result = call_expensive_api()
        
        # Emit metering event manually
        client.emit_event(
            agent_id="my-agent",
            resource_type="openai.gpt-4.output_tokens",
            quantity=Decimal("500")
        )
except BudgetExceededError as e:
    print(f"Budget exceeded: {e}")
```

</details>

---

### create_child_agent

Create a child agent with optional delegated budget.

```python
create_child_agent(
    parent_agent_id: str,
    child_name: str,
    child_owner: str,
    delegated_budget: Optional[Decimal] = None,
    budget_currency: str = "USD",
    budget_time_window: str = "daily",
    metadata: Optional[Dict] = None
) -> Dict[str, Any]
```

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `parent_agent_id` | str | Yes | - | Parent agent ID |
| `child_name` | str | Yes | - | Unique child name |
| `child_owner` | str | Yes | - | Owner identifier |
| `delegated_budget` | Decimal | No | None | Budget to delegate |
| `budget_currency` | str | No | USD | Currency code |
| `budget_time_window` | str | No | daily | Time window |
| `metadata` | Dict | No | None | Agent metadata |

**Returns:** Dictionary with child agent details.

| Return Field | Description |
|--------------|-------------|
| `agent_id` | Child agent ID |
| `name` | Child name |
| `owner` | Child owner |
| `parent_agent_id` | Parent ID |
| `delegation_token` | JWT token (if budget specified) |
| `policy_id` | Policy ID (if budget specified) |

<details>
<summary>Example</summary>

```python
from decimal import Decimal

client = CaracalClient()

child = client.create_child_agent(
    parent_agent_id="parent-uuid",
    child_name="worker-1",
    child_owner="team@example.com",
    delegated_budget=Decimal("100.00"),
    budget_currency="USD",
    budget_time_window="daily"
)

print(f"Created child: {child['agent_id']}")
print(f"Delegation token: {child['delegation_token']}")
```

</details>

---

### get_delegation_token

Generate delegation token for existing child agent.

```python
get_delegation_token(
    parent_agent_id: str,
    child_agent_id: str,
    spending_limit: Decimal,
    currency: str = "USD",
    expiration_seconds: int = 86400,
    allowed_operations: Optional[List[str]] = None
) -> Optional[str]
```

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `parent_agent_id` | str | Yes | - | Parent agent ID |
| `child_agent_id` | str | Yes | - | Child agent ID |
| `spending_limit` | Decimal | Yes | - | Maximum spending |
| `currency` | str | No | USD | Currency code |
| `expiration_seconds` | int | No | 86400 | Token validity (24h default) |
| `allowed_operations` | List[str] | No | None | Allowed operations |

**Returns:** JWT delegation token string.

<details>
<summary>Example</summary>

```python
from decimal import Decimal

client = CaracalClient()

token = client.get_delegation_token(
    parent_agent_id="parent-uuid",
    child_agent_id="child-uuid",
    spending_limit=Decimal("50.00"),
    currency="USD",
    expiration_seconds=3600  # 1 hour
)

print(f"Token: {token}")
```

</details>

---

### query_spending_with_children

Query spending for agent including all children.

```python
query_spending_with_children(
    agent_id: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    include_breakdown: bool = False
) -> Dict[str, Any]
```

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `agent_id` | str | Yes | - | Parent agent ID |
| `start_time` | datetime | No | Start of day | Query start |
| `end_time` | datetime | No | Now | Query end |
| `include_breakdown` | bool | No | False | Include hierarchy |

**Returns:** Spending summary dictionary.

| Return Field | Description |
|--------------|-------------|
| `agent_id` | Parent agent ID |
| `own_spending` | Parent's own spending |
| `children_spending` | Total child spending |
| `total_spending` | Combined spending |
| `agent_count` | Number of agents included |
| `breakdown` | Hierarchical breakdown (if requested) |

<details>
<summary>Example</summary>

```python
from datetime import datetime, timedelta

client = CaracalClient()

end = datetime.utcnow()
start = end - timedelta(days=1)

result = client.query_spending_with_children(
    agent_id="parent-uuid",
    start_time=start,
    end_time=end,
    include_breakdown=True
)

print(f"Total: {result['total_spending']}")
print(f"Parent: {result['own_spending']}")
print(f"Children: {result['children_spending']}")
```

</details>

---

## Accessing Caracal Data

The SDK provides access to internal components for advanced use cases.

### Get Agent List

<details>
<summary>Example</summary>

```python
client = CaracalClient()

# Access agent registry directly
agents = client.agent_registry.list_agents()

for agent in agents:
    print(f"Agent: {agent.name} ({agent.agent_id})")
    print(f"  Owner: {agent.owner}")
    print(f"  Parent: {agent.parent_agent_id}")
```

</details>

### Get Policies for Agent

<details>
<summary>Example</summary>

```python
client = CaracalClient()

# Get policies for a specific agent
policies = client.policy_store.get_policies("agent-uuid")

for policy in policies:
    print(f"Policy: {policy.policy_id}")
    print(f"  Limit: {policy.limit_amount} {policy.currency}")
    print(f"  Window: {policy.time_window}")
```

</details>

### Query Ledger Events

<details>
<summary>Example</summary>

```python
from datetime import datetime, timedelta

client = CaracalClient()

end = datetime.utcnow()
start = end - timedelta(hours=1)

# Query recent events
events = client.ledger_query.query_events(
    agent_id="agent-uuid",
    start_time=start,
    end_time=end
)

for event in events:
    print(f"Event: {event.event_id}")
    print(f"  Amount: {event.amount}")
    print(f"  Operation: {event.operation_type}")
```

</details>

### Get Pricebook Entries

<details>
<summary>Example</summary>

```python
client = CaracalClient()

# List all prices
prices = client.pricebook.list_prices()

for price in prices:
    print(f"{price.resource_type}: ${price.price}")

# Get specific price
gpt4_price = client.pricebook.get_price("openai.gpt-4.output_tokens")
print(f"GPT-4 output: ${gpt4_price.price} per token")
```

</details>

---

## Fail-Closed Semantics

The SDK implements fail-closed behavior to prevent unchecked spending.

| Scenario | Behavior |
|----------|----------|
| Initialization failure | Raises `ConnectionError` |
| Event emission failure | Raises `ConnectionError` |
| Budget check failure | Returns `False` (deny) |
| Missing policy | Returns `False` (deny) |
| Any unexpected error | Deny/raise exception |

---

## Error Handling

<details>
<summary>Example Error Handling</summary>

```python
from caracal.sdk.client import CaracalClient
from caracal.exceptions import (
    ConnectionError,
    BudgetExceededError,
    SDKConfigurationError
)

# Handle initialization errors
try:
    client = CaracalClient(config_path="/invalid/path.yaml")
except SDKConfigurationError as e:
    print(f"Configuration error: {e}")
except ConnectionError as e:
    print(f"Connection error: {e}")

# Handle event emission errors
try:
    client.emit_event(
        agent_id="my-agent",
        resource_type="openai.gpt-4.input_tokens",
        quantity=Decimal("1000")
    )
except ConnectionError as e:
    print(f"Failed to emit event: {e}")

# Handle budget check errors
try:
    with client.budget_check("my-agent"):
        result = call_api()
except BudgetExceededError as e:
    print(f"Budget exceeded: {e}")
```

</details>

---

## Integration Examples

### With OpenAI

<details>
<summary>OpenAI Integration</summary>

```python
from decimal import Decimal
import openai
from caracal.sdk.client import CaracalClient

client = CaracalClient()
AGENT_ID = "my-agent"

def chat_with_budget(messages):
    # Check budget first
    if not client.check_budget(AGENT_ID):
        raise Exception("Budget exceeded")
    
    # Call OpenAI
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages
    )
    
    # Calculate tokens
    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens
    
    # Record spending
    client.emit_event(
        agent_id=AGENT_ID,
        resource_type="openai.gpt-4.input_tokens",
        quantity=Decimal(str(input_tokens))
    )
    client.emit_event(
        agent_id=AGENT_ID,
        resource_type="openai.gpt-4.output_tokens",
        quantity=Decimal(str(output_tokens))
    )
    
    return response.choices[0].message.content
```

</details>

### With LangChain

<details>
<summary>LangChain Integration</summary>

```python
from decimal import Decimal
from langchain.callbacks.base import BaseCallbackHandler
from caracal.sdk.client import CaracalClient

class CaracalCallback(BaseCallbackHandler):
    def __init__(self, agent_id: str):
        self.client = CaracalClient()
        self.agent_id = agent_id
    
    def on_llm_end(self, response, **kwargs):
        # Get token counts from response
        if hasattr(response, 'llm_output'):
            usage = response.llm_output.get('token_usage', {})
            
            if 'prompt_tokens' in usage:
                self.client.emit_event(
                    agent_id=self.agent_id,
                    resource_type="openai.gpt-4.input_tokens",
                    quantity=Decimal(str(usage['prompt_tokens']))
                )
            
            if 'completion_tokens' in usage:
                self.client.emit_event(
                    agent_id=self.agent_id,
                    resource_type="openai.gpt-4.output_tokens",
                    quantity=Decimal(str(usage['completion_tokens']))
                )

# Usage
callback = CaracalCallback("my-agent")
llm = ChatOpenAI(callbacks=[callback])
```

</details>

---

## See Also

- [MCP Integration](/caracalCore/apiReference/mcpIntegration) - Model Context Protocol
- [CLI Reference](/caracalCore/cliReference/) - Command-line tools
