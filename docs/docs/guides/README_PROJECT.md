# Caracal

[![Version](https://img.shields.io/badge/version-0.4.0-blue.svg)](VERSION)
[![License](https://img.shields.io/badge/license-AGPL--3.0-green.svg)](LICENSE)

**Caracal** is an economic control plane for AI agents. It provides a robust infrastructure for budget enforcement, real-time metering, and secure ledger management.

---

## Options

Caracal provides two ways to interact with the platform:

### 1. Caracal Flow (Standard Use)
For standard users who want a guided experience with default configurations. 
*   **Command**: `uv run caracal-flow`
*   **Default**: Starts with minimal infrastructure using file-based SQLite storage.
*   **Upgrade**: Easily transition to production-grade infra via the built-in settings.

### 2. Caracal Core (Power Users)
For power users who require high customization and programmatic control.
*   **Command**: `caracal`
*   **Usage**: Ideal for CLI workflows, CI/CD integration, and custom scripting.
*   **Extensible**: Full access to the SDK and advanced environment configurations.

---

## Quickstart

### 1. Installation
Clone the repository and install dependencies using `uv`:

```bash
git clone https://github.com/Garudex-Labs/caracal.git
cd caracal
pip install -e .
```

### 2. Launch the TUI
Start the interactive dashboard:

```bash
uv run caracal-flow
```

### 3. Production Infrastructure
By default, Caracal uses **SQLite** and local file storage. To enable production-grade infrastructure (PostgreSQL, Kafka, Redis):

1.  Open `caracal-flow`.
2.  Navigate to **Settings & Config** -> **Infrastructure Setup**.
3.  Select **Start All Services**.
4.  All services will be provisioned via Docker automatically.

---

## CLI Usage (Caracal Core)

```bash
# Register an agent
caracal agents register --name "researcher"

# List policies
caracal policies list

# Check service status
caracal status
```

---

## Project Structure

*   `caracal/core/`: Budgeting, identity, and ledger logic.
*   `caracal/flow/`: Terminal UI (TUI) interactive experience.
*   `caracal/gateway/`: Policy enforcement proxy.
*   `deploy/docker/`: Production infrastructure definitions.

---

## License

Licensed under **AGPL-3.0**. See [LICENSE](LICENSE) for details.

---

**Developed by the Garudex Labs.**
