"""
CLI commands for provisional charge management.

Provides commands for listing and cleaning up provisional charges.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from caracal.core.provisional_charges import ProvisionalChargeManager, ProvisionalChargeConfig
from caracal.db.connection import DatabaseConnectionManager, DatabaseConfig
from caracal.exceptions import CaracalError, ProvisionalChargeError


def get_provisional_charge_manager(config) -> ProvisionalChargeManager:
    """
    Create ProvisionalChargeManager instance from configuration.
    
    Args:
        config: Configuration object
        
    Returns:
        ProvisionalChargeManager instance
    """
    # Create database connection manager
    db_config = DatabaseConfig(
        host=config.database.host,
        port=config.database.port,
        database=config.database.database,
        user=config.database.user,
        password=config.database.password,
        pool_size=config.database.pool_size,
        max_overflow=config.database.max_overflow,
        pool_timeout=config.database.pool_timeout,
    )
    
    db_manager = DatabaseConnectionManager(db_config)
    db_manager.initialize()
    
    # Create session
    session = db_manager.get_session()
    
    # Create provisional charge config
    pc_config = ProvisionalChargeConfig(
        default_expiration_seconds=config.ase.provisional_charges.default_expiration_seconds,
        timeout_minutes=config.ase.provisional_charges.timeout_minutes,
        cleanup_interval_seconds=config.ase.provisional_charges.cleanup_interval_seconds,
        cleanup_batch_size=config.ase.provisional_charges.cleanup_batch_size,
    )
    
    return ProvisionalChargeManager(session, pc_config)


@click.command('list')
@click.option(
    '--agent-id',
    '-a',
    default=None,
    help='Filter by agent ID (optional)',
)
@click.option(
    '--show-expired',
    is_flag=True,
    help='Include expired charges in the list',
)
@click.option(
    '--format',
    '-f',
    type=click.Choice(['table', 'json'], case_sensitive=False),
    default='table',
    help='Output format (default: table)',
)
@click.pass_context
def list_charges(
    ctx,
    agent_id: Optional[str],
    show_expired: bool,
    format: str,
):
    """
    List provisional charges.
    
    By default, shows only active (not released, not expired) charges.
    Use --show-expired to include expired charges awaiting cleanup.
    
    Examples:
    
        # List all active provisional charges
        caracal provisional-charges list
        
        # List active charges for a specific agent
        caracal provisional-charges list --agent-id 550e8400-e29b-41d4-a716-446655440000
        
        # List all charges including expired ones
        caracal provisional-charges list --show-expired
        
        # JSON output
        caracal provisional-charges list --format json
    """
    try:
        # Get CLI context
        cli_ctx = ctx.obj
        
        # Create provisional charge manager
        import asyncio
        pc_manager = get_provisional_charge_manager(cli_ctx.config)
        
        if show_expired:
            # Query all charges (active + expired)
            from caracal.db.models import ProvisionalCharge
            from sqlalchemy import select
            from uuid import UUID
            
            stmt = select(ProvisionalCharge)
            if agent_id:
                stmt = stmt.where(ProvisionalCharge.agent_id == UUID(agent_id))
            stmt = stmt.where(ProvisionalCharge.released == False)
            stmt = stmt.order_by(ProvisionalCharge.created_at.desc())
            
            result = pc_manager.db_session.execute(stmt)
            charges = result.scalars().all()
        else:
            # Query only active charges
            if agent_id:
                from uuid import UUID
                charges = asyncio.run(pc_manager.get_active_provisional_charges(UUID(agent_id)))
            else:
                # Get all active charges across all agents
                from caracal.db.models import ProvisionalCharge
                from sqlalchemy import select
                
                now = datetime.utcnow()
                stmt = (
                    select(ProvisionalCharge)
                    .where(ProvisionalCharge.released == False)
                    .where(ProvisionalCharge.expires_at > now)
                    .order_by(ProvisionalCharge.created_at.desc())
                )
                
                result = pc_manager.db_session.execute(stmt)
                charges = result.scalars().all()
        
        if not charges:
            if show_expired:
                click.echo("No provisional charges found (active or expired).")
            else:
                click.echo("No active provisional charges found.")
            return
        
        # Calculate expired count if showing all
        now = datetime.utcnow()
        expired_count = sum(1 for c in charges if c.expires_at < now)
        active_count = len(charges) - expired_count
        
        if format.lower() == 'json':
            # JSON output
            output = {
                "total_charges": len(charges),
                "active_charges": active_count,
                "expired_charges": expired_count,
                "charges": [
                    {
                        "charge_id": str(charge.charge_id),
                        "agent_id": str(charge.agent_id),
                        "amount": str(charge.amount),
                        "currency": charge.currency,
                        "created_at": charge.created_at.isoformat(),
                        "expires_at": charge.expires_at.isoformat(),
                        "released": charge.released,
                        "expired": charge.expires_at < now,
                        "final_charge_event_id": charge.final_charge_event_id,
                    }
                    for charge in charges
                ]
            }
            click.echo(json.dumps(output, indent=2))
        else:
            # Table output
            click.echo(f"Provisional Charges")
            click.echo("=" * 100)
            click.echo()
            click.echo(f"Total charges: {len(charges)}")
            click.echo(f"Active charges: {active_count}")
            if show_expired:
                click.echo(f"Expired charges (awaiting cleanup): {expired_count}")
            click.echo()
            
            # Print header
            header = (
                f"{'Charge ID':<38}  "
                f"{'Agent ID':<38}  "
                f"{'Amount':<12}  "
                f"{'Status':<10}  "
                f"Expires At"
            )
            click.echo(header)
            click.echo("-" * 100)
            
            # Print charges
            for charge in charges:
                # Determine status
                if charge.released:
                    status = "Released"
                elif charge.expires_at < now:
                    status = "Expired"
                else:
                    status = "Active"
                
                # Format timestamps
                expires_at = charge.expires_at.strftime("%Y-%m-%d %H:%M:%S")
                amount_str = f"{charge.amount} {charge.currency}"
                
                click.echo(
                    f"{str(charge.charge_id):<38}  "
                    f"{str(charge.agent_id):<38}  "
                    f"{amount_str:<12}  "
                    f"{status:<10}  "
                    f"{expires_at}"
                )
    
    except ProvisionalChargeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except CaracalError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@click.command('cleanup')
@click.option(
    '--dry-run',
    is_flag=True,
    help='Show what would be cleaned up without actually cleaning',
)
@click.pass_context
def cleanup_charges(
    ctx,
    dry_run: bool,
):
    """
    Manually trigger cleanup of expired provisional charges.
    
    Releases expired charges that have not yet been cleaned up by the
    background cleanup job. Use --dry-run to see what would be cleaned
    without actually performing the cleanup.
    
    Examples:
    
        # Clean up expired charges
        caracal provisional-charges cleanup
        
        # Preview what would be cleaned up
        caracal provisional-charges cleanup --dry-run
    """
    try:
        # Get CLI context
        cli_ctx = ctx.obj
        
        # Create provisional charge manager
        import asyncio
        pc_manager = get_provisional_charge_manager(cli_ctx.config)
        
        if dry_run:
            # Count expired charges without cleaning
            from caracal.db.models import ProvisionalCharge
            from sqlalchemy import select
            
            now = datetime.utcnow()
            stmt = (
                select(ProvisionalCharge)
                .where(ProvisionalCharge.expires_at < now)
                .where(ProvisionalCharge.released == False)
            )
            
            result = pc_manager.db_session.execute(stmt)
            charges = result.scalars().all()
            
            click.echo(f"Dry run: Would clean up {len(charges)} expired provisional charges")
            
            if charges:
                click.echo()
                click.echo("Charges that would be cleaned up:")
                click.echo("-" * 80)
                
                for charge in charges[:10]:  # Show first 10
                    click.echo(
                        f"  Charge ID: {charge.charge_id}, "
                        f"Agent: {charge.agent_id}, "
                        f"Amount: {charge.amount} {charge.currency}, "
                        f"Expired: {charge.expires_at.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                
                if len(charges) > 10:
                    click.echo(f"  ... and {len(charges) - 10} more")
        else:
            # Perform cleanup
            released_count = asyncio.run(pc_manager.cleanup_expired_charges())
            
            if released_count > 0:
                click.echo(f"✓ Successfully cleaned up {released_count} expired provisional charges")
            else:
                click.echo("No expired provisional charges to clean up")
    
    except ProvisionalChargeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except CaracalError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)
