#!/bin/bash
#
# Snapshot-Based Recovery Script for Caracal Core v0.3
#
# This script performs snapshot-based recovery by:
# 1. Restoring from the latest snapshot
# 2. Replaying events from Kafka since the snapshot timestamp
# 3. Verifying ledger integrity
#
# Usage:
#   ./snapshot-recovery.sh [options]
#
# Options:
#   --snapshot-id ID      Snapshot ID to restore (default: latest)
#   --verify-integrity    Verify Merkle tree integrity after recovery (default: true)
#   --kubernetes          Use kubectl for Kubernetes deployment (default: false)
#   --namespace NS        Kubernetes namespace (default: caracal)
#
# Requirements: Deployment

set -euo pipefail

# Default configuration
SNAPSHOT_ID="${SNAPSHOT_ID:-latest}"
VERIFY_INTEGRITY="${VERIFY_INTEGRITY:-true}"
KUBERNETES="${KUBERNETES:-false}"
NAMESPACE="${NAMESPACE:-caracal}"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --snapshot-id)
      SNAPSHOT_ID="$2"
      shift 2
      ;;
    --verify-integrity)
      VERIFY_INTEGRITY="true"
      shift
      ;;
    --no-verify-integrity)
      VERIFY_INTEGRITY="false"
      shift
      ;;
    --kubernetes)
      KUBERNETES="true"
      shift
      ;;
    --namespace)
      NAMESPACE="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo "=========================================="
echo "Caracal Snapshot-Based Recovery"
echo "=========================================="
echo "Snapshot ID: $SNAPSHOT_ID"
echo "Verify integrity: $VERIFY_INTEGRITY"
echo "Kubernetes: $KUBERNETES"
echo "=========================================="

# Step 1: Stop all consumers
echo ""
echo "Step 1: Stopping Kafka consumers..."
if [ "$KUBERNETES" = "true" ]; then
  kubectl scale deployment/caracal-ledger-writer -n "$NAMESPACE" --replicas=0
  kubectl scale deployment/caracal-metrics-aggregator -n "$NAMESPACE" --replicas=0
  kubectl scale deployment/caracal-audit-logger -n "$NAMESPACE" --replicas=0
  
  echo "Waiting for consumers to stop..."
  sleep 10
else
  echo "WARNING: Not running in Kubernetes, please stop consumers manually"
  read -p "Press Enter when consumers are stopped..."
fi

echo "Consumers stopped"

# Step 2: List available snapshots
echo ""
echo "Step 2: Listing available snapshots..."
if [ "$SNAPSHOT_ID" = "latest" ]; then
  echo "Finding latest snapshot..."
  SNAPSHOT_LIST=$(caracal snapshot list --format json)
  SNAPSHOT_ID=$(echo "$SNAPSHOT_LIST" | jq -r '.[0].snapshot_id')
  
  if [ -z "$SNAPSHOT_ID" ] || [ "$SNAPSHOT_ID" = "null" ]; then
    echo "ERROR: No snapshots found"
    exit 1
  fi
  
  echo "Latest snapshot ID: $SNAPSHOT_ID"
fi

# Get snapshot details
SNAPSHOT_DETAILS=$(caracal snapshot get --snapshot-id "$SNAPSHOT_ID" --format json)
SNAPSHOT_TIMESTAMP=$(echo "$SNAPSHOT_DETAILS" | jq -r '.snapshot_timestamp')
SNAPSHOT_EVENT_COUNT=$(echo "$SNAPSHOT_DETAILS" | jq -r '.total_events')

echo "Snapshot timestamp: $SNAPSHOT_TIMESTAMP"
echo "Snapshot event count: $SNAPSHOT_EVENT_COUNT"

# Step 3: Restore from snapshot
echo ""
echo "Step 3: Restoring from snapshot..."
START_TIME=$(date +%s)

caracal snapshot restore --snapshot-id "$SNAPSHOT_ID"

END_TIME=$(date +%s)
RESTORE_DURATION=$((END_TIME - START_TIME))

echo "Snapshot restored successfully in ${RESTORE_DURATION}s"

# Step 4: Replay events from Kafka
echo ""
echo "Step 4: Replaying events from Kafka..."
echo "Replaying events since: $SNAPSHOT_TIMESTAMP"

REPLAY_START_TIME=$(date +%s)

caracal replay start \
  --from-timestamp "$SNAPSHOT_TIMESTAMP" \
  --consumer-group ledger-writer-group

# Monitor replay progress
echo "Monitoring replay progress..."
while true; do
  REPLAY_STATUS=$(caracal replay status --format json)
  REPLAY_STATE=$(echo "$REPLAY_STATUS" | jq -r '.state')
  EVENTS_PROCESSED=$(echo "$REPLAY_STATUS" | jq -r '.events_processed')
  
  echo "  State: $REPLAY_STATE, Events processed: $EVENTS_PROCESSED"
  
  if [ "$REPLAY_STATE" = "completed" ]; then
    break
  elif [ "$REPLAY_STATE" = "failed" ]; then
    echo "ERROR: Replay failed"
    exit 1
  fi
  
  sleep 5
done

REPLAY_END_TIME=$(date +%s)
REPLAY_DURATION=$((REPLAY_END_TIME - REPLAY_START_TIME))

echo "Event replay completed successfully in ${REPLAY_DURATION}s"
echo "Events replayed: $EVENTS_PROCESSED"

# Step 5: Verify ledger integrity
if [ "$VERIFY_INTEGRITY" = "true" ]; then
  echo ""
  echo "Step 5: Verifying ledger integrity..."
  
  VERIFY_START_TIME=$(date +%s)
  
  # Verify from snapshot timestamp to now
  VERIFY_RESULT=$(caracal merkle verify-range \
    --start-time "$SNAPSHOT_TIMESTAMP" \
    --end-time "now" \
    --format json)
  
  VERIFY_END_TIME=$(date +%s)
  VERIFY_DURATION=$((VERIFY_END_TIME - VERIFY_START_TIME))
  
  BATCHES_VERIFIED=$(echo "$VERIFY_RESULT" | jq -r '.batches_verified')
  BATCHES_PASSED=$(echo "$VERIFY_RESULT" | jq -r '.batches_passed')
  BATCHES_FAILED=$(echo "$VERIFY_RESULT" | jq -r '.batches_failed')
  
  echo "Batches verified: $BATCHES_VERIFIED"
  echo "Batches passed: $BATCHES_PASSED"
  echo "Batches failed: $BATCHES_FAILED"
  echo "Verification duration: ${VERIFY_DURATION}s"
  
  if [ "$BATCHES_FAILED" -gt 0 ]; then
    echo "ERROR: Integrity verification failed"
    exit 1
  fi
  
  echo "Integrity verification: PASSED"
fi

# Step 6: Restart consumers
echo ""
echo "Step 6: Restarting Kafka consumers..."
if [ "$KUBERNETES" = "true" ]; then
  kubectl scale deployment/caracal-ledger-writer -n "$NAMESPACE" --replicas=3
  kubectl scale deployment/caracal-metrics-aggregator -n "$NAMESPACE" --replicas=2
  kubectl scale deployment/caracal-audit-logger -n "$NAMESPACE" --replicas=1
  
  echo "Consumers restarted"
else
  echo "WARNING: Not running in Kubernetes, please restart consumers manually"
fi

# Summary
TOTAL_DURATION=$(($(date +%s) - START_TIME))

echo ""
echo "=========================================="
echo "Recovery completed successfully"
echo "=========================================="
echo "Snapshot ID: $SNAPSHOT_ID"
echo "Snapshot timestamp: $SNAPSHOT_TIMESTAMP"
echo "Snapshot events: $SNAPSHOT_EVENT_COUNT"
echo "Events replayed: $EVENTS_PROCESSED"
if [ "$VERIFY_INTEGRITY" = "true" ]; then
  echo "Batches verified: $BATCHES_VERIFIED"
  echo "Integrity: PASSED"
fi
echo "Total duration: ${TOTAL_DURATION}s"
echo "=========================================="

exit 0
