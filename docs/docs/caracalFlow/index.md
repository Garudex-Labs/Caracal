---
sidebar_position: 1
title: Caracal Flow
---

# Caracal Flow

Terminal-based user interface (TUI) for managing your Caracal deployment. Rich, interactive experience without memorizing CLI commands.

---

## What is Caracal Flow?

Flow makes Caracal accessible to everyone:

- **Visual menus** with arrow-key navigation
- **Guided wizards** for complex tasks
- **Real-time feedback** with rich colors and indicators
- **No CLI knowledge required** for basic operations

```
+------------------------------------------------------------------+
|                                                                   |
|                        CARACAL FLOW                               |
|               Interactive Terminal Interface                      |
|                                                                   |
+------------------------------------------------------------------+
|                                                                   |
|    +----------------------------------------------------+         |
|    |  Main Menu                                         |         |
|    +----------------------------------------------------+         |
|    |  -> Agents         Register and manage             |         |
|    |     Policies       Budget limits                   |         |
|    |     Ledger         Spending history                |         |
|    |     Pricebook      Resource pricing                |         |
|    |     Delegation     Parent-child budgets            |         |
|    |     Settings       Configuration                   |         |
|    |     Help           Documentation                   |         |
|    +----------------------------------------------------+         |
|                                                                   |
|     Up/Down Navigate   Enter Select   q Quit   ? Help             |
|                                                                   |
+------------------------------------------------------------------+
```

---

## Flow vs Core CLI

| Task | Use Flow | Use Core CLI |
|------|:--------:|:------------:|
| First-time setup | Yes | |
| Register agents | Yes | Yes |
| Create budgets | Yes | Yes |
| View spending | Yes | Yes |
| Automation/scripting | | Yes |
| Merkle verification | | Yes |
| Key rotation | | Yes |
| Recovery operations | | Yes |

**Rule of thumb:** Use Flow for interactive work, use [Core CLI](/caracalCore/cliReference/) for automation or advanced operations.

See [Core vs Flow](/caracalCore/concepts/coreVsFlow) for a detailed comparison.

---

## Getting Started

### Quick Launch

```bash
# Start Caracal Flow
caracal-flow

# Or with UV
uv run caracal-flow
```

### First Run

On first launch, Flow runs an onboarding wizard:

1. **Configuration Setup** - Choose where to store Caracal data
2. **Database Setup** - Configure PostgreSQL or use file-based storage
3. **Register First Agent** - Create your first AI agent identity
4. **Create First Policy** - Set up initial budget limits

### Command-Line Options

```bash
caracal-flow [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--reset` | Reset state and restart onboarding |
| `--compact` | Use compact mode for small terminals |
| `--no-onboarding` | Skip onboarding even on first run |
| `--version` | Show version and exit |
| `--help` | Show help message |

---

## Feature Overview

### Agent Management

Register, view, and configure AI agents:

- Create new agents with names and owners
- Add metadata for organization
- Create parent-child relationships
- View agent details and history

### Policy Configuration

Set up and manage spending limits:

- Create daily/weekly/monthly budgets
- Choose calendar or rolling windows
- View active policies per agent
- Quick budget adjustments

### Spending Dashboard

Monitor agent spending in real-time:

- View current spending vs budget
- See breakdown by operation type
- Track delegation chain spending
- Identify high-cost operations

### Settings and Infrastructure

Configure Caracal and manage infrastructure:

- View current configuration
- Edit config files
- Start/stop Docker services
- Check database and Kafka status
- Create and restore backups

### Delegation Center

Manage parent-child budget relationships:

- View all delegations
- See spending by child agents
- Quick status checks

---

## Keyboard Shortcuts

Navigate Flow efficiently with these shortcuts:

| Key | Action |
|-----|--------|
| `Up` / `k` | Move up in menus |
| `Down` / `j` | Move down in menus |
| `Enter` | Select / Confirm |
| `Tab` | Auto-complete in prompts |
| `Esc` / `q` | Go back / Cancel |
| `Ctrl+C` | Exit immediately |
| `?` | Show help |

---

## Documentation

### Getting Started

- **[Introduction](./gettingStarted/introduction)** - What is Caracal Flow?
- **[Quickstart](./gettingStarted/quickstart)** - Launch the TUI

### Guides

- **[Configuration](./guides/configuration)** - Customize Flow settings

---

## When to Use Core CLI Instead

While Flow handles most daily tasks, some operations require the Core CLI:

### Operations Only in CLI

1. **Merkle Verification** - Cryptographic integrity checks
2. **Event Replay** - Recover from failures
3. **DLQ Management** - Handle failed events
4. **Key Rotation** - Security operations
5. **Batch Operations** - Scripted automation
6. **Advanced Queries** - Complex ledger filters

<details>
<summary>CLI-only examples</summary>

```bash
# These require Core CLI, not Flow:

# Verify ledger integrity
caracal merkle verify --full

# Manage dead letter queue
caracal dlq list
caracal dlq process --retry-failed

# Generate inclusion proof
caracal merkle proof --event-id evt-001-aaaa-bbbb

# Rotate signing keys
caracal keys rotate --key-type merkle-signing
```

</details>

---

## Requirements

### System Requirements

- Python 3.10+
- Terminal with color support
- 80x24 minimum terminal size (120x40 recommended)

### Dependencies

Flow requires these Python packages (installed automatically):

- `rich` - Terminal formatting
- `prompt_toolkit` - Interactive prompts

### Installation

Flow is included with Caracal Core:

```bash
# Install Caracal (includes Flow)
pip install caracal-core

# Or with UV
uv pip install caracal-core
```

---

## Troubleshooting

### Flow won't start

```bash
# Check dependencies
pip install rich prompt_toolkit

# Try with verbose output
python -c "from caracal.flow.app import FlowApp; print('OK')"
```

### Colors don't display

Ensure your terminal supports ANSI colors. Try:
- Modern terminals: iTerm2, Windows Terminal, GNOME Terminal
- Set `TERM=xterm-256color` in your environment

### Screen too small

Use compact mode for small terminals:

```bash
caracal-flow --compact
```

### Reset everything

If something goes wrong, reset Flow state:

```bash
caracal-flow --reset
```

This clears onboarding state but preserves your agents and policies.

---

## Next Steps

<div className="row">
  <div className="col col--6">
    <div className="card">
      <div className="card__header">
        <h3>Introduction</h3>
      </div>
      <div className="card__body">
        Learn more about what Flow can do
      </div>
      <div className="card__footer">
        <a className="button button--primary button--block" href="./gettingStarted/introduction">
          Read More
        </a>
      </div>
    </div>
  </div>
  <div className="col col--6">
    <div className="card">
      <div className="card__header">
        <h3>Quickstart</h3>
      </div>
      <div className="card__body">
        Launch Flow and start managing
      </div>
      <div className="card__footer">
        <a className="button button--secondary button--block" href="./gettingStarted/quickstart">
          Get Started
        </a>
      </div>
    </div>
  </div>
</div>
