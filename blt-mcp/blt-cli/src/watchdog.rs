use std::sync::Arc;
use std::time::Duration;
use tokio::sync::Mutex;

use crate::app::AppEvent;
use crate::mcp_client::McpSubprocessClient;

/// Configuration for the watchdog.
#[derive(Clone, Debug)]
pub struct WatchdogConfig {
    /// How often to send a heartbeat ping.
    pub ping_interval: Duration,
    /// How many consecutive failed pings before declaring dead.
    pub max_failures: u32,
    /// How many times to attempt auto-restart.
    pub max_restarts: u32,
    /// Delay between restart attempts.
    pub restart_delay: Duration,
}

impl Default for WatchdogConfig {
    fn default() -> Self {
        Self {
            ping_interval: Duration::from_secs(30),
            max_failures: 3,
            max_restarts: 5,
            restart_delay: Duration::from_secs(2),
        }
    }
}

/// Heartbeat result sent back to the TUI event loop.
#[derive(Clone, Debug, PartialEq)]
pub enum WatchdogEvent {
    Degraded { consecutive_failures: u32 },
    Disconnected { reason: String },
    Reconnected { attempt: u32 },
    Fatal { reason: String },
}

pub async fn run_watchdog(
    client: Arc<Mutex<McpSubprocessClient>>,
    cmd_name: String,
    cmd_args: Vec<String>,
    config: WatchdogConfig,
    event_sender: tokio::sync::mpsc::UnboundedSender<AppEvent>,
) {
    let mut failures = 0u32;
    let mut restarts = 0u32;

    loop {
        tokio::time::sleep(config.ping_interval).await;

        // Try acquiring lock and sending a lightweight ping with a short timeout to prevent UI freezes
        let lock_result = tokio::time::timeout(Duration::from_secs(2), client.lock()).await;

        let ping_ok = match lock_result {
            Ok(mut guard) => guard
                .ping_with_timeout(Duration::from_secs(3))
                .await
                .is_ok(),
            Err(_) => {
                // Lock acquisition timed out because an active tool execution is holding the lock.
                // Since an active request is running, the client channel is active.
                true
            }
        };

        if ping_ok {
            if failures > 0 {
                // Recovered from degraded state
                failures = 0;
            }
            continue;
        }

        failures += 1;
        let _ = event_sender.send(AppEvent::WatchdogStatus {
            event: WatchdogEvent::Degraded {
                consecutive_failures: failures,
            },
        });

        if failures < config.max_failures {
            continue;
        }

        // Subprocess appears dead — attempt restart
        if restarts >= config.max_restarts {
            let _ = event_sender.send(AppEvent::WatchdogStatus {
                event: WatchdogEvent::Fatal {
                    reason: format!("Max restarts ({}) exceeded", config.max_restarts),
                },
            });
            return; // Give up
        }

        let _ = event_sender.send(AppEvent::WatchdogStatus {
            event: WatchdogEvent::Disconnected {
                reason: format!("{} consecutive ping failures", failures),
            },
        });

        tokio::time::sleep(config.restart_delay).await;
        restarts += 1;

        // Attempt respawn
        let new_client = McpSubprocessClient::spawn(&cmd_name, &cmd_args).await.ok();

        if let Some(mut c) = new_client {
            if c.initialize().await.is_ok() {
                *client.lock().await = c;
                failures = 0;
                let _ = event_sender.send(AppEvent::WatchdogStatus {
                    event: WatchdogEvent::Reconnected { attempt: restarts },
                });
            }
        }
    }
}
