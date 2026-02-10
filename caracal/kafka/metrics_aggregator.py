"""
MetricsAggregator Consumer for Caracal Core v0.3.

Consumes metering events from Kafka and updates real-time metrics in Redis
and Prometheus. Computes spending trends and detects anomalies.

Requirements: 2.2, 16.2, 16.3, 16.4, 16.5, 16.6
"""

import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any

from caracal.kafka.consumer import BaseKafkaConsumer, KafkaMessage, ConsumerConfig
from caracal.redis.client import RedisClient  # Kept for type hinting in __init__
from caracal.monitoring.metrics import MetricsRegistry
from caracal.logging_config import get_logger

logger = get_logger(__name__)


class MetricsAggregatorConsumer(BaseKafkaConsumer):
    """
    Kafka consumer for aggregating metrics from metering events.
    
    Subscribes to caracal.metering.events and:
    - Updates Redis spending cache
    - Updates Prometheus metrics (spending rate, event count)
    - Computes spending trends (hourly, daily, weekly)
    - Detects spending anomalies (spending > 2x average)
    - Publishes alert events when anomalies detected
    
    Requirements: 2.2, 16.2, 16.3, 16.4, 16.5, 16.6
    """
    
    # Topic to subscribe to
    TOPIC_METERING = "caracal.metering.events"
    
    # Consumer group
    CONSUMER_GROUP = "metrics-aggregator-group"
    
    # Anomaly detection threshold (2x average)
    ANOMALY_THRESHOLD_MULTIPLIER = 2.0
    
    # Historical window for anomaly detection (7 days)
    ANOMALY_HISTORICAL_WINDOW_DAYS = 7
    
    def __init__(
        self,
        brokers: List[str],
        redis_client: RedisClient,
        metrics_registry: MetricsRegistry,
        security_protocol: str = "PLAINTEXT",
        sasl_mechanism: Optional[str] = None,
        sasl_username: Optional[str] = None,
        sasl_password: Optional[str] = None,
        ssl_ca_location: Optional[str] = None,
        ssl_cert_location: Optional[str] = None,
        ssl_key_location: Optional[str] = None,
        consumer_config: Optional[ConsumerConfig] = None,
        enable_transactions: bool = True,
        enable_anomaly_detection: bool = False  # Deprecated
    ):
        """
        Initialize MetricsAggregator consumer.
        
        Args:
            brokers: List of Kafka broker addresses
            redis_client: RedisClient instance for caching
            metrics_registry: MetricsRegistry instance for Prometheus metrics
            security_protocol: Security protocol for Kafka
            sasl_mechanism: SASL mechanism for Kafka
            sasl_username: SASL username for Kafka
            sasl_password: SASL password for Kafka
            ssl_ca_location: Path to CA certificate
            ssl_cert_location: Path to client certificate
            ssl_key_location: Path to client private key
            consumer_config: ConsumerConfig instance
            enable_transactions: Enable exactly-once semantics
            enable_anomaly_detection: Deprecated
        """
        super().__init__(
            brokers=brokers,
            topics=[self.TOPIC_METERING],
            consumer_group=self.CONSUMER_GROUP,
            security_protocol=security_protocol,
            sasl_mechanism=sasl_mechanism,
            sasl_username=sasl_username,
            sasl_password=sasl_password,
            ssl_ca_location=ssl_ca_location,
            ssl_cert_location=ssl_cert_location,
            ssl_key_location=ssl_key_location,
            consumer_config=consumer_config,
            enable_transactions=enable_transactions
        )
        
        self.redis_client = redis_client
        # RedisSpendingCache removed as part of v0.5 refactor
        self.metrics_registry = metrics_registry
        
        # Initialize Prometheus metrics for v0.5
        self._initialize_metrics()
        
        logger.info(
            f"MetricsAggregatorConsumer initialized: "
            f"brokers={brokers}"
        )
    
    def _initialize_metrics(self):
        """Initialize Prometheus metrics."""
        from prometheus_client import Counter, Gauge
        
        # Event count metrics
        self.event_count_total = Counter(
            'caracal_metering_events_processed_total',
            'Total number of metering events processed',
            ['agent_id', 'resource_type'],
            registry=self.metrics_registry.registry
        )
        
        # Consumer lag metrics
        self.consumer_lag_gauge = Gauge(
            'caracal_metrics_aggregator_consumer_lag',
            'Consumer lag in number of messages',
            ['partition'],
            registry=self.metrics_registry.registry
        )
        
        logger.info("Prometheus metrics initialized")
    
    async def process_message(self, message: KafkaMessage) -> None:
        """
        Process metering event from Kafka.
        
        Steps:
        1. Deserialize event
        2. Update Prometheus metrics (event count)
        
        Args:
            message: Kafka message containing metering event
            
        Requirements: 2.2, 16.2
        """
        try:
            # Deserialize event
            event = message.deserialize_json()
            
            # Extract event fields
            event_id = event.get('event_id')
            agent_id = event.get('agent_id')
            resource_type = event.get('resource_type')
            
            logger.debug(
                f"Processing metering event: event_id={event_id}, "
                f"agent_id={agent_id}, resource={resource_type}"
            )
            
            # Update Prometheus metrics
            self._update_prometheus_metrics(
                agent_id=agent_id,
                resource_type=resource_type
            )
            
            logger.debug(
                f"Metering event processed successfully: event_id={event_id}"
            )
        
        except Exception as e:
            logger.error(
                f"Failed to process metering event: {e}",
                exc_info=True
            )
            raise
    
    def _update_prometheus_metrics(
        self,
        agent_id: str,
        resource_type: str
    ) -> None:
        """
        Update Prometheus metrics.
        
        Updates:
        - Event count (counter)
        
        Args:
            agent_id: Agent identifier
            resource_type: Resource type
        """
        try:
            # Increment event count
            self.event_count_total.labels(
                agent_id=agent_id,
                resource_type=resource_type
            ).inc()
            
            logger.debug(
                f"Updated Prometheus metrics: agent_id={agent_id}, event_count++"
            )
        
        except Exception as e:
            logger.error(
                f"Failed to update Prometheus metrics for agent {agent_id}: {e}",
                exc_info=True
            )
    

