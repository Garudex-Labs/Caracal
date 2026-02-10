"""
CLI commands for event replay operations.

Provides commands to replay events from Kafka, check replay status,
and validate event ordering.

Requirements: 11.2, 11.5
"""

import asyncio
import sys
from datetime import datetime
from typing import Optional
from uuid import UUID

import click

from caracal.kafka.replay import EventReplayManager
from caracal.logging_config import get_logger
from caracal.exceptions import CaracalError

logger = get_logger(__name__)

# Try to import tabulate, fall back to simple formatting if not available
try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False


# Import pass_context and CLIContext after they're defined
# This avoids circular import issues
def pass_context(f):
    """Decorator to pass CLI context - imported lazily to avoid circular imports."""
    from caracal.cli.context import pass_context as _pass_context
    return _pass_context(f)


def get_cli_context():
    """Get CLIContext class - imported lazily to avoid circular imports."""
    from caracal.cli.main import CLIContext
    return CLIContext


# Local error handler to avoid circular import
def handle_caracal_error(func):
    """
    Decorator to handle CaracalError exceptions in CLI commands.
    
    Catches CaracalError exceptions and displays user-friendly error messages.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except CaracalError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"Unexpected error: {e}", err=True)
            import logging
            if logging.getLogger("caracal").level == logging.DEBUG:
                import traceback
                traceback.print_exc()
            sys.exit(1)
    
    return wrapper


@click.group(name='replay')
def replay_group():
    """Event replay operations."""
    pass


@replay_group.command(name='start')
@click.option(
    '--consumer-group',
    '-g',
    required=True,
    help='Consumer group to replay'
)
@click.option(
    '--topics',
    '-t',
    required=True,
    multiple=True,
    help='Topics to replay (can specify multiple times)'
)
@click.option(
    '--timestamp',
    '-ts',
    required=False,
    help='Timestamp to replay from (ISO format: YYYY-MM-DDTHH:MM:SS)'
)
@click.option(
    '--snapshot-id',
    '-s',
    required=False,
    help='Snapshot ID to replay from (alternative to timestamp)'
)
@pass_context
@handle_caracal_error
def start(
    ctx,  # Will be CLIContext but we avoid the import
    consumer_group: str,
    topics: tuple,
    timestamp: Optional[str],
    snapshot_id: Optional[str]
):
    """
    Start event replay from Kafka.
    
    Resets consumer group offsets and begins replaying events from the specified
    timestamp or snapshot.
    
    Examples:
        # Replay from specific timestamp
        caracal replay start -g ledger-writer-group -t caracal.metering.events \\
            --timestamp 2024-01-15T10:00:00
        
        # Replay from snapshot
        caracal replay start -g ledger-writer-group -t caracal.metering.events \\
            --snapshot-id 550e8400-e29b-41d4-a716-446655440000
    
    Requirements: 11.2, 11.5
    """
    try:
        # Validate inputs
        if not timestamp and not snapshot_id:
            click.echo("Error: Must specify either --timestamp or --snapshot-id", err=True)
            return
        
        if timestamp and snapshot_id:
            click.echo("Error: Cannot specify both --timestamp and --snapshot-id", err=True)
            return
        
        # Parse timestamp if provided
        start_timestamp = None
        if timestamp:
            try:
                start_timestamp = datetime.fromisoformat(timestamp)
            except ValueError as e:
                click.echo(f"Error: Invalid timestamp format: {e}", err=True)
                click.echo("Expected format: YYYY-MM-DDTHH:MM:SS", err=True)
                return
        
        # Load snapshot if provided
        if snapshot_id:
            from caracal.db.connection import get_session
            from caracal.merkle.snapshot import SnapshotManager
            from caracal.core.ledger import LedgerQuery
            from caracal.merkle.verifier import MerkleVerifier
            from caracal.merkle.signer import create_merkle_signer
            
            click.echo(f"Loading snapshot: {snapshot_id}")
            
            with get_session(ctx.config) as session:
                # Create dependencies
                ledger_query = LedgerQuery(session)
                merkle_signer = create_merkle_signer(ctx.config.merkle)
                merkle_verifier = MerkleVerifier(session, merkle_signer)
                snapshot_manager = SnapshotManager(session, ledger_query, merkle_verifier)
                
                # Load snapshot
                try:
                    snapshot_uuid = UUID(snapshot_id)
                    recovery_result = asyncio.run(
                        snapshot_manager.recover_from_snapshot(snapshot_uuid)
                    )
                    
                    start_timestamp = recovery_result.replay_from_timestamp
                    
                    click.echo(f"✓ Snapshot loaded: {snapshot_id}")
                    click.echo(f"  Agents restored: {recovery_result.agents_restored}")
                    click.echo(f"  Replay from: {start_timestamp}")
                except Exception as e:
                    click.echo(f"Error: Failed to load snapshot: {e}", err=True)
                    return
        
        # Create replay manager
        kafka_config = ctx.config.kafka
        replay_manager = EventReplayManager(
            brokers=kafka_config.brokers,
            security_protocol=kafka_config.security_protocol,
            sasl_mechanism=getattr(kafka_config, 'sasl_mechanism', None),
            sasl_username=getattr(kafka_config, 'sasl_username', None),
            sasl_password=getattr(kafka_config, 'sasl_password', None),
            ssl_ca_location=getattr(kafka_config, 'ssl_ca_location', None),
            ssl_cert_location=getattr(kafka_config, 'ssl_cert_location', None),
            ssl_key_location=getattr(kafka_config, 'ssl_key_location', None)
        )
        
        # Start replay
        click.echo(f"\nStarting event replay:")
        click.echo(f"  Consumer group: {consumer_group}")
        click.echo(f"  Topics: {', '.join(topics)}")
        click.echo(f"  Start timestamp: {start_timestamp}")
        
        replay_id = asyncio.run(
            replay_manager.start_replay(
                consumer_group=consumer_group,
                topics=list(topics),
                start_timestamp=start_timestamp
            )
        )
        
        click.echo(f"\n✓ Event replay started successfully!")
        click.echo(f"  Replay ID: {replay_id}")
        click.echo(f"\nUse 'caracal replay status --replay-id {replay_id}' to check progress")
        
    except Exception as e:
        click.echo(f"Error: Failed to start replay: {e}", err=True)
        logger.error(f"Replay start failed: {e}", exc_info=True)
        raise


@replay_group.command(name='status')
@click.option(
    '--replay-id',
    '-r',
    required=False,
    help='Replay ID to check status for (omit to list all)'
)
@pass_context
@handle_caracal_error
def status(ctx, replay_id: Optional[str]):
    """
    Check status of event replay operations.
    
    Examples:
        # Check specific replay
        caracal replay status --replay-id 550e8400-e29b-41d4-a716-446655440000
        
        # List all replays
        caracal replay status
    
    Requirements: 11.7
    """
    try:
        # Create replay manager
        kafka_config = ctx.config.kafka
        replay_manager = EventReplayManager(
            brokers=kafka_config.brokers,
            security_protocol=kafka_config.security_protocol,
            sasl_mechanism=getattr(kafka_config, 'sasl_mechanism', None),
            sasl_username=getattr(kafka_config, 'sasl_username', None),
            sasl_password=getattr(kafka_config, 'sasl_password', None),
            ssl_ca_location=getattr(kafka_config, 'ssl_ca_location', None),
            ssl_cert_location=getattr(kafka_config, 'ssl_cert_location', None),
            ssl_key_location=getattr(kafka_config, 'ssl_key_location', None)
        )
        
        if replay_id:
            # Check specific replay
            try:
                replay_uuid = UUID(replay_id)
                progress = replay_manager.get_replay_progress(replay_uuid)
                
                if not progress:
                    click.echo(f"Replay not found: {replay_id}", err=True)
                    return
                
                # Display replay details
                click.echo(f"\nReplay Status:")
                click.echo(f"  Replay ID: {progress.replay_id}")
                click.echo(f"  Consumer Group: {progress.consumer_group}")
                click.echo(f"  Topics: {', '.join(progress.topics)}")
                click.echo(f"  Status: {progress.status}")
                click.echo(f"  Start Timestamp: {progress.start_timestamp}")
                click.echo(f"  Start Time: {progress.start_time}")
                
                if progress.end_time:
                    duration = (progress.end_time - progress.start_time).total_seconds()
                    click.echo(f"  End Time: {progress.end_time}")
                    click.echo(f"  Duration: {duration:.2f}s")
                
                click.echo(f"  Events Processed: {progress.events_processed}")
                
                if progress.error_message:
                    click.echo(f"  Error: {progress.error_message}")
                
                # Display current offsets
                if progress.current_offsets:
                    click.echo(f"\n  Current Offsets:")
                    for topic, partitions in progress.current_offsets.items():
                        for partition, offset in partitions.items():
                            click.echo(f"    {topic}[{partition}]: {offset}")
            
            except ValueError:
                click.echo(f"Error: Invalid replay ID format: {replay_id}", err=True)
                return
        
        else:
            # List all replays
            all_replays = replay_manager.list_all_replays()
            
            if not all_replays:
                click.echo("No replay operations found")
                return
            
            # Build table
            table_data = []
            for progress in all_replays:
                duration = ""
                if progress.end_time:
                    duration = f"{(progress.end_time - progress.start_time).total_seconds():.2f}s"
                
                table_data.append([
                    str(progress.replay_id)[:8] + "...",
                    progress.consumer_group,
                    ', '.join(progress.topics),
                    progress.status,
                    progress.events_processed,
                    progress.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                    duration
                ])
            
            headers = ["Replay ID", "Consumer Group", "Topics", "Status", "Events", "Start Time", "Duration"]
            click.echo("\nReplay Operations:")
            
            if HAS_TABULATE:
                click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))
            else:
                # Simple formatting without tabulate
                click.echo(" | ".join(headers))
                click.echo("-" * 100)
                for row in table_data:
                    click.echo(" | ".join(str(cell) for cell in row))
    
    except Exception as e:
        click.echo(f"Error: Failed to get replay status: {e}", err=True)
        logger.error(f"Replay status check failed: {e}", exc_info=True)
        raise


@replay_group.command(name='validate')
@click.option(
    '--consumer-group',
    '-g',
    required=True,
    help='Consumer group to validate'
)
@click.option(
    '--topics',
    '-t',
    required=True,
    multiple=True,
    help='Topics to validate (can specify multiple times)'
)
@click.option(
    '--max-events',
    '-n',
    type=int,
    default=None,
    help='Maximum events to check (default: all)'
)
@pass_context
@handle_caracal_error
def validate(
    ctx,
    consumer_group: str,
    topics: tuple,
    max_events: Optional[int]
):
    """
    Validate event ordering during replay.
    
    Checks that events are processed in chronological order based on timestamps.
    
    Examples:
        # Validate all events
        caracal replay validate -g ledger-writer-group -t caracal.metering.events
        
        # Validate first 1000 events
        caracal replay validate -g ledger-writer-group -t caracal.metering.events -n 1000
    
    Requirements: 11.3, 11.6
    """
    try:
        # Create replay manager
        kafka_config = ctx.config.kafka
        replay_manager = EventReplayManager(
            brokers=kafka_config.brokers,
            security_protocol=kafka_config.security_protocol,
            sasl_mechanism=getattr(kafka_config, 'sasl_mechanism', None),
            sasl_username=getattr(kafka_config, 'sasl_username', None),
            sasl_password=getattr(kafka_config, 'sasl_password', None),
            ssl_ca_location=getattr(kafka_config, 'ssl_ca_location', None),
            ssl_cert_location=getattr(kafka_config, 'ssl_cert_location', None),
            ssl_key_location=getattr(kafka_config, 'ssl_key_location', None)
        )
        
        click.echo(f"\nValidating event ordering:")
        click.echo(f"  Consumer group: {consumer_group}")
        click.echo(f"  Topics: {', '.join(topics)}")
        if max_events:
            click.echo(f"  Max events: {max_events}")
        
        # Validate ordering
        validation = asyncio.run(
            replay_manager.validate_event_ordering(
                consumer_group=consumer_group,
                topics=list(topics),
                max_events=max_events
            )
        )
        
        # Display results
        click.echo(f"\nValidation Results:")
        click.echo(f"  Total events: {validation.total_events}")
        click.echo(f"  Ordered events: {validation.ordered_events}")
        click.echo(f"  Out-of-order events: {validation.out_of_order_events}")
        click.echo(f"  Validation: {'✓ PASSED' if validation.validation_passed else '✗ FAILED'}")
        
        # Display out-of-order details if any
        if validation.out_of_order_events > 0:
            click.echo(f"\nOut-of-Order Events:")
            
            # Show first 10 out-of-order events
            for detail in validation.out_of_order_details[:10]:
                click.echo(
                    f"  {detail['topic']}[{detail['partition']}] offset {detail['offset']}: "
                    f"timestamp={detail['timestamp']}, previous={detail['previous_timestamp']}, "
                    f"diff={detail['time_diff_ms']}ms"
                )
            
            if len(validation.out_of_order_details) > 10:
                click.echo(f"  ... and {len(validation.out_of_order_details) - 10} more")
        
        # Exit with error code if validation failed
        if not validation.validation_passed:
            raise click.ClickException("Event ordering validation failed")
    
    except Exception as e:
        click.echo(f"Error: Failed to validate event ordering: {e}", err=True)
        logger.error(f"Event ordering validation failed: {e}", exc_info=True)
        raise


# Export the group
__all__ = ['replay_group']
