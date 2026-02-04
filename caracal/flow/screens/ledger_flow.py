"""
Caracal Flow Ledger Flow Screen.

Ledger exploration:
- Query builder (visual filters)
- Spending summary dashboard
- Delegation chain visualizer
"""

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from caracal.flow.components.menu import show_menu
from caracal.flow.components.prompt import FlowPrompt
from caracal.flow.theme import Colors, Icons


def run_ledger_flow(console: Optional[Console] = None) -> None:
    """Run the ledger exploration flow."""
    console = console or Console()
    
    while True:
        console.clear()
        
        action = show_menu(
            title="Ledger Explorer",
            items=[
                ("query", "Query Events", "Search ledger events with filters"),
                ("summary", "Spending Summary", "View aggregated spending"),
                ("chain", "Delegation Chain", "Visualize agent relationships"),
            ],
            subtitle="Explore spending history and relationships",
        )
        
        if action is None:
            break
        
        console.clear()
        
        if action == "query":
            _query_events(console)
        elif action == "summary":
            _spending_summary(console)
        elif action == "chain":
            _delegation_chain(console)
        
        console.print()
        console.print(f"  [{Colors.HINT}]Press Enter to continue...[/]")
        input()


def _query_events(console: Console) -> None:
    """Query ledger events with filters."""
    prompt = FlowPrompt(console)
    
    console.print(Panel(
        f"[{Colors.NEUTRAL}]Search ledger events with optional filters[/]",
        title=f"[bold {Colors.INFO}]Query Events[/]",
        border_style=Colors.PRIMARY,
    ))
    console.print()
    
    # Build filters
    console.print(f"  [{Colors.INFO}]Optional Filters (press Enter to skip):[/]")
    console.print()
    
    agent_id = prompt.text("Agent ID", required=False)
    resource = prompt.text("Resource type", required=False)
    start_date = prompt.text("Start date (YYYY-MM-DD)", required=False)
    end_date = prompt.text("End date (YYYY-MM-DD)", required=False)
    
    try:
        from caracal.cli.ledger import get_ledger_query
        from caracal.config import load_config
        
        config = load_config()
        query = get_ledger_query(config)
        
        # Build filters
        filters = {}
        if agent_id:
            filters["agent_id"] = agent_id
        if resource:
            filters["resource_type"] = resource
        if start_date:
            filters["start_time"] = start_date
        if end_date:
            filters["end_time"] = end_date
        
        events = query.query_events(**filters)
        
        console.print()
        
        if not events:
            console.print(f"  [{Colors.DIM}]No events found matching filters.[/]")
            return
        
        # Display results
        table = Table(show_header=True, header_style=f"bold {Colors.INFO}")
        table.add_column("Time", style=Colors.DIM)
        table.add_column("Agent", style=Colors.DIM)
        table.add_column("Resource", style=Colors.NEUTRAL)
        table.add_column("Units", style=Colors.NEUTRAL)
        table.add_column("Cost", style=Colors.SUCCESS)
        
        for event in events[:20]:  # Limit display
            table.add_row(
                str(event.timestamp)[:19],
                event.agent_id[:8] + "...",
                event.resource_type[:20],
                str(event.units),
                f"${float(event.cost):.4f}",
            )
        
        console.print(table)
        
        if len(events) > 20:
            console.print(f"  [{Colors.DIM}]...and {len(events) - 20} more events[/]")
        
        console.print()
        console.print(f"  [{Colors.DIM}]Total: {len(events)} events[/]")
        
    except ImportError:
        args = []
        if agent_id:
            args.append(f"--agent-id {agent_id}")
        if resource:
            args.append(f"--resource {resource}")
        if start_date:
            args.append(f"--start {start_date}")
        if end_date:
            args.append(f"--end {end_date}")
        _show_cli_command(console, "ledger", "query", " ".join(args))
    except Exception as e:
        console.print(f"  [{Colors.ERROR}]{Icons.ERROR} Error: {e}[/]")


def _spending_summary(console: Console) -> None:
    """Show spending summary."""
    prompt = FlowPrompt(console)
    
    console.print(Panel(
        f"[{Colors.NEUTRAL}]View aggregated spending by agent[/]",
        title=f"[bold {Colors.INFO}]Spending Summary[/]",
        border_style=Colors.PRIMARY,
    ))
    console.print()
    
    try:
        from caracal.cli.ledger import get_ledger_query, get_agent_registry
        from caracal.config import load_config
        
        config = load_config()
        query = get_ledger_query(config)
        registry = get_agent_registry(config)
        
        # Get all agents
        agents = registry.list_all()
        
        if not agents:
            console.print(f"  [{Colors.DIM}]No agents registered.[/]")
            return
        
        # Option to filter by agent
        filter_agent = prompt.confirm("Filter by specific agent?", default=False)
        agent_filter = None
        
        if filter_agent:
            items = [(a.agent_id, a.name) for a in agents]
            agent_filter = prompt.uuid("Agent ID", items)
        
        # Get summary
        summary = query.get_spending_summary(agent_id=agent_filter)
        
        console.print()
        
        if not summary:
            console.print(f"  [{Colors.DIM}]No spending data available.[/]")
            return
        
        # Display summary
        table = Table(show_header=True, header_style=f"bold {Colors.INFO}")
        table.add_column("Agent", style=Colors.NEUTRAL)
        table.add_column("Total Spent", style=Colors.SUCCESS)
        table.add_column("Events", style=Colors.NEUTRAL)
        
        for row in summary:
            agent_name = next((a.name for a in agents if a.agent_id == row["agent_id"]), row["agent_id"][:8])
            table.add_row(
                agent_name,
                f"${float(row['total_spent']):.2f}",
                str(row["event_count"]),
            )
        
        console.print(table)
        
    except ImportError:
        _show_cli_command(console, "ledger", "summary", "")
    except Exception as e:
        console.print(f"  [{Colors.ERROR}]{Icons.ERROR} Error: {e}[/]")


def _delegation_chain(console: Console) -> None:
    """Visualize delegation chain."""
    prompt = FlowPrompt(console)
    
    console.print(Panel(
        f"[{Colors.NEUTRAL}]Visualize parent-child agent relationships[/]",
        title=f"[bold {Colors.INFO}]Delegation Chain[/]",
        border_style=Colors.PRIMARY,
    ))
    console.print()
    
    try:
        from caracal.cli.agent import get_agent_registry
        from caracal.config import load_config
        
        config = load_config()
        registry = get_agent_registry(config)
        agents = registry.list_all()
        
        if not agents:
            console.print(f"  [{Colors.DIM}]No agents registered.[/]")
            return
        
        items = [(a.agent_id, a.name) for a in agents]
        agent_id = prompt.uuid("Agent ID (Tab for suggestions)", items)
        
        agent = registry.get(agent_id)
        if not agent:
            console.print(f"  [{Colors.ERROR}]{Icons.ERROR} Agent not found[/]")
            return
        
        console.print()
        console.print(f"  [{Colors.INFO}]Delegation Chain for {agent.name}:[/]")
        console.print()
        
        # Find ancestors
        ancestors = []
        current = agent
        while current.parent_id:
            parent = registry.get(current.parent_id)
            if parent:
                ancestors.insert(0, parent)
                current = parent
            else:
                break
        
        # Display chain
        indent = 0
        for ancestor in ancestors:
            console.print(f"  {'  ' * indent}[{Colors.DIM}]↓[/] [{Colors.NEUTRAL}]{ancestor.name}[/] [{Colors.DIM}]({ancestor.agent_id[:8]}...)[/]")
            indent += 1
        
        # Current agent
        console.print(f"  {'  ' * indent}[{Colors.PRIMARY}]★[/] [{Colors.PRIMARY}]{agent.name}[/] [{Colors.DIM}]({agent.agent_id[:8]}...)[/]")
        indent += 1
        
        # Find children
        children = [a for a in agents if a.parent_id == agent_id]
        for child in children:
            console.print(f"  {'  ' * indent}[{Colors.DIM}]↓[/] [{Colors.NEUTRAL}]{child.name}[/] [{Colors.DIM}]({child.agent_id[:8]}...)[/]")
        
        if not ancestors and not children:
            console.print(f"  [{Colors.DIM}]This agent has no parent or children.[/]")
        
    except ImportError:
        agent_id = prompt.text("Enter agent ID")
        _show_cli_command(console, "ledger", "delegation-chain", f"--agent-id {agent_id}")
    except Exception as e:
        console.print(f"  [{Colors.ERROR}]{Icons.ERROR} Error: {e}[/]")


def _show_cli_command(console: Console, group: str, command: str, args: str) -> None:
    """Show the equivalent CLI command."""
    console.print()
    console.print(f"  [{Colors.HINT}]Run this command instead:[/]")
    console.print(f"  [{Colors.DIM}]$ caracal {group} {command} {args}[/]")
