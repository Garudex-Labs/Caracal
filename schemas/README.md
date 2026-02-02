# Caracal Core v0.3 - Avro Schemas

This directory contains Avro schemas for Kafka event types used in Caracal Core v0.3.

## Schema Files

### metering-event.avsc
Schema for metering events that track resource usage and costs.

**Topic**: `caracal.metering.events`

**Fields**:
- `event_id`: Unique event identifier (UUID)
- `schema_version`: Schema version for backward compatibility
- `timestamp`: Event timestamp (milliseconds since epoch)
- `agent_id`: Agent identifier
- `event_type`: Type of event (API_CALL, MCP_TOOL, DELEGATION, CHARGE)
- `resource_type`: Type of resource consumed
- `resource_uri`: URI of the resource accessed
- `quantity`: Quantity of resource consumed
- `unit`: Unit of measurement
- `cost`: Cost in specified currency
- `currency`: Currency code (ISO 4217)
- `provisional_charge_id`: Associated provisional charge ID
- `parent_agent_id`: Parent agent for delegated operations
- `correlation_id`: Correlation ID for tracing
- `metadata`: Additional metadata as key-value pairs

### policy-decision.avsc
Schema for policy evaluation decision events.

**Topic**: `caracal.policy.decisions`

**Fields**:
- `event_id`: Unique event identifier (UUID)
- `schema_version`: Schema version for backward compatibility
- `timestamp`: Event timestamp (milliseconds since epoch)
- `agent_id`: Agent identifier
- `policy_id`: Policy that was evaluated
- `decision`: ALLOW or DENY
- `reason`: Reason for the decision
- `requested_cost`: Requested cost for the operation
- `current_spending`: Current spending at evaluation time
- `budget_limit`: Budget limit from policy
- `time_window`: Time window for the policy
- `resource_uri`: Resource URI that was checked
- `allowlist_checked`: Whether allowlist was checked
- `allowlist_matched`: Whether resource matched allowlist
- `evaluation_duration_ms`: Time taken to evaluate policy
- `correlation_id`: Correlation ID for tracing
- `metadata`: Additional metadata as key-value pairs

### agent-lifecycle.avsc
Schema for agent lifecycle events.

**Topic**: `caracal.agent.lifecycle`

**Fields**:
- `event_id`: Unique event identifier (UUID)
- `schema_version`: Schema version for backward compatibility
- `timestamp`: Event timestamp (milliseconds since epoch)
- `agent_id`: Agent identifier
- `lifecycle_event`: Type of event (CREATED, UPDATED, DELETED, ACTIVATED, DEACTIVATED)
- `agent_name`: Human-readable agent name
- `parent_agent_id`: Parent agent for delegated agents
- `changed_by`: User or system that made the change
- `change_reason`: Reason for the lifecycle change
- `previous_state`: Previous agent state (for UPDATED events)
- `new_state`: New agent state (for UPDATED events)
- `correlation_id`: Correlation ID for tracing
- `metadata`: Additional metadata as key-value pairs

### policy-change.avsc
Schema for policy change events (versioning and audit trail).

**Topic**: `caracal.policy.changes`

**Fields**:
- `event_id`: Unique event identifier (UUID)
- `schema_version`: Schema version for backward compatibility
- `timestamp`: Event timestamp (milliseconds since epoch)
- `policy_id`: Policy identifier
- `version_number`: New version number after this change
- `change_type`: Type of change (CREATED, MODIFIED, DEACTIVATED)
- `agent_id`: Agent this policy applies to
- `limit_amount`: Budget limit amount
- `currency`: Currency code (ISO 4217)
- `time_window`: Time window for the policy
- `window_type`: ROLLING or CALENDAR
- `changed_by`: User or system that made the change
- `change_reason`: Reason for the policy change
- `previous_limit`: Previous limit amount (for MODIFIED events)
- `previous_time_window`: Previous time window (for MODIFIED events)
- `active`: Whether policy is active after this change
- `correlation_id`: Correlation ID for tracing
- `metadata`: Additional metadata as key-value pairs

## Schema Versioning Strategy

Caracal Core uses **backward compatibility** for schema evolution:

- **Backward compatible changes** (allowed):
  - Adding optional fields (with default values)
  - Removing fields
  - Adding enum symbols (at the end)

- **Breaking changes** (not allowed):
  - Removing required fields
  - Changing field types
  - Renaming fields
  - Removing enum symbols

When making schema changes:
1. Increment the `schema_version` field
2. Add new fields as optional with default values
3. Test compatibility with Schema Registry
4. Update consumers to handle new schema version

## Schema Registration

Schemas are registered with Confluent Schema Registry using the naming convention:
- `{topic-name}-value` for value schemas
- `{topic-name}-key` for key schemas (if needed)

Example subjects:
- `caracal.metering.events-value`
- `caracal.policy.decisions-value`
- `caracal.agent.lifecycle-value`
- `caracal.policy.changes-value`

## Usage

### Register Schemas

Run the registration script to register all schemas:

```bash
./scripts/register-schemas.sh
```

### View Registered Schemas

List all subjects:
```bash
curl http://localhost:8081/subjects
```

Get latest schema version:
```bash
curl http://localhost:8081/subjects/caracal.metering.events-value/versions/latest
```

Get specific schema version:
```bash
curl http://localhost:8081/subjects/caracal.metering.events-value/versions/1
```

### Check Compatibility

Test if a new schema is compatible:
```bash
curl -X POST -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data '{"schema": "{...}"}' \
  http://localhost:8081/compatibility/subjects/caracal.metering.events-value/versions/latest
```

### Update Schema

To update a schema:
1. Modify the `.avsc` file
2. Ensure changes are backward compatible
3. Run the registration script again
4. Schema Registry will assign a new version number

## Python Integration

### Install Dependencies

```bash
pip install confluent-kafka[avro]
```

### Producer Example

```python
from confluent_kafka import avro
from confluent_kafka.avro import AvroProducer

# Load schema
value_schema = avro.load('schemas/metering-event.avsc')

# Configure producer
producer_config = {
    'bootstrap.servers': 'localhost:9093',
    'schema.registry.url': 'http://localhost:8081',
    'security.protocol': 'SASL_SSL',
    'sasl.mechanism': 'SCRAM-SHA-512',
    'sasl.username': 'producer',
    'sasl.password': 'producer-secret',
}

producer = AvroProducer(producer_config, default_value_schema=value_schema)

# Produce event
event = {
    'event_id': str(uuid.uuid4()),
    'schema_version': 1,
    'timestamp': int(time.time() * 1000),
    'agent_id': 'agent-123',
    'event_type': 'API_CALL',
    'resource_type': 'openai.gpt-4',
    'quantity': 1000.0,
    'unit': 'tokens',
    'cost': 0.03,
    'currency': 'USD',
    'metadata': {}
}

producer.produce(topic='caracal.metering.events', value=event)
producer.flush()
```

### Consumer Example

```python
from confluent_kafka import avro
from confluent_kafka.avro import AvroConsumer

# Configure consumer
consumer_config = {
    'bootstrap.servers': 'localhost:9093',
    'schema.registry.url': 'http://localhost:8081',
    'group.id': 'my-consumer-group',
    'security.protocol': 'SASL_SSL',
    'sasl.mechanism': 'SCRAM-SHA-512',
    'sasl.username': 'consumer',
    'sasl.password': 'consumer-secret',
    'auto.offset.reset': 'earliest',
}

consumer = AvroConsumer(consumer_config)
consumer.subscribe(['caracal.metering.events'])

# Consume events
while True:
    msg = consumer.poll(1.0)
    if msg is None:
        continue
    if msg.error():
        print(f"Error: {msg.error()}")
        continue
    
    # Avro deserialization is automatic
    event = msg.value()
    print(f"Received event: {event['event_id']}")
    print(f"Agent: {event['agent_id']}")
    print(f"Cost: {event['cost']} {event['currency']}")
```

## Schema Evolution Example

### Version 1 (Initial)
```json
{
  "type": "record",
  "name": "MeteringEvent",
  "fields": [
    {"name": "event_id", "type": "string"},
    {"name": "agent_id", "type": "string"},
    {"name": "cost", "type": "double"}
  ]
}
```

### Version 2 (Add optional field - backward compatible)
```json
{
  "type": "record",
  "name": "MeteringEvent",
  "fields": [
    {"name": "event_id", "type": "string"},
    {"name": "agent_id", "type": "string"},
    {"name": "cost", "type": "double"},
    {"name": "currency", "type": "string", "default": "USD"}
  ]
}
```

Old consumers can still read new events (they ignore the `currency` field).
New consumers can read old events (they use the default value "USD").

## References

- [Apache Avro Documentation](https://avro.apache.org/docs/current/)
- [Confluent Schema Registry Documentation](https://docs.confluent.io/platform/current/schema-registry/index.html)
- [Schema Evolution and Compatibility](https://docs.confluent.io/platform/current/schema-registry/avro.html)
- [Python Avro Client](https://docs.confluent.io/kafka-clients/python/current/overview.html#avro-serializer-and-deserializer)
