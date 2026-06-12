# 🥓 OWASP BLT TUI CLI (`blt-cli`)

A high-performance terminal user interface (TUI) client for the OWASP Bug Logging Tool (BLT) ecosystem. Built in Rust using **Ratatui** and **Crossterm**, `blt-cli` provides developer-friendly dashboards for triaging issues, tracking bounty hunts, viewing statistics, and interacting with the BLT-MCP server.

---

## 🚀 Key Features

* **Ecosystem Dashboards:** Tab-based views for browsing issues, hunts, statistics, and configurations.
* **Dual-Mode execution:**
  * **Standalone Mode:** Connects directly to the REST endpoints of the BLT API.
  * **MCP Mode:** Acts as an MCP host, spawning the Python `blt-mcp` server in a subprocess and exchanging standard JSON-RPC 2.0 frames over piped stdin/stdout.
* **Offline Sandbox (`--offline`):** Loaded with full mock datasets mimicking live API shapes. Allows testing and UI iterations completely offline without API credentials.
* **Human-in-the-Loop Safeguards:** Prompts confirmation dialogs for write operations (such as status updates/triage) before executing actions on the backend.
* **BLT Brand Theme:** Minimalist slate background (`#1E1E23`) combined with high-contrast text and primary red (`#E10101`) accents reserved for active selections and critical status changes.

---

## 🛠️ CLI Flags & Options

Configure execution modes directly via command-line arguments:

```bash
# Launch with local mock database datasets (Offline Mode)
blt-cli --offline

# Spawn Python MCP server subprocess to invoke protocol tools
blt-cli --mcp-path ../blt_mcp/server.py

# Query a custom or staging BLT REST API endpoint base
blt-cli --api-base https://staging.owaspblt.org
```

| Flag | Short | Environment Fallback | Description | Default |
| :--- | :--- | :--- | :--- | :--- |
| `--offline` | `-o` | - | Runs with mock data; bypasses networking. | `false` |
| `--mcp-path` | `-m` | `BLT_MCP_PATH` | Path to spawn the local Python MCP server. | `None` |
| `--api-base` | `-a` | `BLT_API_BASE` | Base URL path for the unified BLT REST API. | `https://api.owaspblt.org` |

---

## ⌨️ Keyboard Shortcuts Reference

| Key Code | Description | Action |
| :--- | :--- | :--- |
| `Tab` / `BackTab` | Tab Swapper | Switch focus sequentially between tabs. |
| `1` - `4` | Numeric Jumps | Switch directly to a tab (1: Issues, 2: Hunts, 3: Stats, 4: Settings). |
| `Arrow Up/Down` / `j`/`k` | Scroll | Navigate list items/vulnerabilities logs. |
| `h` / `?` | Help Overlay | Toggle the help keyboard shortcut quick legend. |
| `t` | Triage Issue | Trigger status transition (`In Review`) modal for selected issue. |
| `Enter` | Modal Confirm | Approve write-action triggers (active only inside modals). |
| `Esc` | Modal Cancel | Dismiss the help popup or abort triage modal. |
| `q` / `Ctrl+C` | Quit | Securely exit the terminal app and restore console state. |

---

## ⚙️ Compilation & Build Instructions

Ensure you have Rust and Cargo installed via [rustup.rs](https://rustup.rs/).

```bash
# 1. Navigate to the crate directory
cd blt-cli

# 2. Run formatting and clippy static analysis checks
cargo fmt --check
cargo clippy -- -D warnings

# 3. Compile and execute in debug mode (default to offline)
cargo run -- --offline

# 4. Build optimized release binary
cargo build --release
```
The compiled executable binary will be generated under `./target/release/blt-cli` (or `/target/release/blt-cli.exe` on Windows).
