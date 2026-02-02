"""
Demo: LedgerWriter Consumer

This example demonstrates how to use the LedgerWriterConsumer to consume
metering events from Kafka and write them to PostgreSQL.

Requirements:
- Kafka broker running on localhost:9092
- PostgreSQL database configured
- caracal.metering.events topic created

Usage:
    python examples/ledger_writer_consumer_demo.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from caracal.kafka.ledger_writer import LedgerWriterConsumer
from caracal.db.connection import DatabaseConnectionManager
from caracal.config.settings import Settings
from caracal.logging_config import get_logger

logger = get_logger(__name__)


async def main():
    """Run LedgerWriter consumer demo."""
    
    # Load configuration
    settings = Settings()
    
    # Initialize database connection manager
    db_manager = DatabaseConnectionManager(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.database,
        user=settings.database.user,
        password=settings.database.password,
        pool_size=settings.database.pool_size,
        max_overflow=settings.database.max_overflow,
        pool_timeout=settings.database.pool_timeout
    )
    
    # Create session factory
    def session_factory():
        return db_manager.get_session()
    
    # Initialize LedgerWriter consumer
    consumer = LedgerWriterConsumer(
        brokers=settings.kafka.brokers,
        db_session_factory=session_factory,
        security_protocol=settings.kafka.security_protocol,
        sasl_mechanism=settings.kafka.sasl_mechanism,
        sasl_username=settings.kafka.sasl_username,
        sasl_password=settings.kafka.sasl_password,
        ssl_ca_location=settings.kafka.ssl_ca_location,
        ssl_cert_location=settings.kafka.ssl_cert_location,
        ssl_key_location=settings.kafka.ssl_key_location,
        enable_transactions=settings.kafka.processing.enable_transactions
    )
    
    logger.info("Starting LedgerWriter consumer...")
    logger.info(f"Consuming from topic: {consumer.TOPIC}")
    logger.info(f"Consumer group: {consumer.CONSUMER_GROUP}")
    logger.info(f"Kafka brokers: {settings.kafka.brokers}")
    logger.info(f"Database: {settings.database.host}:{settings.database.port}/{settings.database.database}")
    logger.info("")
    logger.info("Press Ctrl+C to stop...")
    
    try:
        # Start consuming (blocks until stopped)
        await consumer.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, stopping consumer...")
    finally:
        await consumer.stop()
        db_manager.close()
        logger.info("Consumer stopped")


if __name__ == "__main__":
    asyncio.run(main())
