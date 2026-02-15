"""
Caracal Flow Onboarding Screen.

First-run setup wizard with:
- Step 1: Configuration path selection
- Step 2: Database setup (optional)
- Step 3: First principal registration
- Step 4: First authority policy creation
- Step 5: Issue first mandate
- Step 6: Validate mandate demo
- Skip options with actionable to-dos
"""

from pathlib import Path
from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from caracal.flow.components.prompt import FlowPrompt
from caracal.flow.components.wizard import Wizard, WizardStep
from caracal.flow.state import FlowState, StatePersistence, RecentAction
from caracal.flow.theme import Colors, Icons


def _get_db_config_from_env() -> dict:
    """Load database configuration from .env file."""
    config = {
        "host": "localhost",
        "port": 5432,
        "database": "caracal",
        "username": "caracal",
        "password": "",
    }
    try:
        env_path = Path.cwd() / ".env"
        if env_path.exists():
            import re
            content = env_path.read_text()
            mapping = {
                "host": r"^DB_HOST=(.*)$",
                "port": r"^DB_PORT=(.*)$",
                "database": r"^DB_NAME=(.*)$",
                "username": r"^DB_USER=(.*)$",
                "password": r"^DB_PASSWORD=(.*)$",
            }
            for key, pattern in mapping.items():
                match = re.search(pattern, content, re.MULTILINE)
                if match:
                    val = match.group(1).strip()
                    if key == "port":
                        try:
                            config[key] = int(val)
                        except ValueError:
                            pass
                    else:
                        config[key] = val
    except Exception:
        pass
    return config


def _save_db_config_to_env(config: dict) -> bool:
    """Save database configuration back to .env file."""
    try:
        env_path = Path.cwd() / ".env"
        if env_path.exists():
            import re
            content = env_path.read_text()
            mapping = {
                "DB_HOST": config.get("host", "localhost"),
                "DB_PORT": str(config.get("port", 5432)),
                "DB_NAME": config.get("database", "caracal"),
                "DB_USER": config.get("username", "caracal"),
                "DB_PASSWORD": config.get("password", ""),
            }
            for key, val in mapping.items():
                if re.search(f"^{key}=", content, re.MULTILINE):
                    content = re.sub(f"^{key}=.*$", f"{key}={val}", content, flags=re.MULTILINE)
                else:
                    content += f"\n{key}={val}"
            env_path.write_text(content)
            return True
    except Exception:
        pass
    return False


def _test_db_connection(config: dict) -> tuple[bool, str]:
    """Test PostgreSQL connection with given config."""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=config.get("host", "localhost"),
            port=int(config.get("port", 5432)),
            database=config.get("database", "caracal"),
            user=config.get("username", "caracal"),
            password=config.get("password", ""),
            connect_timeout=5
        )
        conn.close()
        return True, ""
    except Exception as e:
        return False, str(e)


def _step_workspace(wizard: Wizard) -> Any:
    """Step 0: Workspace selection/creation/deletion.
    
    CRITICAL: This step cannot be skipped. A workspace must be selected
    or created before proceeding to the main menu, as it defines where
    all configuration and data will be stored.
    
    Returns:
        str: Path to the selected/created workspace
        
    Raises:
        RuntimeError: If no workspace is selected (should never happen)
        KeyboardInterrupt: If user cancels (propagates to caller)
    """
    console = wizard.console
    prompt = FlowPrompt(console)
    
    from caracal.flow.workspace import WorkspaceManager, set_workspace
    
    console.print(f"  [{Colors.NEUTRAL}]Caracal can manage multiple workspaces (organizations).")
    console.print(f"  [{Colors.DIM}]Each workspace has its own configuration, data, and agents.[/]")
    console.print()
    
    # List existing workspaces
    workspaces = WorkspaceManager.list_workspaces()
    
    if workspaces:
        console.print(f"  [{Colors.INFO}]{Icons.INFO} Existing workspaces:[/]")
        console.print()
        
        from rich.table import Table
        table = Table(show_header=True, header_style=f"bold {Colors.PRIMARY}", border_style=Colors.DIM)
        table.add_column("#", style=Colors.NEUTRAL, width=4)
        table.add_column("Name", style=Colors.INFO)
        table.add_column("Path", style=Colors.DIM)
        
        for idx, ws in enumerate(workspaces, 1):
            table.add_row(str(idx), ws["name"], ws["path"])
        
        console.print(table)
        console.print()
    
    # Present options
    choices = []
    if workspaces:
        choices.append("Select existing workspace")
    choices.extend([
        "Create new workspace",
    ])
    if workspaces:
        choices.append("Delete workspace")
    
    action = prompt.select(
        "What would you like to do?",
        choices=choices,
    )
    
    # Handle workspace selection
    if action == "Select existing workspace":
        workspace_names = [ws["name"] for ws in workspaces]
        selected_name = prompt.select(
            "Select workspace",
            choices=workspace_names,
        )
        
        selected_ws = next(ws for ws in workspaces if ws["name"] == selected_name)
        workspace_path = Path(selected_ws["path"])
        
        console.print()
        console.print(f"  [{Colors.SUCCESS}]{Icons.SUCCESS} Selected workspace: {selected_name}[/]")
        console.print(f"  [{Colors.DIM}]Path: {workspace_path}[/]")
        
        # Set the selected workspace as active
        set_workspace(workspace_path)
        wizard.context["workspace_path"] = str(workspace_path)
        wizard.context["workspace_name"] = selected_name
        wizard.context["workspace_existing"] = True
        
        return str(workspace_path)
    
    elif action == "Create new workspace":
        console.print()
        workspace_name = prompt.text(
            "Workspace name",
            default="my-workspace",
        )
        
        # Generate path from name
        default_base = Path.home() / ".caracal"
        workspace_path = default_base / workspace_name.lower().replace(" ", "-")
        
        custom_path = prompt.confirm(
            f"Use default path ({workspace_path})?",
            default=True,
        )
        
        if not custom_path:
            path_str = prompt.text(
                "Enter workspace directory path",
                default=str(workspace_path),
            )
            workspace_path = Path(path_str).expanduser()
        
        console.print()
        console.print(f"  [{Colors.INFO}]{Icons.INFO} Creating workspace: {workspace_name}[/]")
        console.print(f"  [{Colors.DIM}]Path: {workspace_path}[/]")
        
        # Create directory
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        # Register workspace
        WorkspaceManager.register_workspace(workspace_name, workspace_path)
        
        console.print(f"  [{Colors.SUCCESS}]{Icons.SUCCESS} Workspace created and registered[/]")
        
        # Set the new workspace as active
        set_workspace(workspace_path)
        wizard.context["workspace_path"] = str(workspace_path)
        wizard.context["workspace_name"] = workspace_name
        wizard.context["workspace_existing"] = False
        wizard.context["fresh_start"] = True
        
        return str(workspace_path)
    
    elif action == "Delete workspace":
        workspace_names = [ws["name"] for ws in workspaces]
        selected_name = prompt.select(
            "Select workspace to delete",
            choices=workspace_names,
        )
        
        selected_ws = next(ws for ws in workspaces if ws["name"] == selected_name)
        workspace_path = Path(selected_ws["path"])
        
        console.print()
        console.print(f"  [{Colors.WARNING}]⚠️  WARNING: This will delete workspace '{selected_name}'[/]")
        console.print(f"  [{Colors.DIM}]Path: {workspace_path}[/]")
        console.print()
        
        delete_files = prompt.confirm(
            "Also delete workspace directory from disk?",
            default=False,
        )
        
        confirm = prompt.confirm(
            f"Are you sure you want to delete '{selected_name}'?",
            default=False,
        )
        
        if confirm:
            WorkspaceManager.delete_workspace(
                workspace_path,
                delete_directory=delete_files,
            )
            console.print()
            console.print(f"  [{Colors.SUCCESS}]{Icons.SUCCESS} Workspace deleted[/]")
            console.print()
            
            # Restart workspace selection
            return _step_workspace(wizard)
        else:
            console.print()
            console.print(f"  [{Colors.INFO}]{Icons.INFO} Deletion cancelled[/]")
            console.print()
            # Restart workspace selection
            return _step_workspace(wizard)
    
    # This should never be reached, but handle it gracefully
    console.print()
    console.print(f"  [{Colors.ERROR}]{Icons.ERROR} No workspace action selected[/]")
    raise RuntimeError("Workspace selection is required to continue")


def _step_config(wizard: Wizard) -> Any:
    """Step 1: Configuration setup."""
    console = wizard.console
    prompt = FlowPrompt(console)
    
    from caracal.flow.workspace import get_workspace
    
    # If workspace was selected/created in previous step, use that
    workspace_path = wizard.context.get("workspace_path")
    if workspace_path:
        config_path = Path(workspace_path)
    else:
        config_path = get_workspace().root
    
    # If workspace was just created, skip the existing config check
    if wizard.context.get("workspace_existing") is False:
        console.print(f"  [{Colors.INFO}]{Icons.INFO} Initializing new workspace configuration...[/]")
        
        try:
            _initialize_caracal_dir(config_path, wipe=True)
            console.print(f"  [{Colors.SUCCESS}]{Icons.SUCCESS} Configuration initialized at {config_path}[/]")
        except Exception as e:
            console.print(f"  [{Colors.ERROR}]{Icons.ERROR} Failed: {e}[/]")
            raise
        
        wizard.context["config_path"] = str(config_path)
        return str(config_path)
    
    console.print(f"  [{Colors.NEUTRAL}]Caracal stores its configuration and data files in a directory.")
    console.print(f"  [{Colors.DIM}]Location: {config_path}[/]")
    console.print()
    
    # Determine if we should wipe based on whether we found existing config and user rejected it
    wipe = False
    if config_path.exists() and (config_path / "config.yaml").exists():
        console.print(f"  [{Colors.SUCCESS}]{Icons.SUCCESS} Configuration found at {config_path}[/]")
        console.print()
        
        use_existing = prompt.confirm(
            "Use existing configuration?",
            default=True,
        )
        
        if use_existing:
            wizard.context["config_path"] = str(config_path)
            
            # Check if user wants to start fresh with data
            if prompt.confirm("Reset database (clear all data)?", default=False):
                wizard.context["fresh_start"] = True
                
            return str(config_path)
        else:
            wipe = True
            wizard.context["fresh_start"] = True
    console.print()
    
    # Initialize directory structure
    console.print()
    console.print(f"  [{Colors.INFO}]{Icons.INFO} Initializing configuration...[/]")
    
    try:
        _initialize_caracal_dir(config_path, wipe=wipe)
        console.print(f"  [{Colors.SUCCESS}]{Icons.SUCCESS} Configuration initialized at {config_path}[/]")
        wizard.context["config_path"] = str(config_path)
        return str(config_path)
    except Exception as e:
        console.print(f"  [{Colors.ERROR}]{Icons.ERROR} Failed to initialize: {e}[/]")
        raise


def _initialize_caracal_dir(path: Path, wipe: bool = False) -> None:
    """Initialize Caracal directory structure."""
    if wipe and path.exists():
        import shutil
        # Wipe data files but keep the directory
        for item in path.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir() and item.name != "backups":
                shutil.rmtree(item)

    # Create directories
    path.mkdir(parents=True, exist_ok=True)
    (path / "backups").mkdir(exist_ok=True)
    
    # Create default config if needed
    config_path = path / "config.yaml"
    if not config_path.exists():
        default_config = f"""# Caracal Core Configuration

storage:
  agent_registry: {path}/agents.json
  policy_store: {path}/policies.json
  ledger: {path}/ledger.jsonl
  backup_dir: {path}/backups
  backup_count: 3

defaults:
  time_window: daily

logging:
  level: INFO
  file: {path}/caracal.log
"""
        config_path.write_text(default_config)
    
    # Create empty data files if needed
    agents_path = path / "agents.json"
    if not agents_path.exists():
        agents_path.write_text("[]")
    
    policies_path = path / "policies.json"
    if not policies_path.exists():
        policies_path.write_text("[]")
    
    ledger_path = path / "ledger.jsonl"
    if not ledger_path.exists():
        ledger_path.write_text("")
    
    # SQLite database file - should be wiped if fresh start
    db_path = path / "caracal.db"
    if db_path.exists() and wipe:
        db_path.unlink()


def _step_database(wizard: Wizard) -> Any:
    """Step 2: Database setup (optional)."""
    console = wizard.console
    prompt = FlowPrompt(console)
    
    # 1. Try automatic setup from .env
    env_config = _get_db_config_from_env()
    if env_config.get("password"):
        console.print()
        console.print(f"  [{Colors.INFO}]{Icons.INFO} Testing PostgreSQL connection...[/]")
        
        success, error = _test_db_connection(env_config)
        
        if success:
            console.print(f"  [{Colors.SUCCESS}]{Icons.SUCCESS} PostgreSQL connected successfully![/]")
            console.print(f"  [{Colors.DIM}]Host: {env_config['host']}:{env_config['port']}[/]")
            console.print(f"  [{Colors.DIM}]Database: {env_config['database']}[/]")
            console.print()
            
            # Auto-configure without prompting
            wizard.context["database"] = {**env_config, "type": "postgresql"}
            wizard.context["database_auto_configured"] = True
            return wizard.context["database"]
        else:
            console.print(f"  [{Colors.WARNING}]PostgreSQL connection failed: {error}[/]")
            if "password authentication failed" in error.lower():
                console.print(f"  [{Colors.HINT}]{Icons.INFO} Tip: Run './reset_postgres.sh' to sync credentials.[/]")
            console.print()
    
    # 2. Ask if user wants PostgreSQL (simple Y/N)
    console.print(f"  [{Colors.NEUTRAL}]Database Setup:[/]")
    console.print(f"  [{Colors.DIM}]• PostgreSQL: Production-ready, scalable database[/]")
    console.print(f"  [{Colors.DIM}]• SQLite: Simple file-based storage (default)[/]")
    console.print()
    
    use_postgres = prompt.confirm(
        "Use PostgreSQL?",
        default=False,
    )
    
    if not use_postgres:
        console.print()
        console.print(f"  [{Colors.INFO}]{Icons.INFO} Using SQLite (file-based storage)[/]")
        wizard.context["database"] = "file"
        return "file"
    
    # 3. Auto-setup PostgreSQL with standard config
    console.print()
    console.print(f"  [{Colors.INFO}]{Icons.INFO} Setting up PostgreSQL...[/]")
    
    # Use environment config or defaults
    config = {
        "host": env_config.get("host", "localhost"),
        "port": int(env_config.get("port", 5432)),
        "database": env_config.get("database", "caracal"),
        "username": env_config.get("username", "caracal"),
        "password": env_config.get("password", "caracal"),
    }
    
    console.print(f"  [{Colors.DIM}]Host: {config['host']}:{config['port']}[/]")
    console.print(f"  [{Colors.DIM}]Database: {config['database']}[/]")
    console.print(f"  [{Colors.DIM}]Username: {config['username']}[/]")
    console.print()
    
    # Test the connection
    console.print(f"  [{Colors.INFO}]{Icons.INFO} Testing connection...[/]")
    success, error = _test_db_connection(config)
    
    if success:
        console.print(f"  [{Colors.SUCCESS}]{Icons.SUCCESS} PostgreSQL configured successfully![/]")
        
        # Save config to .env
        if _save_db_config_to_env(config):
            console.print(f"  [{Colors.SUCCESS}]{Icons.SUCCESS} Configuration saved to .env[/]")
        
        wizard.context["database"] = {**config, "type": "postgresql"}
        return wizard.context["database"]
    else:
        console.print(f"  [{Colors.ERROR}]{Icons.ERROR} Connection failed: {error}[/]")
        console.print()
        console.print(f"  [{Colors.INFO}]{Icons.INFO} Falling back to SQLite[/]")
        console.print(f"  [{Colors.DIM}]Make sure PostgreSQL is running on {config['host']}:{config['port']}[/]")
        console.print(f"  [{Colors.DIM}]You can configure PostgreSQL later from settings[/]")
        console.print()
        
        wizard.context["database"] = "file"
        return "file"


def _step_principal(wizard: Wizard) -> Any:
    """Step 3: Register first principal."""
    console = wizard.console
    prompt = FlowPrompt(console)
    
    # Get system username for better defaults
    import os
    import getpass
    system_user = getpass.getuser()
    default_name = f"{system_user}-admin"
    default_email = f"{system_user}@localhost"
    
    console.print(f"  [{Colors.NEUTRAL}]Let's register your first principal.")
    console.print(f"  [{Colors.DIM}]This will be your admin user account.[/]")
    console.print()
    
    principal_type = prompt.select(
        "Principal type",
        choices=["user", "agent", "service"],
        default="user",
    )
    
    name = prompt.text(
        "Principal name",
        default=default_name,
    )
    
    owner = prompt.text(
        "Owner email",
        default=default_email,
    )
    
    # Store for later
    wizard.context["first_principal"] = {
        "name": name,
        "owner": owner,
        "type": principal_type,
    }
    
    console.print()
    console.print(f"  [{Colors.INFO}]{Icons.INFO} Principal will be registered after setup completes.[/]")
    console.print(f"  [{Colors.DIM}]Name: {name}[/]")
    console.print(f"  [{Colors.DIM}]Owner: {owner}[/]")
    console.print(f"  [{Colors.DIM}]Type: {principal_type}[/]")
    
    return wizard.context["first_principal"]


def _step_policy(wizard: Wizard) -> Any:
    """Step 4: Create first authority policy."""
    console = wizard.console
    prompt = FlowPrompt(console)
    
    principal_info = wizard.context.get("first_principal", {})
    principal_name = principal_info.get("name", "the principal")
    
    console.print(f"  [{Colors.NEUTRAL}]Now let's create an authority policy for {principal_name}.")
    console.print(f"  [{Colors.DIM}]Policies define how mandates can be issued.[/]")
    console.print()
    
    max_validity = prompt.number(
        "Maximum mandate validity (seconds)",
        default=3600,
        min_value=60,
    )
    
    wizard.context["first_policy"] = {
        "max_validity_seconds": int(max_validity),
        "resource_patterns": ["api:*", "database:*"],
        "actions": ["api_call", "database_query"],
    }
    
    console.print()
    console.print(f"  [{Colors.INFO}]{Icons.INFO} Policy will be created after setup completes.[/]")
    console.print(f"  [{Colors.DIM}]Max Validity: {int(max_validity)}s[/]")
    
    return wizard.context["first_policy"]


def _step_mandate(wizard: Wizard) -> Any:
    """Step 5: Issue first mandate."""
    console = wizard.console
    prompt = FlowPrompt(console)
    
    principal_info = wizard.context.get("first_principal", {})
    principal_name = principal_info.get("name", "the principal")
    
    console.print(f"  [{Colors.NEUTRAL}]Let's issue an execution mandate for {principal_name}.")
    console.print(f"  [{Colors.DIM}]Mandates grant specific execution rights for a limited time.[/]")
    console.print()
    
    validity = prompt.number(
        "Mandate validity (seconds)",
        default=1800,
        min_value=60,
    )
    
    wizard.context["first_mandate"] = {
        "validity_seconds": int(validity),
        "resource_scope": ["api:openai:*"],
        "action_scope": ["api_call"],
    }
    
    console.print()
    console.print(f"  [{Colors.INFO}]{Icons.INFO} Mandate will be issued after setup completes.[/]")
    console.print(f"  [{Colors.DIM}]Validity: {int(validity)}s[/]")
    
    return wizard.context["first_mandate"]


def _step_validate(wizard: Wizard) -> Any:
    """Step 6: Validate mandate demo."""
    console = wizard.console
    
    console.print(f"  [{Colors.NEUTRAL}]Finally, we'll demonstrate mandate validation.")
    console.print(f"  [{Colors.DIM}]This shows how authority is checked before execution.[/]")
    console.print()
    
    console.print(f"  [{Colors.INFO}]{Icons.INFO} Validation demo will run after setup completes.[/]")
    
    wizard.context["validate_demo"] = True
    
    return True


def run_onboarding(
    console: Optional[Console] = None,
    state: Optional[FlowState] = None,
) -> dict[str, Any]:
    """
    Run the onboarding wizard.
    
    Args:
        console: Rich console
        state: Application state
    
    Returns:
        Dictionary of collected information
    """
    console = console or Console()
    
    # Define wizard steps
    steps = [
        WizardStep(
            key="workspace",
            title="Workspace Setup",
            description="Select, create, or delete a workspace",
            action=_step_workspace,
            skippable=False,
        ),
        WizardStep(
            key="config",
            title="Configuration Setup",
            description="Set up Caracal's configuration directory and files",
            action=_step_config,
            skippable=False,
        ),
        WizardStep(
            key="database",
            title="Database Setup",
            description="Configure database connection (optional)",
            action=_step_database,
            skippable=True,
            skip_message="Using default file-based storage",
        ),
        WizardStep(
            key="principal",
            title="Register First Principal",
            description="Create your first principal identity",
            action=_step_principal,
            skippable=True,
            skip_message="You can register principals later from the main menu",
        ),
        WizardStep(
            key="policy",
            title="Create First Authority Policy",
            description="Set up an authority policy for your principal",
            action=_step_policy,
            skippable=True,
            skip_message="You can create policies later from the main menu",
        ),
        WizardStep(
            key="mandate",
            title="Issue First Mandate",
            description="Create an execution mandate",
            action=_step_mandate,
            skippable=True,
            skip_message="You can issue mandates later from the main menu",
        ),
        WizardStep(
            key="validate",
            title="Validate Mandate Demo",
            description="Demonstrate mandate validation",
            action=_step_validate,
            skippable=True,
            skip_message="You can validate mandates later from the main menu",
        ),
    ]
    
    # Run wizard
    wizard = Wizard(
        title="Welcome to Caracal Flow",
        steps=steps,
        console=console,
    )
    
    results = wizard.run()
    
    # Validate that workspace was selected (critical requirement)
    if not wizard.context.get("workspace_path"):
        console.print()
        console.print(f"  [{Colors.ERROR}]{Icons.ERROR} No workspace selected. Cannot proceed without a workspace.[/]")
        console.print(f"  [{Colors.INFO}]{Icons.INFO} A workspace is required to store your configuration and data.[/]")
        console.print()
        results["workspace_configured"] = False
        return results
    
    results["workspace_configured"] = True
    
    # Show summary
    wizard.show_summary()
    
    # Persist changes
    try:
        from pathlib import Path
        from caracal.config import load_config
        from caracal.db.connection import DatabaseConfig, DatabaseConnectionManager
        from caracal.db.models import Principal, AuthorityPolicy
        from datetime import datetime
        from uuid import uuid4
        from caracal.flow.workspace import get_workspace
        
        # Load fresh config (in case it was just initialized)
        config = load_config()
        
        # Save database configuration if provided
        db_config_data = results.get("database")
        if db_config_data and isinstance(db_config_data, dict) and db_config_data.get("type") == "postgresql":
            console.print()
            console.print(f"  [{Colors.INFO}]{Icons.INFO} Saving database configuration...[/]")
            
            # Update config file with database settings
            import yaml
            
            config_path = wizard.context.get("config_path", get_workspace().root)
            config_file = Path(config_path) / "config.yaml"
            
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config_yaml = yaml.safe_load(f) or {}
                
                # Update database section
                config_yaml['database'] = {
                    'type': 'postgres',
                    'host': db_config_data['host'],
                    'port': db_config_data['port'],
                    'database': db_config_data['database'],
                    'user': db_config_data['username'],
                    'password': db_config_data['password'],
                }
                
                with open(config_file, 'w') as f:
                    yaml.dump(config_yaml, f, default_flow_style=False)
                
                console.print(f"  [{Colors.SUCCESS}]{Icons.SUCCESS} PostgreSQL configuration saved to config.yaml[/]")
                
                # Reload config
                config = load_config()
        elif db_config_data == "file":
            console.print()
            console.print(f"  [{Colors.INFO}]{Icons.INFO} Using SQLite (file-based storage)[/]")
        
        # Setup database connection - prioritize wizard results over existing config
        if db_config_data == "file":
            # User explicitly selected SQLite in wizard
            db_config = DatabaseConfig(
                type='sqlite',
                file_path=str(get_workspace().db_path),
            )
        elif db_config_data == "postgresql":
            # User explicitly selected PostgreSQL in wizard (should have env vars)
            db_config = DatabaseConfig(
                type='postgresql',
                host=env_vars.get('PGHOST', 'localhost'),
                port=int(env_vars.get('PGPORT', '5432')),
                database=env_vars['PGDATABASE'],
                user=env_vars['PGUSER'],
                password=env_vars.get('PGPASSWORD', ''),
            )
        elif hasattr(config, 'database') and config.database:
            # Fall back to existing config if wizard didn't complete
            db_config = DatabaseConfig(
                type=getattr(config.database, 'type', 'sqlite'),
                host=getattr(config.database, 'host', 'localhost'),
                port=getattr(config.database, 'port', 5432),
                database=getattr(config.database, 'database', 'caracal'),
                user=getattr(config.database, 'user', 'caracal'),
                password=getattr(config.database, 'password', ''),
                file_path=getattr(config.database, 'file_path', str(get_workspace().db_path)),
            )
        else:
            # Default to SQLite
            db_config = DatabaseConfig(
                type='sqlite',
                file_path=str(get_workspace().db_path),
            )
        
        db_manager = DatabaseConnectionManager(db_config)
        db_manager.initialize()
        
        # Only clean database if explicitly requested or if it's a new workspace with fresh start
        # Do NOT clean database if it was auto-configured from .env without user confirmation
        should_clean = (
            wizard.context.get("fresh_start") and 
            not wizard.context.get("database_auto_configured")
        )
        
        if should_clean:
            try:
                console.print()
                console.print(f"  [{Colors.INFO}]{Icons.INFO} Cleaning database for fresh start...[/]")
                with db_manager.session_scope() as db_session:
                    from sqlalchemy import text
                    # Truncate tables in correct order (mandates -> policies -> principals)
                    if db_config.type == 'postgresql':
                        db_session.execute(text("TRUNCATE TABLE execution_mandates CASCADE"))
                        db_session.execute(text("TRUNCATE TABLE authority_policies CASCADE"))
                        db_session.execute(text("TRUNCATE TABLE principals CASCADE"))
                    else:
                        db_session.execute(text("DELETE FROM execution_mandates"))
                        db_session.execute(text("DELETE FROM authority_policies"))
                        db_session.execute(text("DELETE FROM principals"))
                console.print(f"  [{Colors.SUCCESS}]{Icons.SUCCESS} Database cleaned for fresh start.[/]")
            except Exception as e:
                console.print(f"  [{Colors.WARNING}]{Icons.WARNING} Failed to clean database: {e}[/]")
        
        # Handle Principal Registration
        principal_data = results.get("principal")
        principal_id = None
        
        if principal_data:
            console.print()
            console.print(f"  [{Colors.INFO}]{Icons.INFO} Finalizing setup...[/]")
            
            try:
                with db_manager.session_scope() as db_session:
                    # Check if principal already exists
                    existing = db_session.query(Principal).filter_by(
                        name=principal_data["name"]
                    ).first()
                    
                    if existing:
                        principal_id = existing.principal_id
                        console.print(f"  [{Colors.SUCCESS}]{Icons.SUCCESS} Principal already exists, reusing.[/]")
                        console.print(f"  [{Colors.DIM}]Principal ID: {principal_id}[/]")
                    else:
                        principal = Principal(
                            name=principal_data["name"],
                            principal_type=principal_data["type"],
                            owner=principal_data["owner"],
                            created_at=datetime.utcnow(),
                        )
                        
                        db_session.add(principal)
                        db_session.flush()
                        
                        principal_id = principal.principal_id
                        console.print(f"  [{Colors.SUCCESS}]{Icons.SUCCESS} Principal registered successfully.[/]")
                        console.print(f"  [{Colors.DIM}]Principal ID: {principal_id}[/]")
            except Exception as e:
                console.print(f"  [{Colors.ERROR}]{Icons.ERROR} Failed to register principal: {e}[/]")
        
        # Handle Authority Policy Creation
        policy_data = results.get("policy")
        if policy_data and principal_id:
            try:
                with db_manager.session_scope() as db_session:
                    # Check if a policy already exists for this principal
                    existing_policy = db_session.query(AuthorityPolicy).filter_by(
                        principal_id=principal_id,
                        active=True,
                    ).first()
                    
                    if existing_policy:
                        console.print(f"  [{Colors.SUCCESS}]{Icons.SUCCESS} Authority policy already exists, skipping.[/]")
                    else:
                        policy = AuthorityPolicy(
                            policy_id=uuid4(),
                            principal_id=principal_id,
                            max_validity_seconds=policy_data["max_validity_seconds"],
                            allowed_resource_patterns=policy_data["resource_patterns"],
                            allowed_actions=policy_data["actions"],
                            allow_delegation=True,
                            max_delegation_depth=3,
                            created_at=datetime.utcnow(),
                            created_by=principal_data["owner"] if principal_data else "system",
                            active=True,
                        )
                        
                        db_session.add(policy)
                        
                        console.print(f"  [{Colors.SUCCESS}]{Icons.SUCCESS} Authority policy created successfully.[/]")
            except Exception as e:
                console.print(f"  [{Colors.ERROR}]{Icons.ERROR} Failed to create policy: {e}[/]")
        
        # Close database connection
        db_manager.close()
                
    except Exception as e:
        console.print(f"  [{Colors.ERROR}]{Icons.ERROR} Error saving configuration: {e}[/]")
        import traceback
        traceback.print_exc()

    # Update state
    if state:
        state.onboarding.mark_complete()
        for step in steps:
            if step.status.value == "completed":
                state.onboarding.mark_step_complete(step.key)
            elif step.status.value == "skipped":
                state.onboarding.mark_step_skipped(step.key)
        
        # Save state
        persistence = StatePersistence()
        persistence.save(state)
    
    # Show next steps
    _show_next_steps(console, results, wizard.context)
    
    return results


def _show_next_steps(console: Console, results: dict, context: dict) -> None:
    """Show actionable next steps after onboarding."""
    console.print()
    console.print(f"  [{Colors.INFO}]{Icons.INFO} Next Steps:[/]")
    console.print()
    
    todos = []
    
    # Check what was skipped
    if results.get("principal") is None:
        todos.append(("Register a principal", "caracal authority register --name my-principal --owner user@example.com"))
    
    if results.get("policy") is None:
        todos.append(("Create an authority policy", "caracal authority-policy create --principal-id <uuid> --max-validity 3600"))
    
    if results.get("mandate") is None:
        todos.append(("Issue an execution mandate", "caracal authority issue --issuer-id <uuid> --subject-id <uuid>"))
    
    if results.get("database") == "file":
        todos.append(("Consider PostgreSQL for production", "Set database.type: postgresql in config.yaml"))
    
    # Always suggest viewing the ledger
    todos.append(("Explore your authority ledger", "caracal authority-ledger query"))
    
    for i, (title, cmd) in enumerate(todos, 1):
        console.print(f"  [{Colors.NEUTRAL}]{i}. {title}[/]")
        console.print(f"     [{Colors.DIM}]{cmd}[/]")
        console.print()
    
    console.print(f"  [{Colors.HINT}]Press Enter to continue to the main menu...[/]")
    input()
