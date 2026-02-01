"""
CLI commands for delegation token management.

Provides commands for generating and viewing delegation tokens.
"""

import json
import sys
from pathlib import Path

import click

from caracal.core.delegation import DelegationTokenManager
from caracal.core.identity import AgentRegistry
from caracal.exceptions import CaracalError


def get_agent_registry_with_delegation(config) -> tuple:
    """
    Create AgentRegistry and DelegationTokenManager instances from configuration.
    
    Args:
        config: Configuration object
        
    Returns:
        Tuple of (AgentRegistry, DelegationTokenManager)
    """
    registry_path = Path(config.storage.agent_registry).expanduser()
    backup_count = config.storage.backup_count
    
    # Create delegation token manager first
    delegation_manager = DelegationTokenManager(agent_registry=None)
    
    # Create agent registry with delegation manager
    registry = AgentRegistry(
        str(registry_path),
        backup_count=backup_count,
        delegation_token_manager=delegation_manager
    )
    
    # Set registry reference in delegation manager
    delegation_manager.agent_registry = registry
    
    return registry, delegation_manager


@click.command('generate')
@click.option(
    '--parent-id',
    '-p',
    required=True,
    help='Parent agent ID (issuer)',
)
@click.option(
    '--child-id',
    '-c',
    required=True,
    help='Child agent ID (subject)',
)
@click.option(
    '--spending-limit',
    '-l',
    required=True,
    type=float,
    help='Maximum spending allowed',
)
@click.option(
    '--currency',
    default='USD',
    help='Currency code (default: USD)',
)
@click.option(
    '--expiration',
    '-e',
    default=86400,
    type=int,
    help='Token validity duration in seconds (default: 86400 = 24 hours)',
)
@click.option(
    '--operations',
    '-o',
    multiple=True,
    help='Allowed operations (can be specified multiple times, default: api_call, mcp_tool)',
)
@click.pass_context
def generate(ctx, parent_id: str, child_id: str, spending_limit: float, 
             currency: str, expiration: int, operations: tuple):
    """
    Generate a delegation token for a child agent.
    
    Creates a JWT token signed by the parent agent that authorizes the child
    agent to spend up to the specified limit.
    
    Examples:
    
        caracal delegation generate \\
            --parent-id 550e8400-e29b-41d4-a716-446655440000 \\
            --child-id 660e8400-e29b-41d4-a716-446655440001 \\
            --spending-limit 100.00
        
        caracal delegation generate -p parent-uuid -c child-uuid \\
            -l 50.00 --currency EUR --expiration 3600 \\
            -o api_call -o mcp_tool
    """
    try:
        # Get CLI context
        cli_ctx = ctx.obj
        
        # Create registry and delegation manager
        registry, delegation_manager = get_agent_registry_with_delegation(cli_ctx.config)
        
        # Parse allowed operations
        allowed_operations = list(operations) if operations else None
        
        # Generate token
        token = registry.generate_delegation_token(
            parent_agent_id=parent_id,
            child_agent_id=child_id,
            spending_limit=spending_limit,
            currency=currency,
            expiration_seconds=expiration,
            allowed_operations=allowed_operations
        )
        
        if token is None:
            click.echo("Error: Delegation token generation not available", err=True)
            sys.exit(1)
        
        # Display success message
        click.echo("✓ Delegation token generated successfully!")
        click.echo()
        click.echo(f"Parent Agent:    {parent_id}")
        click.echo(f"Child Agent:     {child_id}")
        click.echo(f"Spending Limit:  {spending_limit} {currency}")
        click.echo(f"Expires In:      {expiration} seconds")
        click.echo()
        click.echo("Token:")
        click.echo(token)
        click.echo()
        click.echo("⚠ Store this token securely. It will not be displayed again.")
        
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
    required=True,
    help='Agent ID to list delegation tokens for',
)
@click.option(
    '--format',
    '-f',
    type=click.Choice(['table', 'json'], case_sensitive=False),
    default='table',
    help='Output format (default: table)',
)
@click.pass_context
def list_tokens(ctx, agent_id: str, format: str):
    """
    List delegation tokens for an agent.
    
    Displays metadata about delegation tokens issued to or by an agent.
    
    Examples:
    
        caracal delegation list --agent-id 550e8400-e29b-41d4-a716-446655440000
        
        caracal delegation list -a 550e8400-e29b-41d4-a716-446655440000 --format json
    """
    try:
        # Get CLI context
        cli_ctx = ctx.obj
        
        # Create registry
        registry_path = Path(cli_ctx.config.storage.agent_registry).expanduser()
        backup_count = cli_ctx.config.storage.backup_count
        registry = AgentRegistry(str(registry_path), backup_count=backup_count)
        
        # Get agent
        agent = registry.get_agent(agent_id)
        
        if not agent:
            click.echo(f"Error: Agent not found: {agent_id}", err=True)
            sys.exit(1)
        
        # Get delegation tokens from metadata
        tokens = agent.metadata.get("delegation_tokens", [])
        
        if not tokens:
            click.echo(f"No delegation tokens found for agent {agent_id}")
            return
        
        if format.lower() == 'json':
            # JSON output
            click.echo(json.dumps(tokens, indent=2))
        else:
            # Table output
            click.echo(f"Delegation Tokens for Agent: {agent.name}")
            click.echo(f"Agent ID: {agent_id}")
            click.echo()
            click.echo(f"Total tokens: {len(tokens)}")
            click.echo()
            
            # Print header
            click.echo(f"{'Token ID':<25}  {'Parent Agent':<38}  {'Limit':<15}  {'Created':<20}")
            click.echo("-" * 110)
            
            # Print tokens
            for token in tokens:
                token_id = token.get("token_id", "N/A")
                parent_id = token.get("parent_agent_id", "N/A")
                limit = f"{token.get('spending_limit', 0)} {token.get('currency', 'USD')}"
                created = token.get("created_at", "N/A").replace('T', ' ').replace('Z', '')
                
                click.echo(f"{token_id:<25}  {parent_id:<38}  {limit:<15}  {created:<20}")
        
    except CaracalError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@click.command('validate')
@click.option(
    '--token',
    '-t',
    required=True,
    help='Delegation token to validate',
)
@click.pass_context
def validate(ctx, token: str):
    """
    Validate a delegation token.
    
    Verifies the token signature, expiration, and displays the decoded claims.
    
    Examples:
    
        caracal delegation validate --token eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9...
    """
    try:
        # Get CLI context
        cli_ctx = ctx.obj
        
        # Create registry and delegation manager
        registry, delegation_manager = get_agent_registry_with_delegation(cli_ctx.config)
        
        # Validate token
        claims = delegation_manager.validate_token(token)
        
        # Display validation result
        click.echo("✓ Token is valid!")
        click.echo()
        click.echo("Token Claims:")
        click.echo("=" * 50)
        click.echo(f"Issuer (Parent):     {claims.issuer}")
        click.echo(f"Subject (Child):     {claims.subject}")
        click.echo(f"Audience:            {claims.audience}")
        click.echo(f"Token ID:            {claims.token_id}")
        click.echo(f"Spending Limit:      {claims.spending_limit} {claims.currency}")
        click.echo(f"Issued At:           {claims.issued_at}")
        click.echo(f"Expires At:          {claims.expiration}")
        click.echo(f"Allowed Operations:  {', '.join(claims.allowed_operations)}")
        click.echo(f"Max Delegation Depth: {claims.max_delegation_depth}")
        
        if claims.budget_category:
            click.echo(f"Budget Category:     {claims.budget_category}")
        
    except CaracalError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)
