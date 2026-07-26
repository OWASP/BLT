//! Entrypoint and Orchestrator for the OWASP BLT TUI & MCP Subprocess Client.
//!
//! This module coordinates the CLI arguments parsing, connections set up, TUI terminal configuration,
//! and main loop startup sequence.
//!
//! Lifecycle Steps:
//! 1. Parses CLI parameters (`Args`) using `clap` to resolve local MCP subprocess server paths (`--mcp-path`)
//!    and the target API URL base (`--api-base`).
//! 2. Spawns and configures the Python MCP subprocess server via stdin/stdout piping if a path is specified.
//! 3. Queries the initialized server resources (`blt://v2/bugs`, `/repos`, `/stats`, `/leaderboard`, `/good-first-issues`)
//!    to populate the initial dashboard views.
//! 4. If no server path is specified, it runs in standalone mode by fetching data directly from the REST API.
//! 5. Spawns background local security scan routines using tokio threads.
//! 6. Configures raw terminal input capture modes and installs a custom panic hook to restore standard terminal views on crashes.
//! 7. Runs the main event runner loop defined in `tui::run_app`.
//!
//! Helper Functions:
//! - `split_arguments(s: &str) -> Vec<String>`: Custom string parser that splits executable shell commands (e.g. `uv run -m blt_mcp`)
//!   into separate tokens, respecting single and double quotes.

use clap::Parser;

use crossterm::{
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{backend::CrosstermBackend, Terminal};
use std::io;

mod api;
mod app;
mod mcp_client;
mod models;
mod scanner;
mod tui;
mod ui;

use app::App;

#[derive(Parser, Debug)]
#[command(name = "blt-cli")]
#[command(about = "OWASP BLT High-Velocity Terminal UI (TUI) & MCP Client", long_about = None)]
struct Args {
    /// Explicit local path to launch the Python MCP server subprocess (e.g. "uv run -m blt_mcp.server")
    #[arg(short, long)]
    mcp_path: Option<String>,

    /// Target URL base for direct BLT API interactions
    #[arg(short, long, default_value = "https://api.owaspblt.org")]
    api_base: String,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Parse arguments
    let args = Args::parse();

    // Load .env fallback values if not specified
    let _ = dotenvy::dotenv();

    // Check fallback env for mcp-path if CLI option is not given
    let mcp_path = args.mcp_path.or_else(|| std::env::var("BLT_MCP_PATH").ok());
    let api_base = std::env::var("BLT_API_BASE").unwrap_or(args.api_base);

    // Create App instance
    let mut app = App::new(mcp_path.clone(), api_base.clone());

    if let Some(ref mcp_srv) = mcp_path {
        println!("Connecting to local MCP subprocess: {} ...", mcp_srv);
        let parts = split_arguments(mcp_srv);
        if parts.is_empty() {
            println!("ERROR: Empty MCP server path provided");
            return Ok(());
        }
        let executable = &parts[0];
        let args_slice = &parts[1..];
        match mcp_client::McpSubprocessClient::spawn(executable, args_slice).await {
            Ok(mut client) => {
                match client.initialize().await {
                    Ok(_) => {
                        println!("Connected to MCP server. Loading resources...");
                        let mut issues_loaded = false;
                        let mut repos_loaded = false;

                        // Attempt to read issues resource
                        if let Ok(resp) = client.read_resource("blt://v2/bugs").await {
                            if let Some(contents) = resp
                                .get("result")
                                .and_then(|r| r.get("contents"))
                                .and_then(|c| c.as_array())
                            {
                                if let Some(content) = contents.first() {
                                    if let Some(text) = content.get("text").and_then(|t| t.as_str())
                                    {
                                        if let Ok(root) =
                                            serde_json::from_str::<serde_json::Value>(text)
                                        {
                                            if let Ok(issues) =
                                                crate::api::parse_issues_from_json(&root)
                                            {
                                                app.issues = issues;
                                                issues_loaded = true;
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        // Attempt to read repos resource
                        if let Ok(resp) = client.read_resource("blt://v2/repos").await {
                            if let Some(contents) = resp
                                .get("result")
                                .and_then(|r| r.get("contents"))
                                .and_then(|c| c.as_array())
                            {
                                if let Some(content) = contents.first() {
                                    if let Some(text) = content.get("text").and_then(|t| t.as_str())
                                    {
                                        if let Ok(root) =
                                            serde_json::from_str::<serde_json::Value>(text)
                                        {
                                            if let Ok(repos) =
                                                crate::api::parse_repos_from_json(&root)
                                            {
                                                app.repos = repos;
                                                repos_loaded = true;
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // Attempt to read stats resource
                        if let Ok(resp) = client.read_resource("blt://v2/stats").await {
                            if let Some(contents) = resp
                                .get("result")
                                .and_then(|r| r.get("contents"))
                                .and_then(|c| c.as_array())
                            {
                                if let Some(content) = contents.first() {
                                    if let Some(text) = content.get("text").and_then(|t| t.as_str())
                                    {
                                        if let Ok(root) =
                                            serde_json::from_str::<serde_json::Value>(text)
                                        {
                                            app.stats = crate::api::parse_stats_from_json(&root);
                                        }
                                    }
                                }
                            }
                        }

                        // Attempt to read leaderboard resource
                        if let Ok(resp) = client.read_resource("blt://v2/leaderboard").await {
                            if let Some(contents) = resp
                                .get("result")
                                .and_then(|r| r.get("contents"))
                                .and_then(|c| c.as_array())
                            {
                                if let Some(content) = contents.first() {
                                    if let Some(text) = content.get("text").and_then(|t| t.as_str())
                                    {
                                        if let Ok(root) =
                                            serde_json::from_str::<serde_json::Value>(text)
                                        {
                                            app.leaderboard =
                                                crate::api::parse_leaderboard_from_json(&root);
                                        }
                                    }
                                }
                            }
                        }

                        // Attempt to read good-first-issues resource
                        if let Ok(resp) = client.read_resource("blt://good-first-issues").await {
                            if let Some(contents) = resp
                                .get("result")
                                .and_then(|r| r.get("contents"))
                                .and_then(|c| c.as_array())
                            {
                                if let Some(content) = contents.first() {
                                    if let Some(text) = content.get("text").and_then(|t| t.as_str())
                                    {
                                        if let Ok(root) =
                                            serde_json::from_str::<serde_json::Value>(text)
                                        {
                                            app.good_first_issues =
                                                crate::api::parse_good_first_issues_from_json(
                                                    &root,
                                                );
                                        }
                                    }
                                }
                            }
                        }

                        if issues_loaded && repos_loaded {
                            app.audit_logs.push(
                                "SUCCESS: Connected to live MCP server. Awaiting live events..."
                                    .to_string(),
                            );
                            app.status_message =
                                "MCP connection established successfully!".to_string();
                            app.is_live = true;
                            app.mcp_client =
                                Some(std::sync::Arc::new(tokio::sync::Mutex::new(client)));
                            println!("SUCCESS: Connected to MCP server and loaded live resources.");
                        } else {
                            app.is_live = true;
                            app.mcp_client =
                                Some(std::sync::Arc::new(tokio::sync::Mutex::new(client)));
                            app.status_message =
                                "MCP connected, but failed to load primary resources.".to_string();
                            println!("WARNING: Connected to MCP server, but failed to load primary resources.");
                        }
                    }
                    Err(e) => {
                        app.status_message = format!("MCP Init failed: {}", e);
                        println!("ERROR: MCP handshake/initialization failed: {}", e);
                    }
                }
            }
            Err(e) => {
                app.status_message = format!("MCP spawn failed: {}", e);
                println!("ERROR: Failed to spawn MCP subprocess: {}", e);
            }
        }
    } else {
        // Standalone Mode: Fetch from live API base
        println!("Connecting to live API base: {} ...", api_base);

        let mut any_success = false;

        match api::get_issues(&api_base).await {
            Ok(issues) => {
                app.issues = issues;
                any_success = true;
            }
            Err(e) => {
                println!("  - Issues Fetch Error: {}", e);
            }
        }

        match api::get_repos(&api_base).await {
            Ok(repos) => {
                if !repos.is_empty() {
                    app.repos = repos;
                }
                any_success = true;
            }
            Err(e) => {
                println!("  - Repos Fetch Error: {}", e);
            }
        }

        match api::get_hunts(&api_base).await {
            Ok(hunts) => {
                app.hunts = hunts;
                any_success = true;
            }
            Err(e) => {
                println!("  - Hunts Fetch Error: {}", e);
            }
        }

        match api::get_stats(&api_base).await {
            Ok(stats) => {
                app.stats = stats;
                any_success = true;
            }
            Err(e) => {
                println!("  - Stats Fetch Error: {}", e);
            }
        }

        match api::get_leaderboard(&api_base).await {
            Ok(leaderboard) => {
                app.leaderboard = leaderboard;
                any_success = true;
            }
            Err(e) => {
                println!("  - Leaderboard Fetch Error: {}", e);
            }
        }

        if any_success {
            app.status_message = "Connected to API (loaded live data where available).".to_string();
            app.is_live = true;
            println!("SUCCESS: Connected to API base successfully.");
        } else {
            app.status_message = "API connection failed.".to_string();
            println!("ERROR: All API endpoints failed to connect.");
        }
    }

    println!("Starting TUI session...");

    // Spawn the security health scanner in the background
    let scanner_sender = app.event_sender.clone();
    tokio::spawn(async move {
        let health = scanner::run_scan().await;
        let _ = scanner_sender.send(app::AppEvent::ScanComplete { health });
    });

    // Initialize terminal
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    // Set custom panic hook to restore terminal on panics
    let original_hook = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |panic_info| {
        let _ = disable_raw_mode();
        let mut stdout = io::stdout();
        let _ = execute!(stdout, LeaveAlternateScreen);
        original_hook(panic_info);
    }));

    let was_live = app.is_live;

    // Run TUI main event loop
    let res = tui::run_app(&mut terminal, app);

    // Restore terminal state on exit
    disable_raw_mode()?;
    execute!(terminal.backend_mut(), LeaveAlternateScreen)?;
    terminal.show_cursor()?;

    if let Err(err) = res {
        println!("Error running BLT-CLI: {:?}", err);
    } else {
        println!("OWASP BLT TUI Session Closed.");
        if let Some(ref srv) = mcp_path {
            if was_live {
                println!(
                    "Status: Successfully connected to local MCP server at [{}].",
                    srv
                );
            } else {
                println!("Status: Failed to connect to local MCP server.");
            }
        } else if was_live {
            println!(
                "Status: Successfully connected to live API base at [{}].",
                api_base
            );
        } else {
            println!("Status: Failed to connect to API base at [{}].", api_base);
        }
    }

    Ok(())
}

fn split_arguments(s: &str) -> Vec<String> {
    let mut args = Vec::new();
    let mut current = String::new();
    let mut in_double_quotes = false;
    let mut in_single_quotes = false;
    let mut chars = s.chars().peekable();

    while let Some(c) = chars.next() {
        match c {
            '"' if !in_single_quotes => {
                in_double_quotes = !in_double_quotes;
            }
            '\'' if !in_double_quotes => {
                in_single_quotes = !in_single_quotes;
            }
            ' ' | '\t' if !in_double_quotes && !in_single_quotes => {
                if !current.is_empty() {
                    args.push(current);
                    current = String::new();
                }
            }
            _ => {
                current.push(c);
            }
        }
    }
    if !current.is_empty() {
        args.push(current);
    }
    args
}
