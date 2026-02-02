"""
CLI commands for migrating v0.1 data to v0.2 PostgreSQL backend.

Provides commands for:
- Full migration (v0.1-to-v0.2)
- Selective migration (agents-only, policies-only, ledger-only)
- Migration validation
- Dry-run mode

Requirements: 7.1, 7.2, 7.3
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel

from caracal.cli.main import pass_context, CLIContext
from caracal.core.migration import MigrationManager, MigrationResult, MigrationSummary
from caracal.db.connection import DatabaseConfig, DatabaseConnectionManager

logger = logging.getLogger(__name__)
console = Console()


@click.group(name='migrate')
def migrate_group():
    """Migrate data between Caracal versions."""
    pass


@migrate_group.command(name='v0.1-to-v0.2')
@click.option(
    '--source-dir',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.home() / '.caracal',
    help='Path to v0.1 data directory (default: ~/.caracal)',
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Validate migration without writing to database',
)
@click.option(
    '--agents-only',
    is_flag=True,
    help='Migrate only agent identities',
)
@click.option(
    '--policies-only',
    is_flag=True,
    help='Migrate only budget policies',
)
@click.option(
    '--ledger-only',
    is_flag=True,
    help='Migrate only ledger events',
)
@click.option(
    '--batch-size',
    type=int,
    default=1000,
    help='Number of records to process per batch (default: 1000)',
)
@click.option(
    '--verbose',
    '-v',
    is_flag=True,
    help='Show detailed progress output',
)
@pass_context
def migrate_v01_to_v02(
    ctx: CLIContext,
    source_dir: Path,
    dry_run: bool,
    agents_only: bool,
    policies_only: bool,
    ledger_only: bool,
    batch_size: int,
    verbose: bool,
):
    """
    Migrate v0.1 file-based data to v0.2 PostgreSQL backend.
    
    This command migrates agents.json, policies.json, and ledger.jsonl
    from the v0.1 data directory to the PostgreSQL database.
    
    The migration is idempotent and can be safely re-run.
    
    Examples:
    
        # Full migration
        caracal migrate v0.1-to-v0.2
        
        # Dry-run to validate without writing
        caracal migrate v0.1-to-v0.2 --dry-run
        
        # Migrate only agents
        caracal migrate v0.1-to-v0.2 --agents-only
        
        # Custom source directory
        caracal migrate v0.1-to-v0.2 --source-dir /path/to/data
    """
    try:
        # Display header
        console.print()
        console.print(Panel.fit(
            "[bold cyan]Caracal Migration: v0.1 → v0.2[/bold cyan]",
            border_style="cyan"
        ))
        console.print()
        
        # Display configuration
        console.print(f"[bold]Source Directory:[/bold] {source_dir}")
        
        # Get database configuration from config
        if not hasattr(ctx.config, 'database'):
            console.print("[red]Error: Database configuration not found in config file[/red]")
            console.print("[yellow]Hint: Add database section to your config.yaml[/yellow]")
            sys.exit(1)
        
        db_config = DatabaseConfig(
            host=ctx.config.database.get('host', 'localhost'),
            port=ctx.config.database.get('port', 5432),
            database=ctx.config.database.get('database', 'caracal'),
            user=ctx.config.database.get('user', 'caracal'),
            password=ctx.config.database.get('password', ''),
        )
        
        console.print(f"[bold]Target Database:[/bold] postgresql://{db_config.host}:{db_config.port}/{db_config.database}")
        
        if dry_run:
            console.print("[yellow]Mode: DRY RUN (no data will be written)[/yellow]")
        
        console.print()
        
        # Phase 1: Validation
        console.print("[bold cyan]Phase 1: Validation[/bold cyan]")
        console.print("─" * 50)
        
        # Check source files
        agents_file = source_dir / "agents.json"
        policies_file = source_dir / "policies.json"
        ledger_file = source_dir / "ledger.jsonl"
        
        if not agents_only and not policies_only and not ledger_only:
            # Full migration - check all files
            if not agents_file.exists():
                console.print(f"[red]✗ agents.json not found in {source_dir}[/red]")
                sys.exit(1)
            if not policies_file.exists():
                console.print(f"[red]✗ policies.json not found in {source_dir}[/red]")
                sys.exit(1)
            if not ledger_file.exists():
                console.print(f"[red]✗ ledger.jsonl not found in {source_dir}[/red]")
                sys.exit(1)
        
        # Count source records
        import json
        
        agent_count = 0
        policy_count = 0
        ledger_count = 0
        
        if agents_file.exists() and (not policies_only and not ledger_only):
            with open(agents_file, 'r') as f:
                agent_count = len(json.load(f))
            console.print(f"[green]✓ Found agents.json ({agent_count} agents)[/green]")
        
        if policies_file.exists() and (not agents_only and not ledger_only):
            with open(policies_file, 'r') as f:
                policy_count = len(json.load(f))
            console.print(f"[green]✓ Found policies.json ({policy_count} policies)[/green]")
        
        if ledger_file.exists() and (not agents_only and not policies_only):
            with open(ledger_file, 'r') as f:
                ledger_count = sum(1 for line in f if line.strip())
            console.print(f"[green]✓ Found ledger.jsonl ({ledger_count:,} events)[/green]")
        
        # Test database connection
        if not dry_run:
            db_manager = DatabaseConnectionManager(db_config)
            db_manager.initialize()
            
            if not db_manager.health_check():
                console.print("[red]✗ Database connection failed[/red]")
                sys.exit(1)
            
            console.print("[green]✓ Database connection successful[/green]")
        else:
            console.print("[yellow]⊘ Database connection skipped (dry-run)[/yellow]")
        
        console.print()
        
        if dry_run:
            console.print("[bold green]✓ Validation complete (dry-run mode)[/bold green]")
            console.print()
            console.print("[yellow]No data was written to the database.[/yellow]")
            console.print("[yellow]Run without --dry-run to perform the migration.[/yellow]")
            return
        
        # Phase 2: Migration
        console.print("[bold cyan]Phase 2: Migration[/bold cyan]")
        console.print("─" * 50)
        
        # Create migration manager
        session = db_manager.get_session()
        migration_manager = MigrationManager(session, str(source_dir))
        
        # Perform migration with progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            
            agents_result = None
            policies_result = None
            ledger_result = None
            
            # Migrate agents
            if not policies_only and not ledger_only:
                task = progress.add_task(
                    f"[cyan]Migrating agents...",
                    total=agent_count if agent_count > 0 else 1
                )
                agents_result = migration_manager.migrate_agents(batch_size)
                progress.update(task, completed=agent_count if agent_count > 0 else 1)
            
            # Migrate policies
            if not agents_only and not ledger_only:
                task = progress.add_task(
                    f"[cyan]Migrating policies...",
                    total=policy_count if policy_count > 0 else 1
                )
                policies_result = migration_manager.migrate_policies(batch_size)
                progress.update(task, completed=policy_count if policy_count > 0 else 1)
            
            # Migrate ledger
            if not agents_only and not policies_only:
                task = progress.add_task(
                    f"[cyan]Migrating ledger...",
                    total=ledger_count if ledger_count > 0 else 1
                )
                ledger_result = migration_manager.migrate_ledger(batch_size)
                progress.update(task, completed=ledger_count if ledger_count > 0 else 1)
        
        console.print()
        
        # Display results
        _display_migration_results(agents_result, policies_result, ledger_result)
        
        # Phase 3: Validation
        if not agents_only and not policies_only and not ledger_only:
            console.print()
            console.print("[bold cyan]Phase 3: Validation[/bold cyan]")
            console.print("─" * 50)
            
            validation_result = migration_manager.validate_migration()
            
            if validation_result.agent_count_match:
                console.print(f"[green]✓ Agent count matches: {validation_result.target_counts['agents']}[/green]")
            else:
                console.print(f"[red]✗ Agent count mismatch: source={validation_result.source_counts['agents']}, target={validation_result.target_counts['agents']}[/red]")
            
            if validation_result.policy_count_match:
                console.print(f"[green]✓ Policy count matches: {validation_result.target_counts['policies']}[/green]")
            else:
                console.print(f"[red]✗ Policy count mismatch: source={validation_result.source_counts['policies']}, target={validation_result.target_counts['policies']}[/red]")
            
            if validation_result.ledger_count_match:
                console.print(f"[green]✓ Ledger event count matches: {validation_result.target_counts['ledger']:,}[/green]")
            else:
                console.print(f"[red]✗ Ledger count mismatch: source={validation_result.source_counts['ledger']}, target={validation_result.target_counts['ledger']}[/red]")
            
            if validation_result.spot_check_passed:
                console.print("[green]✓ Spot-check validation passed[/green]")
            else:
                console.print("[red]✗ Spot-check validation failed[/red]")
            
            console.print()
            
            if validation_result.valid:
                console.print("[bold green]✓ Migration completed successfully![/bold green]")
            else:
                console.print("[bold red]✗ Migration completed with validation errors[/bold red]")
                if validation_result.errors:
                    console.print()
                    console.print("[bold]Validation Errors:[/bold]")
                    for error in validation_result.errors[:10]:  # Show first 10 errors
                        console.print(f"  [red]• {error}[/red]")
                    if len(validation_result.errors) > 10:
                        console.print(f"  [yellow]... and {len(validation_result.errors) - 10} more errors[/yellow]")
        else:
            console.print()
            console.print("[bold green]✓ Partial migration completed![/bold green]")
        
        # Next steps
        console.print()
        console.print("[bold]Next Steps:[/bold]")
        console.print("  1. Update configuration to use PostgreSQL backend")
        console.print("  2. Test v0.1 SDK code with v0.2 backend")
        console.print(f"  3. Backup v0.1 data files (already in {source_dir})")
        
        # Close database connection
        session.close()
        db_manager.close()
    
    except Exception as e:
        console.print(f"[red]Error: Migration failed: {e}[/red]")
        if verbose or ctx.verbose:
            import traceback
            console.print()
            console.print("[bold]Traceback:[/bold]")
            console.print(traceback.format_exc())
        sys.exit(1)


@migrate_group.command(name='validate')
@click.option(
    '--source-dir',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.home() / '.caracal',
    help='Path to v0.1 data directory (default: ~/.caracal)',
)
@click.option(
    '--spot-check-count',
    type=int,
    default=10,
    help='Number of random records to validate (default: 10)',
)
@pass_context
def validate_migration(ctx: CLIContext, source_dir: Path, spot_check_count: int):
    """
    Validate completed migration.
    
    Compares record counts and performs spot-check validation
    to ensure migration integrity.
    
    Examples:
    
        # Validate migration
        caracal migrate validate
        
        # Validate with more spot checks
        caracal migrate validate --spot-check-count 50
    """
    try:
        console.print()
        console.print(Panel.fit(
            "[bold cyan]Migration Validation[/bold cyan]",
            border_style="cyan"
        ))
        console.print()
        
        # Get database configuration
        if not hasattr(ctx.config, 'database'):
            console.print("[red]Error: Database configuration not found in config file[/red]")
            sys.exit(1)
        
        db_config = DatabaseConfig(
            host=ctx.config.database.get('host', 'localhost'),
            port=ctx.config.database.get('port', 5432),
            database=ctx.config.database.get('database', 'caracal'),
            user=ctx.config.database.get('user', 'caracal'),
            password=ctx.config.database.get('password', ''),
        )
        
        # Initialize database connection
        db_manager = DatabaseConnectionManager(db_config)
        db_manager.initialize()
        
        if not db_manager.health_check():
            console.print("[red]✗ Database connection failed[/red]")
            sys.exit(1)
        
        # Create migration manager
        session = db_manager.get_session()
        migration_manager = MigrationManager(session, str(source_dir))
        
        # Perform validation
        console.print("[cyan]Running validation...[/cyan]")
        console.print()
        
        validation_result = migration_manager.validate_migration(spot_check_count)
        
        # Display results
        table = Table(title="Validation Results", show_header=True, header_style="bold cyan")
        table.add_column("Check", style="cyan")
        table.add_column("Source", justify="right")
        table.add_column("Target", justify="right")
        table.add_column("Status", justify="center")
        
        def status_icon(passed: bool) -> str:
            return "[green]✓[/green]" if passed else "[red]✗[/red]"
        
        table.add_row(
            "Agents",
            str(validation_result.source_counts['agents']),
            str(validation_result.target_counts['agents']),
            status_icon(validation_result.agent_count_match)
        )
        
        table.add_row(
            "Policies",
            str(validation_result.source_counts['policies']),
            str(validation_result.target_counts['policies']),
            status_icon(validation_result.policy_count_match)
        )
        
        table.add_row(
            "Ledger Events",
            f"{validation_result.source_counts['ledger']:,}",
            f"{validation_result.target_counts['ledger']:,}",
            status_icon(validation_result.ledger_count_match)
        )
        
        table.add_row(
            f"Spot Check ({spot_check_count} samples)",
            "-",
            "-",
            status_icon(validation_result.spot_check_passed)
        )
        
        console.print(table)
        console.print()
        
        if validation_result.valid:
            console.print("[bold green]✓ Validation passed![/bold green]")
        else:
            console.print("[bold red]✗ Validation failed[/bold red]")
            
            if validation_result.errors:
                console.print()
                console.print("[bold]Errors:[/bold]")
                for error in validation_result.errors:
                    console.print(f"  [red]• {error}[/red]")
            
            sys.exit(1)
        
        # Close database connection
        session.close()
        db_manager.close()
    
    except Exception as e:
        console.print(f"[red]Error: Validation failed: {e}[/red]")
        if ctx.verbose:
            import traceback
            console.print()
            console.print("[bold]Traceback:[/bold]")
            console.print(traceback.format_exc())
        sys.exit(1)


def _display_migration_results(
    agents_result: Optional[MigrationResult],
    policies_result: Optional[MigrationResult],
    ledger_result: Optional[MigrationResult],
):
    """Display migration results in a formatted table."""
    
    table = Table(title="Migration Summary", show_header=True, header_style="bold cyan")
    table.add_column("Component", style="cyan")
    table.add_column("Migrated", justify="right", style="green")
    table.add_column("Skipped", justify="right", style="yellow")
    table.add_column("Errors", justify="right", style="red")
    
    total_migrated = 0
    total_skipped = 0
    total_errors = 0
    
    if agents_result:
        table.add_row(
            "Agents",
            str(agents_result.migrated_count),
            str(agents_result.skipped_count),
            str(agents_result.error_count)
        )
        total_migrated += agents_result.migrated_count
        total_skipped += agents_result.skipped_count
        total_errors += agents_result.error_count
    
    if policies_result:
        table.add_row(
            "Policies",
            str(policies_result.migrated_count),
            str(policies_result.skipped_count),
            str(policies_result.error_count)
        )
        total_migrated += policies_result.migrated_count
        total_skipped += policies_result.skipped_count
        total_errors += policies_result.error_count
    
    if ledger_result:
        table.add_row(
            "Ledger Events",
            f"{ledger_result.migrated_count:,}",
            str(ledger_result.skipped_count),
            str(ledger_result.error_count)
        )
        total_migrated += ledger_result.migrated_count
        total_skipped += ledger_result.skipped_count
        total_errors += ledger_result.error_count
    
    table.add_row(
        "[bold]Total[/bold]",
        f"[bold]{total_migrated:,}[/bold]",
        f"[bold]{total_skipped}[/bold]",
        f"[bold]{total_errors}[/bold]"
    )
    
    console.print(table)
    
    # Display errors if any
    if total_errors > 0:
        console.print()
        console.print("[bold yellow]Errors occurred during migration:[/bold yellow]")
        
        all_errors = []
        if agents_result:
            all_errors.extend(agents_result.errors)
        if policies_result:
            all_errors.extend(policies_result.errors)
        if ledger_result:
            all_errors.extend(ledger_result.errors)
        
        for error in all_errors[:10]:  # Show first 10 errors
            console.print(f"  [red]• {error}[/red]")
        
        if len(all_errors) > 10:
            console.print(f"  [yellow]... and {len(all_errors) - 10} more errors[/yellow]")
