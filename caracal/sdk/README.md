# Caracal Authority Enforcement SDK

The Caracal Authority Enforcement SDK provides a developer-friendly Python API for interacting with the Caracal Authority Enforcement system. It supports both synchronous and asynchronous operations.

## Features

- **Mandate Management**: Request, validate, and revoke execution mandates
- **Delegation**: Create delegated mandates with constrained scope
- **Ledger Queries**: Query the authority ledger for audit and compliance
- **Fail-Closed Semantics**: Errors result in denial to prevent unauthorized access
- **Connection Pooling**: Efficient HTTP connection management
- **Retry Logic**: Automatic retry with exponential backoff
- **Async Support**: Full async/await support with `AsyncAuthorityClient`

## Installation

The SDK is included with Caracal Core:

```bash
pip install caracal-core
```

## Quick Start

### Synchronous Client

```python
from caracal.sdk import AuthorityClient

# Initialize client
client = AuthorityClient(
    base_url="http://localhost:8000",
    api_key="your-api-key"  # Optional
)

# Request a mandate
mandate = client.request_mandate(
    issuer_id="admin-principal-id",
    subject_id="agent-principal-id",
    resource_scope=["api:openai:gpt-4"],
    action_scope=["api_call"],
    validity_seconds=3600  # 1 hour
)

# Validate the mandate
decision = client.validate_mandate(
    mandate_id=mandate['mandate_id'],
    requested_action="api_call",
    requested_resource="api:openai:gpt-4"
)

if decision['allowed']:
    print("Action authorized!")
else:
    print(f"Action denied: {decision['denial_reason']}")

# Clean up
client.close()
```

### Context Manager

```python
from caracal.sdk import AuthorityClient

# Automatically closes on exit
with AuthorityClient(base_url="http://localhost:8000") as client:
    mandate = client.request_mandate(
        issuer_id="admin-principal-id",
        subject_id="agent-principal-id",
        resource_scope=["api:openai:*"],
        action_scope=["api_call"],
        validity_seconds=3600
    )
    print(f"Mandate ID: {mandate['mandate_id']}")
```

### Async Client

```python
import asyncio
from caracal.sdk import AsyncAuthorityClient

async def main():
    async with AsyncAuthorityClient(base_url="http://localhost:8000") as client:
        # Request mandate asynchronously
        mandate = await client.request_mandate(
            issuer_id="admin-principal-id",
            subject_id="agent-principal-id",
            resource_scope=["api:openai:*"],
            action_scope=["api_call"],
            validity_seconds=3600
        )
        
        # Validate asynchronously
        decision = await client.validate_mandate(
            mandate_id=mandate['mandate_id'],
            requested_action="api_call",
            requested_resource="api:openai:gpt-4"
        )
        
        print(f"Allowed: {decision['allowed']}")

asyncio.run(main())
```

## API Reference

### AuthorityClient

#### `__init__(base_url, api_key=None, timeout=30, max_retries=3, backoff_factor=0.5)`

Initialize the authority client.

**Parameters:**
- `base_url` (str): Base URL of the Caracal authority service
- `api_key` (str, optional): API key for authentication
- `timeout` (int): Request timeout in seconds (default: 30)
- `max_retries` (int): Maximum retry attempts (default: 3)
- `backoff_factor` (float): Exponential backoff factor (default: 0.5)

#### `request_mandate(issuer_id, subject_id, resource_scope, action_scope, validity_seconds, intent=None, parent_mandate_id=None, metadata=None)`

Request a new execution mandate.

**Parameters:**
- `issuer_id` (str): Principal ID of the issuer
- `subject_id` (str): Principal ID of the subject
- `resource_scope` (List[str]): List of resource patterns
- `action_scope` (List[str]): List of allowed actions
- `validity_seconds` (int): Mandate validity period in seconds
- `intent` (dict, optional): Intent that constrains the mandate
- `parent_mandate_id` (str, optional): Parent mandate for delegation
- `metadata` (dict, optional): Additional metadata

**Returns:** Dictionary containing the execution mandate

**Raises:** `ConnectionError`, `SDKConfigurationError`

#### `validate_mandate(mandate_id, requested_action, requested_resource, mandate_data=None)`

Validate an execution mandate for a specific action.

**Parameters:**
- `mandate_id` (str): Mandate identifier
- `requested_action` (str): Action being requested
- `requested_resource` (str): Resource being accessed
- `mandate_data` (dict, optional): Full mandate data

**Returns:** Dictionary containing the authority decision

**Raises:** `ConnectionError`, `SDKConfigurationError`

#### `revoke_mandate(mandate_id, revoker_id, reason, cascade=True)`

Revoke an execution mandate.

**Parameters:**
- `mandate_id` (str): Mandate identifier to revoke
- `revoker_id` (str): Principal ID of the revoker
- `reason` (str): Reason for revocation
- `cascade` (bool): Revoke child mandates (default: True)

**Returns:** Dictionary containing revocation confirmation

**Raises:** `ConnectionError`, `SDKConfigurationError`

#### `query_ledger(principal_id=None, mandate_id=None, event_type=None, start_time=None, end_time=None, limit=100, offset=0)`

Query the authority ledger for events.

**Parameters:**
- `principal_id` (str, optional): Filter by principal ID
- `mandate_id` (str, optional): Filter by mandate ID
- `event_type` (str, optional): Filter by event type
- `start_time` (datetime, optional): Filter events after this time
- `end_time` (datetime, optional): Filter events before this time
- `limit` (int): Maximum events to return (default: 100)
- `offset` (int): Pagination offset (default: 0)

**Returns:** Dictionary containing events and metadata

**Raises:** `ConnectionError`, `SDKConfigurationError`

#### `delegate_mandate(parent_mandate_id, child_subject_id, resource_scope, action_scope, validity_seconds, metadata=None)`

Create a delegated mandate from a parent mandate.

**Parameters:**
- `parent_mandate_id` (str): Parent mandate identifier
- `child_subject_id` (str): Principal ID for child subject
- `resource_scope` (List[str]): Resource scope (subset of parent)
- `action_scope` (List[str]): Action scope (subset of parent)
- `validity_seconds` (int): Validity period (within parent validity)
- `metadata` (dict, optional): Additional metadata

**Returns:** Dictionary containing the delegated mandate

**Raises:** `ConnectionError`, `SDKConfigurationError`

#### `close()`

Close the HTTP session and release resources.

### AsyncAuthorityClient

The `AsyncAuthorityClient` provides the same methods as `AuthorityClient`, but all methods are async and must be awaited.

## Error Handling

The SDK implements fail-closed semantics:

```python
from caracal.sdk import AuthorityClient
from caracal.exceptions import ConnectionError, SDKConfigurationError

client = AuthorityClient(base_url="http://localhost:8000")

try:
    mandate = client.request_mandate(
        issuer_id="admin-id",
        subject_id="agent-id",
        resource_scope=["api:openai:*"],
        action_scope=["api_call"],
        validity_seconds=3600
    )
except SDKConfigurationError as e:
    print(f"Configuration error: {e}")
except ConnectionError as e:
    print(f"Connection error: {e}")
    # Fail closed: deny the action
finally:
    client.close()
```

## Examples

See `examples/authority_client_demo.py` for complete examples.

## Requirements

- Python 3.11+
- requests (for synchronous client)
- aiohttp (for async client)
- Caracal authority service running

## License

See LICENSE file in the Caracal repository.
