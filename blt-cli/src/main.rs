use std::io;
use clap::Parser;
use crossterm::{
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{backend::CrosstermBackend, Terminal};

mod app;
mod ui;
mod tui;
mod mock_data;
mod api;
mod mcp_client;
mod scanner;

use app::App;

#[derive(Parser, Debug)]
#[command(name = "blt-cli")]
#[command(about = "OWASP BLT High-Velocity Terminal UI (TUI) & MCP Client", long_about = None)]
struct Args {
    /// Launch in offline mode using local mock database datasets
    #[arg(short, long, default_value_t = false)]
    offline: bool,

    /// Explicit local path to launch the Python MCP server subprocess (e.g. "../blt_mcp/server.py")
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
    let mut app = App::new(args.offline, mcp_path.clone(), api_base.clone());

    // If not offline, attempt to load live data
    if !args.offline {
        if let Some(ref mcp_srv) = mcp_path {
            println!("Connecting to local MCP subprocess: {} ...", mcp_srv);
            match mcp_client::McpSubprocessClient::spawn(mcp_srv).await {
                Ok(mut client) => {
                    match client.initialize().await {
                        Ok(_) => {
                            println!("Connected to MCP server. Loading resources...");
                            let mut issues_loaded = false;
                            let mut repos_loaded = false;

                            // Attempt to read issues resource
                            if let Ok(resp) = client.read_resource("blt://issues").await {
                                if let Some(contents) = resp.get("result").and_then(|r| r.get("contents")).and_then(|c| c.as_array()) {
                                    if let Some(content) = contents.first() {
                                        if let Some(text) = content.get("text").and_then(|t| t.as_str()) {
                                            if let Ok(root) = serde_json::from_str::<serde_json::Value>(text) {
                                                app.issues = crate::api::parse_issues_from_json(&root);
                                                issues_loaded = true;
                                            }
                                        }
                                    }
                                }
                            }
                            // Attempt to read repos resource
                            if let Ok(resp) = client.read_resource("blt://repos").await {
                                if let Some(contents) = resp.get("result").and_then(|r| r.get("contents")).and_then(|c| c.as_array()) {
                                    if let Some(content) = contents.first() {
                                        if let Some(text) = content.get("text").and_then(|t| t.as_str()) {
                                            if let Ok(root) = serde_json::from_str::<serde_json::Value>(text) {
                                                app.repos = crate::api::parse_repos_from_json(&root);
                                                repos_loaded = true;
                                            }
                                        }
                                    }
                                }
                            }

                            // Attempt to read stats resource
                            if let Ok(resp) = client.read_resource("blt://stats").await {
                                if let Some(contents) = resp.get("result").and_then(|r| r.get("contents")).and_then(|c| c.as_array()) {
                                    if let Some(content) = contents.first() {
                                        if let Some(text) = content.get("text").and_then(|t| t.as_str()) {
                                            if let Ok(root) = serde_json::from_str::<serde_json::Value>(text) {
                                                app.stats = crate::api::parse_stats_from_json(&root);
                                            }
                                        }
                                    }
                                }
                            }

                            if issues_loaded && repos_loaded {
                                app.hunts.clear(); // Clear mock hunts since MCP doesn't load them yet
                                app.leaderboard.clear(); // Clear mock leaderboard
                                app.audit_logs.clear(); // Clear old offline session logs
                                app.event_feed.clear(); // Clear old offline event feed
                                app.stats = crate::mock_data::Stats { total_issues: 0, active_repos: 0, total_contributors: 0, bacon_points: 0 }; // Clear mock stats
                                app.audit_logs.push("SUCCESS: Connected to live MCP server. Awaiting live events...".to_string());
                                app.status_message = "MCP connection established successfully!".to_string();
                                app.is_live = true;
                                app.mcp_client = Some(std::sync::Arc::new(tokio::sync::Mutex::new(client)));
                                println!("SUCCESS: Connected to MCP server and loaded live resources.");
                            } else {
                                app.mcp_client = Some(std::sync::Arc::new(tokio::sync::Mutex::new(client)));
                                app.status_message = "MCP connected, but failed to load resources. Mock fallback active.".to_string();
                                println!("WARNING: Connected to MCP server, but failed to load resources. Mock fallback active.");
                            }
                        }
                        Err(e) => {
                            app.status_message = format!("MCP Init failed: {}. Mock fallback active.", e);
                            println!("ERROR: MCP handshake/initialization failed: {}. Mock fallback active.", e);
                        }
                    }
                }
                Err(e) => {
                    app.status_message = format!("MCP spawn failed: {}. Mock fallback active.", e);
                    println!("ERROR: Failed to spawn MCP subprocess: {}. Mock fallback active.", e);
                }
            }
        } else {
            // Standalone Mode: Fetch from live API base
            println!("Connecting to live API base: {} ...", api_base);
            
            let mut any_success = false;

            match api::get_issues(&api_base, false).await {
                Ok(issues) => {
                    app.issues = issues;
                    any_success = true;
                }
                Err(e) => {
                    println!("  - Issues Fetch Error: {}", e);
                }
            }

            match api::get_repos(&api_base, false).await {
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

            match api::get_hunts(&api_base, false).await {
                Ok(hunts) => {
                    app.hunts = hunts;
                    any_success = true;
                }
                Err(e) => {
                    println!("  - Hunts Fetch Error: {}", e);
                }
            }

            match api::get_stats(&api_base, false).await {
                Ok(stats) => {
                    app.stats = stats;
                    any_success = true;
                }
                Err(e) => {
                    println!("  - Stats Fetch Error: {}", e);
                }
            }

            if any_success {
                app.status_message = "Connected to API (loaded live data where available).".to_string();
                app.is_live = true;
                println!("SUCCESS: Connected to API base successfully.");
            } else {
                app.status_message = "API connection failed. Used offline mock datasets fallback.".to_string();
                println!("ERROR: All API endpoints failed. Used offline mock datasets fallback.");
            }
        }
    } else {
        println!("Starting in Offline Mode (using local mock datasets)...");
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
        if args.offline {
            println!("Status: Offline Mode (used local mock datasets).");
        } else if let Some(ref srv) = mcp_path {
            if was_live {
                println!("Status: Successfully connected to local MCP server at [{}].", srv);
            } else {
                println!("Status: Failed to connect to local MCP server. Used offline mock datasets fallback.");
            }
        } else if was_live {
            println!("Status: Successfully connected to live API base at [{}].", api_base);
        } else {
            println!("Status: Failed to connect to API base at [{}]. Used offline mock datasets fallback.", api_base);
        }
    }

    Ok(())
}
