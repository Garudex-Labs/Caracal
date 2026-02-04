"""
Caracal Flow Welcome Screen.

Displays:
- ASCII art banner
- Version info
- Quick action shortcuts
"""

import shutil
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from caracal._version import __version__
from caracal.flow.theme import BANNER, BANNER_COMPACT, Colors, Icons


def show_welcome(
    console: Optional[Console] = None,
    compact: bool = False,
) -> None:
    """
    Display the welcome screen.
    
    Args:
        console: Rich console (creates new if not provided)
        compact: Use compact banner for small terminals
    """
    console = console or Console()
    
    # Clear screen
    console.clear()
    
    # Detect terminal size for responsive banner
    term_width = shutil.get_terminal_size().columns
    use_compact = compact or term_width < 75
    
    # Display banner
    banner = BANNER_COMPACT if use_compact else BANNER
    console.print(f"[{Colors.PRIMARY}]{banner}[/]")
    
    # Version info
    console.print(f"  [{Colors.DIM}]Version {__version__}[/]")
    console.print()
    
    # Quick shortcuts
    console.print(f"  [{Colors.HINT}]Quick Start:[/]")
    console.print()
    
    shortcuts = [
        (Icons.ARROW_RIGHT, "Press Enter", "to continue to main menu"),
        ("n", "n", "for new agent setup"),
        ("q", "q", "to quit"),
    ]
    
    for icon, key, desc in shortcuts:
        if icon == Icons.ARROW_RIGHT:
            console.print(f"    [{Colors.PRIMARY}]{icon}[/] [{Colors.NEUTRAL}]{key}[/] [{Colors.DIM}]{desc}[/]")
        else:
            console.print(f"    [{Colors.HINT}][{key}][/] [{Colors.DIM}]{desc}[/]")
    
    console.print()


def show_tips(console: Optional[Console] = None) -> None:
    """Show helpful tips on the welcome screen."""
    console = console or Console()
    
    tips = [
        f"{Icons.ARROW_UP}{Icons.ARROW_DOWN} Use arrow keys to navigate menus",
        "Tab for auto-complete suggestions",
        "Esc or 'q' to go back",
        "Ctrl+C to exit anytime",
    ]
    
    tip_text = Text()
    tip_text.append(f"\n  {Icons.INFO} Tips:\n", style=f"bold {Colors.INFO}")
    
    for tip in tips:
        tip_text.append(f"    {Icons.BULLET} {tip}\n", style=Colors.DIM)
    
    console.print(tip_text)


def wait_for_action(console: Optional[Console] = None) -> str:
    """
    Wait for user action on welcome screen.
    
    Returns:
        Action key: 'continue', 'new', or 'quit'
    """
    console = console or Console()
    
    console.print(f"  [{Colors.HINT}]Press Enter to continue...[/]", end="")
    
    try:
        action = input()
        if action.lower() == 'n':
            return 'new'
        elif action.lower() == 'q':
            return 'quit'
        return 'continue'
    except KeyboardInterrupt:
        return 'quit'
    except EOFError:
        return 'quit'
