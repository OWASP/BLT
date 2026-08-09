# OWASP BLT TUI CLI (`blt-cli`)

A high-performance terminal user interface (TUI) client for the OWASP Bug Logging Tool (BLT) ecosystem. Built in Rust using **Ratatui** and **Crossterm**, `blt-cli` provides developer-friendly dashboards for triaging issues, tracking bounty hunts, viewing statistics, and interacting with the BLT-MCP server.

---

## 🚀 Key Features

* **Ecosystem Dashboards:** Tab-based views for browsing issues, hunts, statistics, logs, and configurations.
* **Interactive Issue Triage:** Easily update issue statuses with human-in-the-loop safeguards and background network execution.
* **Bulk Triage & Selection:** Select multiple issues at once and rapidly triage them to specific states (Open, In Review, Resolved).
* **Search & Filter:** Instantly filter issues and hunts using an inline, interactive search overlay.
* **Audit & Event Logging:** Dedicated Logs & Events tab to track real-time agent/human actions and background network syncs.
* **Session Persistence:** State is automatically preserved upon exiting, retaining audit logs and event feed history across restarts.
* **Log Exporting:** Instantly dump your session's action history to a local text file (`blt_export.log`) at the press of a key.
* **Vulnerability Submission:** Quickly submit new vulnerability reports directly from the TUI with an interactive multi-field form.
* **Bounty Hunts Hub:** Browse active bug bounty hunts, view detailed rules/rewards, and seamlessly launch pre-filled vulnerability forms for specific targets.
* **Dynamic Leaderboard:** View the active top contributors and their accrued bacon in the statistics dashboard.
* **AI-Assisted Triage:** Leverage an integrated MCP (Model Context Protocol) tool to run AI analysis on vulnerabilities, fetching real-time suggestions and duplicate checks.
* **Dual-Mode execution:**
  * **Standalone Mode:** Connects directly to the REST endpoints of the BLT API.
  * **MCP Mode:** Acts as an MCP host, spawning the Python `blt-mcp` server in a subprocess.
* **Offline Sandbox (`--offline`):** Loaded with full mock datasets for completely offline UI iteration without API credentials.

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
| `Tab` / `BackTab` | Navigation | Switch focus sequentially between main tabs or input fields. |
| `1` - `4` | Numeric Jumps | Switch directly to a tab (1: Issues, 2: Hunts, 3: Stats, 4: Settings). |
| `Arrow Up/Down` / `j`/`k` | Scroll | Navigate list items/vulnerabilities logs. |
| `h` / `?` | Help Overlay | Toggle the help keyboard shortcut quick legend. |
| `t` | Triage Issue | Trigger status transition (`In Review`) modal for selected issue. |
| `s` | Submit Issue | Open the Submit Vulnerability form (also works in Hunt Details to pre-fill). |
| `a` | AI Triage | Trigger an AI-Assisted MCP analysis on the currently selected vulnerability. |
| `Enter` | Confirm/Details | Approve modal actions, or open detailed views (e.g., Hunt Details). |
| `Esc` | Cancel/Dismiss | Dismiss popups, modals, forms, or abort operations. |
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
