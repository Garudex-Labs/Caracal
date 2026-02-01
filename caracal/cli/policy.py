"""
CLI commands for policy management.

Provides commands for creating, listing, and retrieving budget policies.
"""

import sys
from decimal import Decimal
from pathlib import Path

import click

from caracal.core.identity import AgentRegistry
from caracal.core.policy import PolicyStore
from caracal.exceptions import (
    AgentNotFoundError,
    CaracalError,
    InvalidPolicyError,
)


def get_policy_store(config) -> PolicyStore:
    """
    Create PolicyStore instance from configuration.
    
    Args:
        config: Configuration object
        
    Returns:
        PolicyStore instance
    """
    policy_path = Path(config.storage.policy_store).expanduser()
    backup_count = config.storage.backup_count
    
    # Create agent registry for validation
    registry_path = Path(config.storage.agent_registry).expanduser()
    agent_registry = AgentRegistry(str(registry_path), backup_count=backup_count)
    
    return PolicyStore(
        str(policy_path),
        agent_registry=agent_registry,
        backup_count=backup_count
    )


@click.command('create')
@click.option(
    '--agent-id',
    '-a',
    required=True,
    help='Agent ID this policy applies to',
)
@click.option(
    '--limit',
    '-l',
    required=True,
    type=str,
    help='Maximum spending limit (e.g., 100.00)',
)
@click.option(
    '--window',
    '-w',
    default='daily',
    help='Time window for budget (default: daily)',
)
@click.option(
    '--currency',
    '-c',
    default='USD',
    help='Currency code (default: USD)',
)
@click.pass_context
def create(ctx, agent_id: str, limit: str, window: str, currency: str):
    """
    Create a new budget policy for an agent.
    
    Creates a policy that constrains agent spending within a time window.
    
    Examples:
    
        caracal policy create --agent-id 550e8400-e29b-41d4-a716-446655440000 --limit 100.00
        
        caracal policy create -a 550e8400-e29b-41d4-a716-446655440000 -l 50.00 -w daily -c USD
    """
    try:
        # Get CLI context
        cli_ctx = ctx.obj
        
        # Validate and parse limit amount
        try:
            limit_amount = Decimal(limit)
            if limit_amount <= 0:
                click.echo(
                    f"Error: Limit amount must be positive, got {limit}",
                    err=True
                )
                sys.exit(1)
        except Exception as e:
            click.echo(
                f"Error: Invalid limit amount '{limit}'. Must be a valid number.",
                err=True
            )
            sys.exit(1)
        
        # Validate time window (v0.1 only supports daily)
        if window != 'daily':
            click.echo(
                f"Error: Only 'daily' time window is supported in v0.1, got '{window}'",
                err=True
            )
            sys.exit(1)
        
        # Validate currency (v0.1 only supports USD)
        if currency.upper() != 'USD':
            click.echo(
                f"Error: Only 'USD' currency is supported in v0.1, got '{currency}'",
                err=True
            )
            sys.exit(1)
        
        # Create policy store
        policy_store = get_policy_store(cli_ctx.config)
        
        # Create policy
        policy = policy_store.create_policy(
            agent_id=agent_id,
            limit_amount=limit_amount,
            time_window=window,
            currency=currency.upper()
        )
        
        # Display success message
        click.echo("✓ Policy created successfully!")
        click.echo()
        click.echo(f"Policy ID:    {policy.policy_id}")
        click.echo(f"Agent ID:     {policy.agent_id}")
        click.echo(f"Limit:        {policy.limit_amount} {policy.currency}")
        click.echo(f"Time Window:  {policy.time_window}")
        click.echo(f"Created:      {policy.created_at}")
        click.echo(f"Active:       {policy.active}")
        
    except AgentNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except InvalidPolicyError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except CaracalError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@click.command('list')
@click.option(
    '--agent-id',
    '-a',
    default=None,
    help='Filter by agent ID (optional)',
)
@click.option(
    '--format',
    '-f',
    type=click.Choice(['table', 'json'], case_sensitive=False),
    default='table',
    help='Output format (default: table)',
)
@click.pass_context
def list_policies(ctx, agent_id: str, format: str):
    """
    List budget policies.
    
    Lists all policies in the system, or filters by agent ID if specified.
    
    Examples:
    
        caracal policy list
        
        caracal policy list --agent-id 550e8400-e29b-41d4-a716-446655440000
        
        caracal policy list --format json
    """
    try:
        # Get CLI context
        cli_ctx = ctx.obj
        
        # Create policy store
        policy_store = get_policy_store(cli_ctx.config)
        
        # Get policies
        if agent_id:
            policies = policy_store.get_policies(agent_id)
        else:
            policies = policy_store.list_all_policies()
        
        if not policies:
            if agent_id:
                click.echo(f"No policies found for agent: {agent_id}")
            else:
                click.echo("No policies found.")
            return
        
        if format.lower() == 'json':
            # JSON output
            import json
            output = [policy.to_dict() for policy in policies]
            click.echo(json.dumps(output, indent=2))
        else:
            # Table output
            click.echo(f"Total policies: {len(policies)}")
            click.echo()
            
            # Calculate column widths
            max_policy_id_len = max(len(policy.policy_id) for policy in policies)
            max_agent_id_len = max(len(policy.agent_id) for policy in policies)
            max_limit_len = max(len(f"{policy.limit_amount} {policy.currency}") for policy in policies)
            
            # Ensure minimum widths for headers
            policy_id_width = max(max_policy_id_len, len("Policy ID"))
            agent_id_width = max(max_agent_id_len, len("Agent ID"))
            limit_width = max(max_limit_len, len("Limit"))
            
            # Print header
            header = (
                f"{'Policy ID':<{policy_id_width}}  "
                f"{'Agent ID':<{agent_id_width}}  "
                f"{'Limit':<{limit_width}}  "
                f"{'Window':<8}  "
                f"{'Active':<6}  "
                f"Created"
            )
            click.echo(header)
            click.echo("-" * len(header))
            
            # Print policies
            for policy in policies:
                # Format created_at to be more readable
                created = policy.created_at.replace('T', ' ').replace('Z', '')
                limit_str = f"{policy.limit_amount} {policy.currency}"
                active_str = "Yes" if policy.active else "No"
                
                click.echo(
                    f"{policy.policy_id:<{policy_id_width}}  "
                    f"{policy.agent_id:<{agent_id_width}}  "
                    f"{limit_str:<{limit_width}}  "
                    f"{policy.time_window:<8}  "
                    f"{active_str:<6}  "
                    f"{created}"
                )
        
    except CaracalError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@click.command('get')
@click.option(
    '--agent-id',
    '-a',
    required=True,
    help='Agent ID to retrieve policies for',
)
@click.option(
    '--format',
    '-f',
    type=click.Choice(['table', 'json'], case_sensitive=False),
    default='table',
    help='Output format (default: table)',
)
@click.pass_context
def get(ctx, agent_id: str, format: str):
    """
    Get policies for a specific agent.
    
    Retrieves and displays all active policies for an agent.
    
    Examples:
    
        caracal policy get --agent-id 550e8400-e29b-41d4-a716-446655440000
        
        caracal policy get -a 550e8400-e29b-41d4-a716-446655440000 --format json
    """
    try:
        # Get CLI context
        cli_ctx = ctx.obj
        
        # Create policy store
        policy_store = get_policy_store(cli_ctx.config)
        
        # Get policies for agent
        policies = policy_store.get_policies(agent_id)
        
        if not policies:
            click.echo(f"No active policies found for agent: {agent_id}")
            return
        
        if format.lower() == 'json':
            # JSON output
            import json
            output = [policy.to_dict() for policy in policies]
            click.echo(json.dumps(output, indent=2))
        else:
            # Table output
            click.echo(f"Policies for Agent: {agent_id}")
            click.echo("=" * 70)
            click.echo()
            
            for i, policy in enumerate(policies, 1):
                if i > 1:
                    click.echo()
                    click.echo("-" * 70)
                    click.echo()
                
                click.echo(f"Policy #{i}")
                click.echo(f"  Policy ID:    {policy.policy_id}")
                click.echo(f"  Limit:        {policy.limit_amount} {policy.currency}")
                click.echo(f"  Time Window:  {policy.time_window}")
                click.echo(f"  Active:       {'Yes' if policy.active else 'No'}")
                click.echo(f"  Created:      {policy.created_at}")
        
    except CaracalError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)
