//! Terminal User Interface Event Loop and Asynchronous Event Coordinator.
//!
//! This module coordinates the primary runtime event loop for the Ratatui-based
//! terminal client. It handles 100ms periodic screen re-renders, polls crossterm
//! keyboard inputs, and processes background notifications transmitted across
//! asynchronous `tokio::sync::mpsc` channels.
//!
//! Module Structure:
//! - `actions`: Asynchronous background task spawners (vulnerability submission, AI triage, bulk actions).
//! - `input`: Keyboard routing, modal key interceptors, form text editing, and Konami code evaluation.
//!
//! Key Functions:
//! - `run_app(terminal, app)`: The root application runner loop.

pub mod actions;
pub mod input;

use std::io;
use std::time::{Duration, Instant};

use crossterm::event::{self, Event};
use ratatui::{backend::Backend, Terminal};

use crate::app::{App, AppEvent, VulnerabilityForm};
use crate::ui;
use input::handle_keys;

/// Primary application event loop.
///
/// Continuously renders UI updates via `ui::draw`, polls for keystroke events,
/// drains asynchronous task completions from `app.event_receiver`, and synchronizes
/// session state before quitting.
pub fn run_app<B: Backend>(terminal: &mut Terminal<B>, mut app: App) -> io::Result<()>
where
    std::io::Error: From<<B as Backend>::Error>,
{
    let tick_rate = Duration::from_millis(100);
    let mut last_tick = Instant::now();

    // Drain any leftover keyboard events (e.g. Enter key pressed to launch the binary)
    while event::poll(Duration::from_millis(0))? {
        let _ = event::read()?;
    }

    loop {
        terminal.draw(|f| ui::draw(f, &mut app))?;

        let timeout = tick_rate
            .checked_sub(last_tick.elapsed())
            .unwrap_or_else(|| Duration::from_secs(0));

        // Process asynchronous notifications from background tokio tasks
        while let Ok(event) = app.event_receiver.try_recv() {
            match event {
                AppEvent::TriageConfirmed {
                    issue_id,
                    success,
                    message,
                    target_status,
                } => {
                    if success {
                        if let Some(issue) = app.issues.iter_mut().find(|i| i.id == issue_id) {
                            issue.status = target_status.clone();
                            let comment = format!(
                                "{}: Manually confirmed & updated triage status for #{} to {} via TUI CLI.",
                                app.auth_user, issue_id, target_status
                            );
                            issue.comments.push(comment.clone());
                            app.audit_logs.push(comment);
                            app.audit_logs
                                .push("+10 Bacon (Pending Verification)".to_string());
                        }
                        app.selected_issues.remove(&issue_id);
                    }
                    app.event_feed.push(message.clone());
                    app.status_message = message;
                }
                AppEvent::SubmitResult { success, message } => {
                    app.event_feed.push(message.clone());
                    app.audit_logs.push(message.clone());
                    if success {
                        app.status_message = format!("SUCCESS: Operation completed! - {}", message);
                        app.submit_form = VulnerabilityForm::default();
                    } else {
                        app.status_message = format!("ERROR: {}", message);
                    }
                    app.save_session();
                }
                AppEvent::IssuesRefreshed { issues, total } => {
                    app.issues = issues;
                    app.selected_issue_index = app
                        .selected_issue_index
                        .min(app.issues.len().saturating_sub(1));
                    app.event_feed
                        .push(format!("Refreshed issues. Total: {}", total));
                    app.audit_logs
                        .push("Issues list refreshed after submission.".to_string());
                    app.save_session();
                }
                AppEvent::VisionDraftComplete { result, success } => {
                    if success {
                        let mut title = String::new();
                        let mut description = String::new();
                        let mut in_desc = false;

                        for line in result.lines() {
                            let upper_line = line.to_uppercase();
                            if upper_line.starts_with("TITLE:") {
                                title = line["TITLE:".len()..].trim().to_string();
                            } else if upper_line.starts_with("DESCRIPTION:") {
                                in_desc = true;
                                description = line["DESCRIPTION:".len()..].trim().to_string();
                            } else if in_desc {
                                description.push('\n');
                                description.push_str(line);
                            }
                        }

                        if description.is_empty() && !result.is_empty() {
                            description = result.clone();
                        }

                        if app.submit_form.title.is_empty() && !title.is_empty() {
                            app.submit_form.title = title;
                        }

                        let clean_desc = description.trim();
                        if !clean_desc.is_empty() {
                            if app.submit_form.description.is_empty()
                                || app.submit_form.description
                                    == crate::app::VISION_ANALYZING_PLACEHOLDER
                            {
                                app.submit_form.description = clean_desc.to_string();
                            } else {
                                app.submit_form.description = format!(
                                    "{}\n\n### AI Vision Analysis:\n{}",
                                    app.submit_form.description.trim(),
                                    clean_desc
                                );
                            }
                        }

                        app.status_message =
                            "Vision AI drafting complete. Review and submit.".to_string();
                        app.audit_logs
                            .push("Vision AI generated issue draft.".to_string());
                    } else {
                        if app.submit_form.description == crate::app::VISION_ANALYZING_PLACEHOLDER {
                            app.submit_form.description.clear();
                        }
                        app.status_message = format!("Vision AI failed: {}", result);
                        app.audit_logs.push(format!("Vision AI failed: {}", result));
                    }
                    app.save_session();
                }
                AppEvent::AiTriageResult { message, success } => {
                    app.ai_triage_result = Some(message.clone());
                    if success {
                        app.event_feed
                            .push("AI Triage analysis complete.".to_string());
                        app.audit_logs
                            .push("Agent triggered AI Triage analysis.".to_string());
                        app.status_message = "AI Triage analysis complete.".to_string();
                    } else {
                        app.event_feed
                            .push("AI Triage analysis failed.".to_string());
                        app.status_message = format!("AI Triage failed: {}", message);
                    }
                    app.save_session();
                }
                AppEvent::ScanComplete { health } => {
                    app.security_health = Some(health);
                    app.event_feed
                        .push("Security Health Scan complete.".to_string());
                    app.save_session();
                }
                AppEvent::ClipboardExtracted { result } => {
                    match result {
                        Ok(path_str) => {
                            app.vision_image_path = path_str;
                            app.vision_context_input.clear();
                            app.active_overlay = crate::app::ActiveOverlay::VisionContext;
                            app.status_message =
                                "Specify optional Vision AI context hints and press Enter."
                                    .to_string();
                        }
                        Err(err_msg) => {
                            app.status_message = err_msg;
                        }
                    }
                    app.save_session();
                }
                AppEvent::WatchdogStatus { event } => {
                    match event {
                        crate::watchdog::WatchdogEvent::Degraded {
                            consecutive_failures,
                        } => {
                            app.status_message =
                                format!("⚠ MCP: {} ping failures", consecutive_failures);
                        }
                        crate::watchdog::WatchdogEvent::Disconnected { reason } => {
                            app.status_message =
                                format!("🔴 MCP disconnected: {}. Restarting...", reason);
                            app.is_live = false;
                        }
                        crate::watchdog::WatchdogEvent::Reconnected { attempt } => {
                            app.status_message =
                                format!("🟢 MCP reconnected (attempt #{})", attempt);
                            app.is_live = true;
                        }
                        crate::watchdog::WatchdogEvent::Fatal { reason } => {
                            app.status_message = format!("❌ MCP watchdog gave up: {}", reason);
                            app.is_live = false;
                        }
                    }
                    app.save_session();
                }
            }
        }

        if event::poll(timeout)? {
            if let Event::Key(key) = event::read()? {
                if key.kind == event::KeyEventKind::Press {
                    handle_keys(key, &mut app);
                }
            }
        }

        if last_tick.elapsed() >= tick_rate {
            last_tick = Instant::now();
        }

        if app.should_quit {
            app.save_session();
            return Ok(());
        }
    }
}
