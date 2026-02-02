#!/bin/bash
# Script to register Avro schemas with Confluent Schema Registry
# Requirements: 14.1, 14.2, 14.6, 14.7
#
# This script registers the following schemas:
# - MeteringEvent (caracal.metering.events-value)
# - PolicyDecision (caracal.policy.decisions-value)
# - AgentLifecycleEvent (caracal.agent.lifecycle-value)
# - PolicyChangeEvent (caracal.policy.changes-value)
#
# Schema compatibility mode: backward (allows adding optional fields)
#
# Usage:
#   ./scripts/register-schemas.sh
#
# Prerequisites:
#   - Schema Registry running (docker-compose -f docker-compose.kafka.yml up -d)
#   - Avro schema files in ./schemas directory

set -e

# Configuration
SCHEMA_REGISTRY_URL="http://localhost:8081"
SCHEMAS_DIR="./schemas"

echo "========================================="
echo "Schema Registry Registration Script"
echo "========================================="
echo ""

# Check if Schema Registry is running
echo "Checking Schema Registry connectivity..."
if ! curl -s -f "$SCHEMA_REGISTRY_URL/" > /dev/null; then
    echo "ERROR: Cannot connect to Schema Registry at $SCHEMA_REGISTRY_URL"
    echo "Make sure Schema Registry is running:"
    echo "  docker-compose -f docker-compose.kafka.yml up -d schema-registry"
    exit 1
fi
echo "✓ Schema Registry is running"
echo ""

# Function to register schema
register_schema() {
    local subject=$1
    local schema_file=$2
    local description=$3
    
    echo "Registering schema: $subject"
    echo "  Schema file: $schema_file"
    echo "  Description: $description"
    
    # Check if schema file exists
    if [ ! -f "$schema_file" ]; then
        echo "  ✗ Schema file not found: $schema_file"
        return 1
    fi
    
    # Read schema file and escape for JSON
    schema_content=$(cat "$schema_file" | jq -c .)
    
    # Create JSON payload
    payload=$(jq -n \
        --arg schema "$schema_content" \
        '{schema: $schema, schemaType: "AVRO"}')
    
    # Register schema
    response=$(curl -s -X POST \
        -H "Content-Type: application/vnd.schemaregistry.v1+json" \
        --data "$payload" \
        "$SCHEMA_REGISTRY_URL/subjects/$subject/versions")
    
    # Check response
    if echo "$response" | jq -e '.id' > /dev/null 2>&1; then
        schema_id=$(echo "$response" | jq -r '.id')
        echo "  ✓ Schema registered successfully (ID: $schema_id)"
    else
        echo "  ✗ Failed to register schema"
        echo "  Response: $response"
        return 1
    fi
    echo ""
}

# Function to set compatibility mode
set_compatibility() {
    local subject=$1
    local compatibility=$2
    
    echo "Setting compatibility mode for $subject to $compatibility..."
    
    payload=$(jq -n --arg compat "$compatibility" '{compatibility: $compat}')
    
    response=$(curl -s -X PUT \
        -H "Content-Type: application/vnd.schemaregistry.v1+json" \
        --data "$payload" \
        "$SCHEMA_REGISTRY_URL/config/$subject")
    
    if echo "$response" | jq -e '.compatibility' > /dev/null 2>&1; then
        echo "  ✓ Compatibility mode set to $compatibility"
    else
        echo "  ⚠ Failed to set compatibility mode (may already be set)"
    fi
    echo ""
}

# Register schemas
echo "Registering Caracal Core v0.3 schemas..."
echo ""

register_schema "caracal.metering.events-value" \
    "$SCHEMAS_DIR/metering-event.avsc" \
    "Metering events for resource usage tracking"

register_schema "caracal.policy.decisions-value" \
    "$SCHEMAS_DIR/policy-decision.avsc" \
    "Policy evaluation decision events"

register_schema "caracal.agent.lifecycle-value" \
    "$SCHEMAS_DIR/agent-lifecycle.avsc" \
    "Agent lifecycle events (created, updated, deleted)"

register_schema "caracal.policy.changes-value" \
    "$SCHEMAS_DIR/policy-change.avsc" \
    "Policy change events for versioning and audit"

# Set compatibility mode for all subjects
echo "Setting compatibility mode..."
echo ""

set_compatibility "caracal.metering.events-value" "BACKWARD"
set_compatibility "caracal.policy.decisions-value" "BACKWARD"
set_compatibility "caracal.agent.lifecycle-value" "BACKWARD"
set_compatibility "caracal.policy.changes-value" "BACKWARD"

# List all registered schemas
echo "========================================="
echo "Registered Schemas Summary"
echo "========================================="
echo ""

subjects=$(curl -s "$SCHEMA_REGISTRY_URL/subjects" | jq -r '.[]')

for subject in $subjects; do
    if [[ $subject == caracal.* ]]; then
        echo "Subject: $subject"
        
        # Get latest version
        latest_version=$(curl -s "$SCHEMA_REGISTRY_URL/subjects/$subject/versions/latest")
        schema_id=$(echo "$latest_version" | jq -r '.id')
        version=$(echo "$latest_version" | jq -r '.version')
        
        echo "  Schema ID: $schema_id"
        echo "  Version: $version"
        
        # Get compatibility mode
        compat=$(curl -s "$SCHEMA_REGISTRY_URL/config/$subject" | jq -r '.compatibilityLevel // "BACKWARD"')
        echo "  Compatibility: $compat"
        echo ""
    fi
done

echo "========================================="
echo "Schemas Registered Successfully!"
echo "========================================="
echo ""
echo "Schema Registry URL: $SCHEMA_REGISTRY_URL"
echo ""
echo "To view schemas:"
echo "  curl $SCHEMA_REGISTRY_URL/subjects"
echo ""
echo "To get schema details:"
echo "  curl $SCHEMA_REGISTRY_URL/subjects/caracal.metering.events-value/versions/latest"
echo ""
echo "Next steps:"
echo "1. Configure Caracal Core to use Schema Registry (update config.yaml)"
echo "2. Implement Kafka event producer with Avro serialization"
echo "3. Deploy event consumers"
echo ""
