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
    # This implementation is now handled by the menu system in wait_for_action
    # or rather, wait_for_action is now the main entry point for the welcome screen
    pass


def wait_for_action(console: Optional[Console] = None) -> str:
    """
    Display welcome screen and wait for user action using a menu.
    
    Returns:
        Action key: 'continue', 'new', or 'quit'
    """
    from caracal.flow.components.menu import Menu, MenuItem
    
    console = console or Console()
    
    # Define menu items
    items = [
        MenuItem(
            key="continue",
            label="Continue to Main Menu",
            description="Access dashboard and management tools",
            icon=Icons.ARROW_RIGHT
        ),
        MenuItem(
            key="new",
            label="New Agent Setup",
            description="Run the onboarding wizard",
            icon="➕"
        ),
        MenuItem(
            key="quit",
            label="Quit",
            description="Exit Caracal Flow",
            icon="✖"
        ),
    ]
    
    # Create menu with banner as header
    banner = BANNER_COMPACT if (console.width < 75) else BANNER
    
    menu = Menu(
        title="",  # Banner used as header
        items=items,
        show_hints=True,
    )
    
    # Custom run loop to show banner
    while True:
        console.clear()
        console.print(f"[{Colors.PRIMARY}]{banner}[/]")
        console.print(f"  [{Colors.DIM}]Version {__version__}[/]")
        console.print()
        
        # We need to manually invoke the menu rendering here or just use menu.run()
        # utilizing menu.run() is simpler but we need to ensure the banner is shown
        # The Menu class usually handles its own clearing/printing.
        # Let's trust Menu to handle navigation, but we might lose the persistent banner 
        # if Menu heavily manages the screen. 
        # Looking at main_menu.py, it uses menu.run().
        
        # Let's adapt to use Menu properly
        result = menu.run()
        
        if result:
            return result.key
            
        return "quit"
