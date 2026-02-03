#!/bin/bash
# Script to create Kafka topics for Caracal Core v0.3
# Requirements: 1.1, 1.2, 1.3, 13.1, 13.2, 13.3, 13.5, 13.6
#
# This script creates the following topics:
# - caracal.metering.events (10 partitions)
# - caracal.policy.decisions (5 partitions)
# - caracal.agent.lifecycle (3 partitions)
# - caracal.policy.changes (3 partitions)
# - caracal.dlq (3 partitions for dead letter queue)
#
# All topics are configured with:
# - Replication factor: 3
# - Min in-sync replicas: 2
# - Retention: 30 days (720 hours)
# - Compression: snappy
#
# Usage:
#   ./scripts/create-kafka-topics.sh
#
# Prerequisites:
#   - Kafka cluster running (docker-compose -f docker-compose.kafka.yml up -d)
#   - SCRAM credentials created

set -e

# Configuration
KAFKA_BROKER="localhost:9093"
CONFIG_FILE="./kafka-certs/client.properties"
REPLICATION_FACTOR=3
MIN_INSYNC_REPLICAS=2
RETENTION_MS=$((30 * 24 * 60 * 60 * 1000))  # 30 days in milliseconds
COMPRESSION_TYPE="snappy"

echo "========================================="
echo "Kafka Topics Creation Script"
echo "========================================="
echo ""

# Check if Kafka is running
echo "Checking Kafka connectivity..."
if ! docker exec -it caracal-kafka-1 kafka-broker-api-versions \
    --bootstrap-server kafka-1:9092 \
    --command-config /etc/kafka/secrets/client.properties > /dev/null 2>&1; then
    echo "ERROR: Cannot connect to Kafka. Make sure Kafka cluster is running."
    echo "Start Kafka with: docker-compose -f docker-compose.kafka.yml up -d"
    exit 1
fi
echo "✓ Kafka is running"
echo ""

# Function to create topic
create_topic() {
    local topic_name=$1
    local partitions=$2
    local description=$3
    
    echo "Creating topic: $topic_name"
    echo "  Partitions: $partitions"
    echo "  Replication factor: $REPLICATION_FACTOR"
    echo "  Min in-sync replicas: $MIN_INSYNC_REPLICAS"
    echo "  Retention: 30 days"
    echo "  Compression: $COMPRESSION_TYPE"
    echo "  Description: $description"
    
    # Check if topic already exists
    if docker exec -it caracal-kafka-1 kafka-topics \
        --bootstrap-server kafka-1:9092 \
        --command-config /etc/kafka/secrets/client.properties \
        --list | grep -q "^${topic_name}$"; then
        echo "  ⚠ Topic already exists, skipping creation"
        echo ""
        return 0
    fi
    
    # Create topic
    docker exec -it caracal-kafka-1 kafka-topics \
        --bootstrap-server kafka-1:9092 \
        --command-config /etc/kafka/secrets/client.properties \
        --create \
        --topic "$topic_name" \
        --partitions "$partitions" \
        --replication-factor "$REPLICATION_FACTOR" \
        --config min.insync.replicas="$MIN_INSYNC_REPLICAS" \
        --config retention.ms="$RETENTION_MS" \
        --config compression.type="$COMPRESSION_TYPE" \
        --config cleanup.policy=delete
    
    if [ $? -eq 0 ]; then
        echo "  ✓ Topic created successfully"
    else
        echo "  ✗ Failed to create topic"
        return 1
    fi
    echo ""
}

# Create topics
echo "Creating Caracal Core v0.3 topics..."
echo ""

create_topic "caracal.metering.events" 10 \
    "Metering events from gateway proxy and MCP adapter"

create_topic "caracal.policy.decisions" 5 \
    "Policy evaluation decisions (allow/deny)"

create_topic "caracal.agent.lifecycle" 3 \
    "Agent lifecycle events (created, updated, deleted)"

create_topic "caracal.policy.changes" 3 \
    "Policy change events for versioning and audit trail"

create_topic "caracal.dlq" 3 \
    "Dead letter queue for failed event processing"

# List all topics
echo "========================================="
echo "Topic Summary"
echo "========================================="
echo ""
docker exec -it caracal-kafka-1 kafka-topics \
    --bootstrap-server kafka-1:9092 \
    --command-config /etc/kafka/secrets/client.properties \
    --list

echo ""
echo "========================================="
echo "Topic Details"
echo "========================================="
echo ""

# Describe each topic
for topic in "caracal.metering.events" "caracal.policy.decisions" "caracal.agent.lifecycle" "caracal.policy.changes" "caracal.dlq"; do
    echo "Topic: $topic"
    docker exec -it caracal-kafka-1 kafka-topics \
        --bootstrap-server kafka-1:9092 \
        --command-config /etc/kafka/secrets/client.properties \
        --describe \
        --topic "$topic"
    echo ""
done

echo "========================================="
echo "Topics Created Successfully!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Register Avro schemas in Schema Registry (see task 1.3)"
echo "2. Configure Caracal Core to use Kafka (update config.yaml)"
echo "3. Deploy event consumers (LedgerWriter, MetricsAggregator, AuditLogger)"
echo ""
