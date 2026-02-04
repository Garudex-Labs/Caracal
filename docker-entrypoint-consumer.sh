#!/bin/bash
set -e

# Wait for dependencies if necessary (handled by Docker/K8s usually)
echo "Starting Caracal Consumer: $CONSUMER_TYPE"

# Run the python module corresponding to the consumer type
if [ "$CONSUMER_TYPE" = "ledger-writer" ]; then
    exec python -m caracal.core.ledger.consumer
elif [ "$CONSUMER_TYPE" = "metrics-aggregator" ]; then
    exec python -m caracal.monitoring.metrics.consumer
elif [ "$CONSUMER_TYPE" = "audit-logger" ]; then
    exec python -m caracal.core.audit.consumer
else
    echo "Unknown CONSUMER_TYPE: $CONSUMER_TYPE"
    exit 1
fi
