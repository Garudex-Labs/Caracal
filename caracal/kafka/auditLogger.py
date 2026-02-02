"""
AuditLogger Consumer for Caracal Core v0.3.

Consumes all events from Kafka topics and writes to append-only audit log.
Provides comprehensive audit trail for compliance and forensic analysis.

Requirements: 17.1, 17.2, 17.3, 17.4
"""

import json
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from caracal.kafka.consumer import BaseKafkaConsumer, KafkaMessage
from caracal.db.models import AuditLog
from caracal.db.connection import get_session
from caracal.logging_config import get_logger

logger = get_logger(__name__)


class AuditLoggerConsumer(BaseKafkaConsumer):
    """
    Audit logger consumer that writes all events to append-only audit log.
    
    Subscribes to all Kafka topics:
    - caracal.metering.events
    - caracal.policy.decisions
    - caracal.agent.lifecycle
    - caracal.policy.changes
    
    For each event:
    1. Deserialize event data
    2. Extract correlation ID from metadata
    3. Write to audit_logs table (append-only)
    4. Never update or delete audit log entries
    
    Requirements: 17.1, 17.2, 17.3, 17.4
    """
    
    # All topics to audit
    AUDIT_TOPICS = [
        "caracal.metering.events",
        "caracal.policy.decisions",
        "caracal.agent.lifecycle",
        "caracal.policy.changes",
    ]
    
    def __init__(
        self,
        brokers: List[str],
        security_protocol: str = "PLAINTEXT",
        sasl_mechanism: Optional[str] = None,
        sasl_username: Optional[str] = None,
        sasl_password: Optional[str] = None,
        ssl_ca_location: Optional[str] = None,
        ssl_cert_location: Optional[str] = None,
        ssl_key_location: Optional[str] = None,
        db_session_factory=None,
    ):
        """
        Initialize AuditLogger consumer.
        
        Args:
            brokers: List of Kafka broker addresses
            security_protocol: Security protocol ('PLAINTEXT', 'SSL', 'SASL_PLAINTEXT', 'SASL_SSL')
            sasl_mechanism: SASL mechanism ('PLAIN', 'SCRAM-SHA-256', 'SCRAM-SHA-512')
            sasl_username: SASL username
            sasl_password: SASL password
            ssl_ca_location: Path to CA certificate
            ssl_cert_location: Path to client certificate
            ssl_key_location: Path to client private key
            db_session_factory: Database session factory (defaults to get_session)
        """
        super().__init__(
            brokers=brokers,
            topics=self.AUDIT_TOPICS,
            consumer_group="audit-logger-group",
            security_protocol=security_protocol,
            sasl_mechanism=sasl_mechanism,
            sasl_username=sasl_username,
            sasl_password=sasl_password,
            ssl_ca_location=ssl_ca_location,
            ssl_cert_location=ssl_cert_location,
            ssl_key_location=ssl_key_location,
            enable_transactions=True,
        )
        
        self.db_session_factory = db_session_factory or get_session
        
        logger.info(
            f"AuditLoggerConsumer initialized: topics={self.AUDIT_TOPICS}"
        )
    
    async def process_message(self, message: KafkaMessage) -> None:
        """
        Process event and write to audit log.
        
        Steps:
        1. Deserialize event data from JSON
        2. Extract event metadata (event_id, event_type, agent_id, correlation_id)
        3. Create audit log entry with full event data
        4. Write to audit_logs table (append-only)
        5. Never update or delete existing entries
        
        Args:
            message: Kafka message containing event data
            
        Requirements: 17.1, 17.2, 17.3, 17.4
        """
        try:
            # Deserialize event data
            event_data = message.deserialize_json()
            
            # Extract event metadata
            event_id = event_data.get("event_id", "unknown")
            event_type = event_data.get("event_type", "unknown")
            
            # Extract agent_id (may be None for some event types)
            agent_id_str = event_data.get("agent_id")
            agent_id = UUID(agent_id_str) if agent_id_str else None
            
            # Extract correlation_id from metadata or headers
            correlation_id = None
            
            # Try to get from event metadata
            if "metadata" in event_data and isinstance(event_data["metadata"], dict):
                correlation_id = event_data["metadata"].get("correlation_id")
            
            # Try to get from message headers
            if not correlation_id and message.headers:
                correlation_id_bytes = message.headers.get("correlation_id")
                if correlation_id_bytes:
                    correlation_id = correlation_id_bytes.decode('utf-8')
            
            # Extract event timestamp
            event_timestamp = None
            if "timestamp" in event_data:
                # Handle both ISO format strings and Unix timestamps
                timestamp_value = event_data["timestamp"]
                if isinstance(timestamp_value, str):
                    event_timestamp = datetime.fromisoformat(timestamp_value.replace('Z', '+00:00'))
                elif isinstance(timestamp_value, (int, float)):
                    # Unix timestamp in milliseconds
                    event_timestamp = datetime.utcfromtimestamp(timestamp_value / 1000.0)
            
            if not event_timestamp:
                # Fall back to message timestamp
                if message.timestamp:
                    event_timestamp = datetime.utcfromtimestamp(message.timestamp / 1000.0)
                else:
                    event_timestamp = datetime.utcnow()
            
            # Create audit log entry
            audit_log = AuditLog(
                event_id=event_id,
                event_type=event_type,
                topic=message.topic,
                partition=message.partition,
                offset=message.offset,
                event_timestamp=event_timestamp,
                agent_id=agent_id,
                correlation_id=correlation_id,
                event_data=event_data,
            )
            
            # Write to database (append-only)
            with self.db_session_factory() as session:
                session.add(audit_log)
                session.commit()
            
            logger.debug(
                f"Audit log entry created: log_id={audit_log.log_id}, "
                f"event_type={event_type}, event_id={event_id}, "
                f"topic={message.topic}, offset={message.offset}"
            )
        
        except Exception as e:
            logger.error(
                f"Failed to process audit log message: topic={message.topic}, "
                f"partition={message.partition}, offset={message.offset}, error={e}",
                exc_info=True
            )
            raise  # Re-raise to trigger retry logic
