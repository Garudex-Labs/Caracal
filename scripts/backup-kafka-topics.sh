#!/bin/bash
#
# Kafka Topic Backup Script for Caracal Core v0.3
#
# This script backs up Kafka topics by consuming all messages and storing them
# in JSON format. Useful for disaster recovery and data migration.
#
# Usage:
#   ./backup-kafka-topics.sh [options]
#
# Options:
#   --backup-dir DIR      Directory to store backups (default: /backups/kafka)
#   --topics TOPICS       Comma-separated list of topics to backup (default: all caracal topics)
#   --bootstrap-server    Kafka bootstrap server (default: localhost:9092)
#   --max-messages N      Maximum messages per topic (default: unlimited)
#   --retention-days N    Number of days to retain backups (default: 30)
#   --s3-bucket BUCKET    S3 bucket for backup storage (optional)
#   --s3-prefix PREFIX    S3 prefix for backups (default: kafka/)
#   --compress            Compress backup with gzip (default: true)
#
# Requirements: Deployment

set -euo pipefail

# Default configuration
BACKUP_DIR="${BACKUP_DIR:-/backups/kafka}"
TOPICS="${TOPICS:-caracal.metering.events,caracal.policy.decisions,caracal.agent.lifecycle,caracal.policy.changes,caracal.dlq}"
BOOTSTRAP_SERVER="${BOOTSTRAP_SERVER:-localhost:9092}"
MAX_MESSAGES="${MAX_MESSAGES:-}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
S3_BUCKET="${S3_BUCKET:-}"
S3_PREFIX="${S3_PREFIX:-kafka/}"
COMPRESS="${COMPRESS:-true}"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --backup-dir)
      BACKUP_DIR="$2"
      shift 2
      ;;
    --topics)
      TOPICS="$2"
      shift 2
      ;;
    --bootstrap-server)
      BOOTSTRAP_SERVER="$2"
      shift 2
      ;;
    --max-messages)
      MAX_MESSAGES="$2"
      shift 2
      ;;
    --retention-days)
      RETENTION_DAYS="$2"
      shift 2
      ;;
    --s3-bucket)
      S3_BUCKET="$2"
      shift 2
      ;;
    --s3-prefix)
      S3_PREFIX="$2"
      shift 2
      ;;
    --compress)
      COMPRESS="true"
      shift
      ;;
    --no-compress)
      COMPRESS="false"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Generate timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=========================================="
echo "Caracal Kafka Topic Backup"
echo "=========================================="
echo "Timestamp: $TIMESTAMP"
echo "Bootstrap server: $BOOTSTRAP_SERVER"
echo "Topics: $TOPICS"
echo "Compress: $COMPRESS"
echo "=========================================="

# Check if kafka-console-consumer is available
if ! command -v kafka-console-consumer &> /dev/null; then
  echo "ERROR: kafka-console-consumer not found"
  echo "Please install Kafka tools or run this script from a Kafka container"
  exit 1
fi

# Backup each topic
IFS=',' read -ra TOPIC_ARRAY <<< "$TOPICS"
TOTAL_TOPICS=${#TOPIC_ARRAY[@]}
CURRENT_TOPIC=0

for TOPIC in "${TOPIC_ARRAY[@]}"; do
  CURRENT_TOPIC=$((CURRENT_TOPIC + 1))
  echo ""
  echo "[$CURRENT_TOPIC/$TOTAL_TOPICS] Backing up topic: $TOPIC"
  
  # Generate backup filename
  if [ "$COMPRESS" = "true" ]; then
    BACKUP_FILE="$BACKUP_DIR/${TOPIC}_${TIMESTAMP}.json.gz"
  else
    BACKUP_FILE="$BACKUP_DIR/${TOPIC}_${TIMESTAMP}.json"
  fi
  
  # Build kafka-console-consumer command
  CONSUMER_CMD="kafka-console-consumer \
    --bootstrap-server $BOOTSTRAP_SERVER \
    --topic $TOPIC \
    --from-beginning \
    --timeout-ms 10000"
  
  # Add max messages if specified
  if [ -n "$MAX_MESSAGES" ]; then
    CONSUMER_CMD="$CONSUMER_CMD --max-messages $MAX_MESSAGES"
  fi
  
  # Consume messages and save to file
  START_TIME=$(date +%s)
  
  if [ "$COMPRESS" = "true" ]; then
    $CONSUMER_CMD 2>/dev/null | gzip > "$BACKUP_FILE" || true
  else
    $CONSUMER_CMD 2>/dev/null > "$BACKUP_FILE" || true
  fi
  
  END_TIME=$(date +%s)
  DURATION=$((END_TIME - START_TIME))
  
  # Count messages
  if [ "$COMPRESS" = "true" ]; then
    MESSAGE_COUNT=$(gunzip -c "$BACKUP_FILE" | wc -l)
  else
    MESSAGE_COUNT=$(wc -l < "$BACKUP_FILE")
  fi
  
  # Get backup size
  BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
  
  echo "  Messages backed up: $MESSAGE_COUNT"
  echo "  Backup size: $BACKUP_SIZE"
  echo "  Duration: ${DURATION}s"
  echo "  File: $BACKUP_FILE"
  
  # Upload to S3 if configured
  if [ -n "$S3_BUCKET" ]; then
    echo "  Uploading to S3..."
    S3_PATH="s3://$S3_BUCKET/$S3_PREFIX$(basename "$BACKUP_FILE")"
    
    if command -v aws &> /dev/null; then
      aws s3 cp "$BACKUP_FILE" "$S3_PATH"
      echo "  Uploaded to: $S3_PATH"
    else
      echo "  WARNING: aws CLI not found, skipping S3 upload"
    fi
  fi
done

# Cleanup old backups
echo ""
echo "Cleaning up old backups (retention: $RETENTION_DAYS days)..."
DELETED_COUNT=$(find "$BACKUP_DIR" -name "*_*.json*" -mtime +$RETENTION_DAYS -delete -print | wc -l)
echo "Deleted $DELETED_COUNT old backup(s)"

# Summary
echo ""
echo "=========================================="
echo "Backup completed successfully"
echo "=========================================="
echo "Topics backed up: $TOTAL_TOPICS"
echo "Backup directory: $BACKUP_DIR"
if [ -n "$S3_BUCKET" ]; then
  echo "S3 bucket: s3://$S3_BUCKET/$S3_PREFIX"
fi
echo "=========================================="

exit 0
