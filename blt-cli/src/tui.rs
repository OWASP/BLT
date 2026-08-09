//! Main Terminal Loop and Input Event Handler.
//!
//! This module runs the main event loop for the Ratatui TUI client. It polls input keys
//! and processes events from background tasks.
//!
//! Key Functions:
//! - `run_app(terminal, app) -> io::Result<()>`: Main application loop. It draws views, polls for
//!   keystroke events at 100ms intervals, and processes incoming channel notifications (e.g. triage results,
//!   draft completions, scan status).
//! - `handle_keys(key, app)`: Handles global commands and navigations:
//!   - Tab navigation (Tab / BackTab / keys 1-6).
//!   - List scrolling (Down / Up / j / k).
//!   - Modals toggling (Help / Search / Command Palette / Easter Egg).
//!   - Multi-field input focus switching and backspace deletions in the submit form.
//!
//! Design details:
//! - Implements Konami Code check sequence. Triggers an easter egg overlay if keys are entered correctly.
//! - Integrates Command Palette interpreter (`search`, `triage issue`, `vision <path>`).
//! - Spawns async tokio tasks to perform write actions (e.g. submit issue, bulk triage) to avoid freezing the UI.

use std::io;

use std::time::{Duration, Instant};

use crossterm::event::{self, Event, KeyCode, KeyEvent, KeyModifiers};
use ratatui::{backend::Backend, Terminal};

use crate::app::{App, Tab};
use crate::ui;

pub fn run_app<B: Backend>(terminal: &mut Terminal<B>, mut app: App) -> io::Result<()>
where
    std::io::Error: From<<B as Backend>::Error>,
{
    let tick_rate = Duration::from_millis(100);
    let mut last_tick = Instant::now();

    loop {
        terminal.draw(|f| ui::draw(f, &mut app))?;

        let timeout = tick_rate
            .checked_sub(last_tick.elapsed())
            .unwrap_or_else(|| Duration::from_secs(0));

        // Process any messages from background tokio tasks
        while let Ok(event) = app.event_receiver.try_recv() {
            match event {
                crate::app::AppEvent::TriageConfirmed {
                    issue_id,
                    success,
                    message,
                    target_status,
                } => {
                    if success {
                        if let Some(issue) = app.issues.iter_mut().find(|i| i.id == issue_id) {
                            issue.status = target_status.clone();
                            let comment = format!("{}: Manually confirmed & updated triage status for #{} to {} via TUI CLI.", app.auth_user, issue_id, target_status);
                            issue.comments.push(comment.clone());
                            app.audit_logs.push(comment);
                            app.audit_logs
                                .push("+10 Points (Pending Verification)".to_string());
                        }
                        app.selected_issues.remove(&issue_id);
                    }
                    app.event_feed.push(message.clone());
                    app.status_message = message;
                }
                crate::app::AppEvent::SubmitResult { success, message } => {
                    app.event_feed.push(message.clone());
                    app.audit_logs.push(message.clone());
                    if success {
                        app.status_message = format!("SUCCESS: Operation completed! - {}", message);
                        app.submit_form = crate::app::VulnerabilityForm::default();
                    } else {
                        app.status_message = format!("ERROR: {}", message);
                    }
                    app.save_session();
                }
                crate::app::AppEvent::IssuesRefreshed { issues, total } => {
                    app.issues = issues;
                    // Clamp to prevent stale index from causing out-of-bounds panics
                    app.selected_issue_index = app
                        .selected_issue_index
                        .min(app.issues.len().saturating_sub(1));
                    app.event_feed
                        .push(format!("Refreshed issues. Total: {}", total));
                    app.audit_logs
                        .push("Issues list refreshed after submission.".to_string());
                    app.save_session();
                }
                crate::app::AppEvent::VisionDraftComplete { result, success } => {
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
                            } else {
                                if !line.trim().is_empty() {
                                    description.push('\n');
                                    description.push_str(line);
                                }
                            }
                        }

                        if !title.is_empty() {
                            app.submit_form.title = title;
                        }
                        app.submit_form.description = description.trim().to_string();
                        app.status_message =
                            "Vision AI drafting complete. Review and submit.".to_string();
                        app.audit_logs
                            .push("Vision AI generated issue draft.".to_string());
                    } else {
                        app.status_message = format!("Vision AI failed: {}", result);
                        app.audit_logs.push(format!("Vision AI failed: {}", result));
                    }
                    app.save_session();
                }
                crate::app::AppEvent::AiTriageResult { message, success } => {
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
                crate::app::AppEvent::ScanComplete { health } => {
                    app.security_health = Some(health);
                    app.event_feed
                        .push("Security Health Scan complete.".to_string());
                    app.save_session();
                }
                crate::app::AppEvent::ClipboardExtracted { result } => {
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
            }
        }

        if event::poll(timeout)? {
            if let Event::Key(key) = event::read()? {
                // Handle key inputs
                handle_keys(key, &mut app);
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

fn handle_vision_draft(app: &mut App, context: Option<String>) {
    app.active_overlay = crate::app::ActiveOverlay::None;
    let path = app.vision_image_path.clone();

    app.submit_form = crate::app::VulnerabilityForm::default();
    app.active_overlay = crate::app::ActiveOverlay::SubmitForm;
    app.submit_form.screenshot_path = path.clone();
    app.submit_form.url = app.api_base.clone();
    app.submit_form.description = "Analyzing image with Vision AI...".to_string();

    let mcp_client_clone = app.mcp_client.clone();
    let sender = app.event_sender.clone();

    tokio::spawn(async move {
        if let Some(mcp) = mcp_client_clone {
            let mut client_guard = mcp.lock().await;
            let mut payload = serde_json::Map::new();
            payload.insert("image_path".to_string(), serde_json::Value::String(path));
            if let Some(ctx) = context {
                if !ctx.is_empty() {
                    payload.insert("context".to_string(), serde_json::Value::String(ctx));
                }
            }

            match client_guard
                .call_tool("draft_vision_issue", serde_json::Value::Object(payload))
                .await
            {
                Ok(res) => {
                    let (success, content_str) = if let Some(result) = res.get("result") {
                        let is_err = result
                            .get("isError")
                            .and_then(|e| e.as_bool())
                            .unwrap_or(false);
                        let text = result
                            .get("content")
                            .and_then(|c| c.as_array())
                            .and_then(|c| c.first())
                            .and_then(|c| c.get("text"))
                            .and_then(|t| t.as_str())
                            .unwrap_or("No response from Vision AI")
                            .to_string();
                        (!is_err, text)
                    } else {
                        (false, "ERROR: Invalid response structure".to_string())
                    };
                    let _ = sender.send(crate::app::AppEvent::VisionDraftComplete {
                        result: content_str,
                        success,
                    });
                }
                Err(e) => {
                    let _ = sender.send(crate::app::AppEvent::VisionDraftComplete {
                        result: format!("ERROR: {}", e),
                        success: false,
                    });
                }
            }
        }
    });
}

fn handle_keys(key: KeyEvent, app: &mut App) {
    // Check for global quit key
    if key.code == KeyCode::Char('q') && app.active_overlay == crate::app::ActiveOverlay::None {
        app.should_quit = true;
        return;
    }
    if key.code == KeyCode::Char('c') && key.modifiers.contains(KeyModifiers::CONTROL) {
        app.should_quit = true;
        return;
    }

    let is_text_input = app.active_overlay == crate::app::ActiveOverlay::SubmitForm
        || app.active_overlay == crate::app::ActiveOverlay::SearchInput
        || app.active_overlay == crate::app::ActiveOverlay::VisionContext;

    if key.code == KeyCode::Char('q')
        && !is_text_input
        && app.active_overlay != crate::app::ActiveOverlay::None
    {
        app.active_overlay = crate::app::ActiveOverlay::None;
        return;
    }

    // Konami code check
    let konami_seq = [
        KeyCode::Up,
        KeyCode::Up,
        KeyCode::Down,
        KeyCode::Down,
        KeyCode::Left,
        KeyCode::Right,
        KeyCode::Left,
        KeyCode::Right,
        KeyCode::Char('b'),
        KeyCode::Char('a'),
    ];

    if key.code == konami_seq[app.konami_index]
        || (key.code == KeyCode::Char('B') && konami_seq[app.konami_index] == KeyCode::Char('b'))
        || (key.code == KeyCode::Char('A') && konami_seq[app.konami_index] == KeyCode::Char('a'))
    {
        app.konami_index += 1;
        if app.konami_index == konami_seq.len() {
            app.active_overlay = crate::app::ActiveOverlay::EasterEgg;
            app.konami_index = 0;
            return;
        }
    } else {
        app.konami_index = 0;
    }

    // Modal check redirects
    match app.active_overlay {
        crate::app::ActiveOverlay::Help => {
            if key.code == KeyCode::Esc
                || key.code == KeyCode::Char(' ')
                || key.code == KeyCode::Char('h')
                || key.code == KeyCode::Char('?')
            {
                app.active_overlay = crate::app::ActiveOverlay::None;
            }
            return;
        }
        crate::app::ActiveOverlay::Triage => {
            match key.code {
                KeyCode::Enter => {
                    app.confirm_triage();
                }
                KeyCode::Esc => {
                    app.active_overlay = crate::app::ActiveOverlay::None;
                    app.status_message = "Triage write operation cancelled.".to_string();
                }
                _ => {}
            }
            return;
        }
        crate::app::ActiveOverlay::VisionContext => {
            match key.code {
                KeyCode::Esc => {
                    handle_vision_draft(app, None);
                }
                KeyCode::Backspace => {
                    app.vision_context_input.pop();
                }
                KeyCode::Char(c) => {
                    app.vision_context_input.push(c);
                }
                KeyCode::Enter => {
                    let context = app.vision_context_input.trim().to_string();
                    handle_vision_draft(app, Some(context));
                }
                _ => {}
            }
            return;
        }
        crate::app::ActiveOverlay::SubmitForm => {
            if key.code == KeyCode::Char('s') && key.modifiers.contains(KeyModifiers::CONTROL) {
                app.active_overlay = crate::app::ActiveOverlay::None;
                let title = app.submit_form.title.clone();
                let url = app.submit_form.url.clone();
                let severity = app.submit_form.severity.clone();
                let bug_type = app.submit_form.bug_type.clone();
                let mut desc = app.submit_form.description.clone();
                let steps = app.submit_form.steps_to_reproduce.clone();
                let screenshot = app.submit_form.screenshot_path.clone();

                if app.run_mode == crate::app::RunMode::Mcp {
                    desc = format!("*Submitted by AI Agent via BLT-MCP*\n\n{}", desc);
                    if !screenshot.is_empty() {
                        desc = format!("{}\n\n[Note: Screenshot '{}' was not included \u{2014} MCP submissions do not support screenshot uploads.]", desc, screenshot);
                    }
                }

                let api_base = app.api_base.clone();
                let run_mode = app.run_mode.clone();
                let sender = app.event_sender.clone();
                let mcp_client_clone = app.mcp_client.clone();

                app.status_message = "Submitting vulnerability...".to_string();
                tokio::spawn(async move {
                    let is_mcp = run_mode == crate::app::RunMode::Mcp;

                    let (success, message) = if is_mcp {
                        if mcp_client_clone.is_none() {
                            (
                                false,
                                "ERROR: MCP connection is unavailable. Submission failed."
                                    .to_string(),
                            )
                        } else {
                            let mcp = mcp_client_clone.clone().unwrap();
                            let mut client_guard = mcp.lock().await;
                            let mut payload = serde_json::Map::new();
                            payload
                                .insert("url".to_string(), serde_json::Value::String(url.clone()));
                            payload.insert(
                                "title".to_string(),
                                serde_json::Value::String(title.clone()),
                            );
                            payload.insert(
                                "description".to_string(),
                                serde_json::Value::String(desc.clone()),
                            );
                            payload.insert(
                                "severity".to_string(),
                                serde_json::Value::String(severity.clone()),
                            );
                            payload.insert(
                                "bug_type".to_string(),
                                serde_json::Value::String(bug_type.clone()),
                            );
                            payload.insert(
                                "steps_to_reproduce".to_string(),
                                serde_json::Value::String(steps.clone()),
                            );
                            payload.insert("confirmed".to_string(), serde_json::Value::Bool(true));
                            let args = serde_json::Value::Object(payload);

                            match client_guard.call_tool("submit_issue", args).await {
                                Ok(res) => {
                                    if let Some(result) = res.get("result") {
                                        let is_error = result
                                            .get("isError")
                                            .and_then(|e| e.as_bool())
                                            .unwrap_or(false);
                                        let content_str = result
                                            .get("content")
                                            .and_then(|c| c.as_array())
                                            .and_then(|c| c.first())
                                            .and_then(|c| c.get("text"))
                                            .and_then(|t| t.as_str())
                                            .unwrap_or("Unknown response from MCP");
                                        if is_error {
                                            (
                                                false,
                                                format!(
                                                    "ERROR: MCP tool execution failed: {}",
                                                    content_str
                                                ),
                                            )
                                        } else {
                                            (true, content_str.to_string())
                                        }
                                    } else {
                                        (
                                            false,
                                            "ERROR: Invalid response structure from MCP server"
                                                .to_string(),
                                        )
                                    }
                                }
                                Err(e) => (
                                    false,
                                    format!("ERROR: Failed to communicate with MCP: {}", e),
                                ),
                            }
                        }
                    } else {
                        match crate::api::submit_issue(
                            &api_base,
                            &url,
                            &title,
                            &severity,
                            &bug_type,
                            &desc,
                            &steps,
                            &screenshot,
                        )
                        .await
                        {
                            Ok(_) => (true, "SUCCESS: Vulnerability report submitted!".to_string()),
                            Err(e) => (false, format!("ERROR: Failed to submit: {}", e)),
                        }
                    };

                    let _ = sender.send(crate::app::AppEvent::SubmitResult { success, message });

                    // Background refresh: wait a moment then re-fetch the live issues list
                    if success {
                        tokio::time::sleep(tokio::time::Duration::from_millis(1500)).await;
                        if is_mcp && mcp_client_clone.is_some() {
                            let mcp = mcp_client_clone.unwrap();
                            let mut client_guard = mcp.lock().await;
                            if let Ok(resp) = client_guard.read_resource("blt://v2/bugs").await {
                                if let Some(contents) = resp
                                    .get("result")
                                    .and_then(|r| r.get("contents"))
                                    .and_then(|c| c.as_array())
                                    .and_then(|c| c.first())
                                    .and_then(|c| c.get("text"))
                                    .and_then(|t| t.as_str())
                                {
                                    if let Ok(root) =
                                        serde_json::from_str::<serde_json::Value>(contents)
                                    {
                                        if let Ok(fresh_issues) =
                                            crate::api::parse_issues_from_json(&root)
                                        {
                                            let total = fresh_issues.len() as u32;
                                            let _ = sender.send(
                                                crate::app::AppEvent::IssuesRefreshed {
                                                    issues: fresh_issues,
                                                    total,
                                                },
                                            );
                                        }
                                    }
                                }
                            }
                        } else {
                            if let Ok(fresh_issues) = crate::api::get_issues(&api_base).await {
                                let total = fresh_issues.len() as u32;
                                let _ = sender.send(crate::app::AppEvent::IssuesRefreshed {
                                    issues: fresh_issues,
                                    total,
                                });
                            }
                        }
                    }
                });
                return;
            }

            if key.modifiers.contains(KeyModifiers::CONTROL) {
                return; // Prevent typing control characters into fields
            }

            match key.code {
                KeyCode::Esc => {
                    app.active_overlay = crate::app::ActiveOverlay::None;
                    app.status_message = "Submit vulnerability cancelled.".to_string();
                }
                KeyCode::Tab => {
                    app.submit_form.active_field = match app.submit_form.active_field {
                        crate::app::FormField::Title => crate::app::FormField::Url,
                        crate::app::FormField::Url => crate::app::FormField::Severity,
                        crate::app::FormField::Severity => crate::app::FormField::BugType,
                        crate::app::FormField::BugType => crate::app::FormField::Description,
                        crate::app::FormField::Description => {
                            crate::app::FormField::StepsToReproduce
                        }
                        crate::app::FormField::StepsToReproduce => {
                            crate::app::FormField::Screenshot
                        }
                        crate::app::FormField::Screenshot => crate::app::FormField::Title,
                    };
                }
                KeyCode::Enter => {
                    let field = match app.submit_form.active_field {
                        crate::app::FormField::Title => &mut app.submit_form.title,
                        crate::app::FormField::Url => &mut app.submit_form.url,
                        crate::app::FormField::Severity => &mut app.submit_form.severity,
                        crate::app::FormField::BugType => &mut app.submit_form.bug_type,
                        crate::app::FormField::Description => &mut app.submit_form.description,
                        crate::app::FormField::StepsToReproduce => {
                            &mut app.submit_form.steps_to_reproduce
                        }
                        crate::app::FormField::Screenshot => &mut app.submit_form.screenshot_path,
                    };
                    if app.submit_form.active_field == crate::app::FormField::Description
                        || app.submit_form.active_field == crate::app::FormField::StepsToReproduce
                    {
                        field.push('\n');
                    } else {
                        app.submit_form.active_field = match app.submit_form.active_field {
                            crate::app::FormField::Title => crate::app::FormField::Url,
                            crate::app::FormField::Url => crate::app::FormField::Severity,
                            crate::app::FormField::Severity => crate::app::FormField::BugType,
                            crate::app::FormField::BugType => crate::app::FormField::Description,
                            crate::app::FormField::Description => {
                                crate::app::FormField::StepsToReproduce
                            }
                            crate::app::FormField::StepsToReproduce => {
                                crate::app::FormField::Screenshot
                            }
                            crate::app::FormField::Screenshot => crate::app::FormField::Title,
                        };
                    }
                }
                KeyCode::Backspace => {
                    let field = match app.submit_form.active_field {
                        crate::app::FormField::Title => &mut app.submit_form.title,
                        crate::app::FormField::Url => &mut app.submit_form.url,
                        crate::app::FormField::Severity => &mut app.submit_form.severity,
                        crate::app::FormField::BugType => &mut app.submit_form.bug_type,
                        crate::app::FormField::Description => &mut app.submit_form.description,
                        crate::app::FormField::StepsToReproduce => {
                            &mut app.submit_form.steps_to_reproduce
                        }
                        crate::app::FormField::Screenshot => &mut app.submit_form.screenshot_path,
                    };
                    field.pop();
                }
                KeyCode::Char(c) => {
                    let field = match app.submit_form.active_field {
                        crate::app::FormField::Title => &mut app.submit_form.title,
                        crate::app::FormField::Url => &mut app.submit_form.url,
                        crate::app::FormField::Severity => &mut app.submit_form.severity,
                        crate::app::FormField::BugType => &mut app.submit_form.bug_type,
                        crate::app::FormField::Description => &mut app.submit_form.description,
                        crate::app::FormField::StepsToReproduce => {
                            &mut app.submit_form.steps_to_reproduce
                        }
                        crate::app::FormField::Screenshot => &mut app.submit_form.screenshot_path,
                    };
                    field.push(c);
                }
                _ => {}
            }
            return;
        }
        crate::app::ActiveOverlay::HuntDetail => {
            match key.code {
                KeyCode::Esc => {
                    app.active_overlay = crate::app::ActiveOverlay::None;
                }
                KeyCode::Char('s') if !app.hunts.is_empty() => {
                    app.submit_form = crate::app::VulnerabilityForm::default();
                    app.submit_form.url = "".to_string();
                    app.active_overlay = crate::app::ActiveOverlay::SubmitForm;
                    app.submit_form.active_field = crate::app::FormField::Url;
                    app.status_message = "Opened Submit Form for Hunt Context".to_string();
                }
                _ => {}
            }
            return;
        }
        crate::app::ActiveOverlay::AiTriage => {
            if key.code == KeyCode::Esc {
                app.active_overlay = crate::app::ActiveOverlay::None;
            }
            return;
        }
        crate::app::ActiveOverlay::SearchInput => {
            match key.code {
                KeyCode::Esc => {
                    app.active_overlay = crate::app::ActiveOverlay::None;
                    app.search_query.clear(); // Clear on escape
                }
                KeyCode::Enter => {
                    app.active_overlay = crate::app::ActiveOverlay::None;
                    app.status_message = format!("Applied search filter: '{}'", app.search_query);
                    let visible_issues = app.get_visible_issue_indices();
                    if !visible_issues.is_empty() {
                        app.selected_issue_index = visible_issues[0];
                    }
                    let visible_hunts = app.get_visible_hunt_indices();
                    if !visible_hunts.is_empty() {
                        app.selected_hunt_index = visible_hunts[0];
                    }
                }
                KeyCode::Backspace => {
                    app.search_query.pop();
                }
                KeyCode::Char(c) => {
                    app.search_query.push(c);
                }
                _ => {}
            }
            return;
        }
        crate::app::ActiveOverlay::BulkTriageConfirm => {
            match key.code {
                KeyCode::Esc => {
                    app.active_overlay = crate::app::ActiveOverlay::None;
                    app.status_message = "Bulk triage cancelled.".to_string();
                }
                KeyCode::Char('1') => {
                    app.triage_target_status = "Open".to_string();
                }
                KeyCode::Char('2') => {
                    app.triage_target_status = "In Review".to_string();
                }
                KeyCode::Char('3') => {
                    app.triage_target_status = "Resolved".to_string();
                }
                KeyCode::Enter => {
                    app.active_overlay = crate::app::ActiveOverlay::None;
                    let target = app.triage_target_status.clone();
                    let count = app.selected_issues.len();
                    app.status_message =
                        format!("Bulk triaging {} issues to '{}'...", count, target);
                    let sender = app.event_sender.clone();
                    let issue_ids: Vec<String> = app.selected_issues.iter().cloned().collect();
                    let mcp_client_clone = app.mcp_client.clone();
                    let api_base = app.api_base.clone();

                    tokio::spawn(async move {
                        let mut all_succeeded = true;
                        let mut failed_count = 0;
                        let mut first_error = String::new();

                        for id in &issue_ids {
                            let res = if let Some(ref client_mutex) = mcp_client_clone {
                                let mut client = client_mutex.lock().await;
                                let args = serde_json::json!({
                                    "id": id,
                                    "status": target,
                                    "confirmed": true
                                });
                                client.call_tool("update_bug", args).await.map(|_| ())
                            } else {
                                crate::api::submit_issue_triage(&api_base, id, &target).await
                            };

                            let (success, message) = match res {
                                Ok(_) => (
                                    true,
                                    format!(
                                        "Bulk triage: successfully updated status for #{} to {}",
                                        id, target
                                    ),
                                ),
                                Err(e) => {
                                    all_succeeded = false;
                                    failed_count += 1;
                                    if first_error.is_empty() {
                                        first_error = e.to_string();
                                    }
                                    (
                                        false,
                                        format!(
                                            "Bulk triage: failed to update status for #{}: {}",
                                            id, e
                                        ),
                                    )
                                }
                            };

                            let _ = sender.send(crate::app::AppEvent::TriageConfirmed {
                                issue_id: id.clone(),
                                success,
                                message,
                                target_status: target.clone(),
                            });
                        }

                        if all_succeeded {
                            let _ = sender.send(crate::app::AppEvent::SubmitResult {
                                success: true,
                                message: format!(
                                    "Successfully bulk triaged {} issues to '{}'.",
                                    count, target
                                ),
                            });
                        } else {
                            let _ = sender.send(crate::app::AppEvent::SubmitResult {
                                success: false,
                                message: format!(
                                    "Bulk triage completed with errors: {} failed. First error: {}",
                                    failed_count, first_error
                                ),
                            });
                        }
                    });
                }
                _ => {}
            }
            return;
        }
        crate::app::ActiveOverlay::AgentStatus => {
            if key.code == KeyCode::Esc || key.code == KeyCode::Char('A') {
                app.active_overlay = crate::app::ActiveOverlay::None;
            }
            return;
        }
        crate::app::ActiveOverlay::PromptPreview => {
            if key.code == KeyCode::Esc || key.code == KeyCode::Char('P') {
                app.active_overlay = crate::app::ActiveOverlay::None;
            }
            return;
        }
        crate::app::ActiveOverlay::EasterEgg => {
            if key.code == KeyCode::Esc
                || key.code == KeyCode::Enter
                || key.code == KeyCode::Char(' ')
            {
                app.active_overlay = crate::app::ActiveOverlay::None;
            }
            return;
        }
        _ => {}
    }

    // Navigation and normal operations
    match key.code {
        KeyCode::Tab => app.next_tab(),
        KeyCode::BackTab => app.prev_tab(),

        // Tab numeric shortcuts
        KeyCode::Char('1') => {
            app.active_tab = Tab::Issues;
            app.status_message = "Switched to tab: Issues".to_string();
        }
        KeyCode::Char('2') => {
            app.active_tab = Tab::Hunts;
            app.status_message = "Switched to tab: Active Hunts".to_string();
        }
        KeyCode::Char('3') => {
            app.active_tab = Tab::Onboarding;
            app.status_message = "Switched to tab: Onboarding".to_string();
        }
        KeyCode::Char('4') => {
            app.active_tab = Tab::Stats;
            app.status_message = "Switched to tab: BLT Stats".to_string();
        }
        KeyCode::Char('5') => {
            app.active_tab = Tab::Logs;
            app.status_message = "Switched to tab: Logs & Events".to_string();
        }
        KeyCode::Char('6') => {
            app.active_tab = Tab::Settings;
            app.status_message = "Switched to tab: Settings".to_string();
        }

        // List Scrolling
        KeyCode::Down | KeyCode::Char('j') => app.scroll_down(),
        KeyCode::Up | KeyCode::Char('k') => app.scroll_up(),

        // Dialog overlays
        KeyCode::Char('e') => {
            if app.active_tab == Tab::Logs {
                app.export_logs();
                app.status_message = "Logs exported to blt_export.log".to_string();
            }
        }
        KeyCode::Char('/') => {
            app.active_overlay = crate::app::ActiveOverlay::SearchInput;
        }
        KeyCode::Char('p') | KeyCode::Char('v')
            if key.code == KeyCode::Char('p')
                || (key.code == KeyCode::Char('v')
                    && key.modifiers.contains(KeyModifiers::CONTROL)) =>
        {
            app.status_message = "Reading image or path from clipboard...".to_string();
            let sender = app.event_sender.clone();

            #[cfg(windows)]
            {
                tokio::spawn(async move {
                    let output = tokio::task::spawn_blocking(|| {
                        std::process::Command::new("powershell.exe")
                            .args([
                                "-NoProfile",
                                "-Command",
                                "Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing; if ([System.Windows.Forms.Clipboard]::ContainsImage()) { $img = [System.Windows.Forms.Clipboard]::GetImage(); $temp = [System.IO.Path]::GetTempFileName() + '.png'; $img.Save($temp, [System.Drawing.Imaging.ImageFormat]::Png); Write-Output \"SUCCESS:$temp\"; } else { if ([System.Windows.Forms.Clipboard]::ContainsText()) { $txt = [System.Windows.Forms.Clipboard]::GetText().Trim().Trim('\"'); if (Test-Path $txt -PathType Leaf) { Write-Output \"SUCCESS:$txt\"; } else { Write-Output 'NO_IMAGE'; } } else { Write-Output 'NO_IMAGE'; } }"
                            ])
                            .output()
                    })
                    .await;

                    let result = match output {
                        Ok(Ok(out)) => {
                            let stdout = String::from_utf8_lossy(&out.stdout).trim().to_string();
                            if stdout.starts_with("SUCCESS:") {
                                let win_path = stdout["SUCCESS:".len()..].trim().to_string();
                                let path_str = if cfg!(target_os = "linux") {
                                    if win_path.as_bytes().get(1..3) == Some(b":\\") {
                                        let drive = win_path[0..1].to_lowercase();
                                        let rest = win_path[3..].replace('\\', "/");
                                        format!("/mnt/{}/{}", drive, rest)
                                    } else {
                                        win_path
                                    }
                                } else {
                                    win_path
                                };
                                Ok(path_str)
                            } else if stdout.contains("NO_IMAGE") {
                                Err("Clipboard does not contain an image or valid image path."
                                    .to_string())
                            } else {
                                Err(format!("PowerShell error: {}", stdout))
                            }
                        }
                        _ => Err("Failed to execute PowerShell command".to_string()),
                    };
                    let _ = sender.send(crate::app::AppEvent::ClipboardExtracted { result });
                });
            }

            #[cfg(not(windows))]
            {
                tokio::spawn(async move {
                    let result = tokio::task::spawn_blocking(move || {
                        match arboard::Clipboard::new() {
                            Ok(mut clipboard) => {
                                match clipboard.get_image() {
                                    Ok(image) => {
                                        let home = dirs::home_dir().unwrap_or_default();
                                        let img_dir = home.join(".blt-mcp").join("images");
                                        let _ = std::fs::create_dir_all(&img_dir);
                                        let temp_path = img_dir.join("temp_clipboard.png");

                                        let mut png_bytes = Vec::new();
                                        let mut encoder = png::Encoder::new(&mut png_bytes, image.width as u32, image.height as u32);
                                        encoder.set_color(png::ColorType::Rgba);
                                        encoder.set_depth(png::BitDepth::Eight);

                                        let mut write_success = false;
                                        if let Ok(mut writer) = encoder.write_header() {
                                            if writer.write_image_data(&image.bytes).is_ok() {
                                                write_success = true;
                                            }
                                        }

                                        if write_success && std::fs::write(&temp_path, &png_bytes).is_ok() {
                                            Ok(temp_path.to_string_lossy().to_string())
                                        } else {
                                            Err("Error: Failed to save clipboard image.".to_string())
                                        }
                                    }
                                    Err(_) => {
                                        // Try reading text as path from clipboard
                                        if let Ok(text) = clipboard.get_text() {
                                            let trimmed = text.trim().replace('"', "");
                                            let path_str = if cfg!(target_os = "linux") {
                                                 if trimmed.as_bytes().get(1..3) == Some(b":\\") {
                                                     let drive = trimmed[0..1].to_lowercase();
                                                     let rest = trimmed[3..].replace('\\', "/");
                                                     format!("/mnt/{}/{}", drive, rest)
                                                 } else {
                                                     trimmed
                                                 }
                                            } else {
                                                trimmed
                                            };
                                            let p = std::path::Path::new(&path_str);
                                            if p.exists() && p.is_file() {
                                                Ok(path_str)
                                            } else {
                                                Err("Clipboard does not contain an image or valid image path.".to_string())
                                            }
                                        } else {
                                            Err("Clipboard does not contain an image.".to_string())
                                        }
                                    }
                                }
                            }
                            Err(e) => {
                                Err(format!("Error: Clipboard access failed: {}", e))
                            }
                        }
                    })
                    .await;

                    let final_res = match result {
                        Ok(res) => res,
                        Err(_) => Err("Clipboard extraction task panicked".to_string()),
                    };
                    let _ =
                        sender.send(crate::app::AppEvent::ClipboardExtracted { result: final_res });
                });
            }
        }
        KeyCode::Char(' ') => {
            if app.active_tab == Tab::Issues
                && !app.issues.is_empty()
                && app
                    .get_visible_issue_indices()
                    .contains(&app.selected_issue_index)
            {
                let id = app.issues[app.selected_issue_index].id.clone();
                if app.selected_issues.contains(&id) {
                    app.selected_issues.remove(&id);
                } else {
                    app.selected_issues.insert(id);
                }
            }
        }
        KeyCode::Char('h') | KeyCode::Char('?') => app.toggle_help(),
        KeyCode::Char('t') => {
            if !app.selected_issues.is_empty() {
                app.active_overlay = crate::app::ActiveOverlay::BulkTriageConfirm;
            } else {
                app.trigger_triage();
            }
        }
        KeyCode::Enter => {
            if app.active_tab == Tab::Hunts
                && !app.hunts.is_empty()
                && app
                    .get_visible_hunt_indices()
                    .contains(&app.selected_hunt_index)
            {
                app.active_overlay = crate::app::ActiveOverlay::HuntDetail;
            } else if app.active_tab == Tab::Issues
                && !app.issues.is_empty()
                && app
                    .get_visible_issue_indices()
                    .contains(&app.selected_issue_index)
            {
                app.trigger_triage();
            } else if app.active_tab == Tab::Settings {
                if let Some(health) = &app.security_health {
                    if !health.findings.is_empty() {
                        app.submit_form = crate::app::VulnerabilityForm::default();
                        app.active_overlay = crate::app::ActiveOverlay::SubmitForm;
                        app.submit_form.url = "".to_string();
                        app.submit_form.severity = "High".to_string();
                        let mut desc = String::new();
                        desc.push_str("Found the following security issues:\n");
                        for finding in &health.findings {
                            desc.push_str(&format!("- {}\n", finding));
                        }
                        app.submit_form.description = desc;
                    }
                }
            }
        }
        KeyCode::Char('s') => {
            app.submit_form = crate::app::VulnerabilityForm::default();
            app.active_overlay = crate::app::ActiveOverlay::SubmitForm;
        }
        KeyCode::Char('A') => app.toggle_agent_status(),
        KeyCode::Char('P') => app.toggle_prompt_preview(),
        KeyCode::Char('a') => {
            if app.active_tab == Tab::Issues
                && !app.issues.is_empty()
                && app
                    .get_visible_issue_indices()
                    .contains(&app.selected_issue_index)
            {
                app.active_overlay = crate::app::ActiveOverlay::AiTriage;
                app.ai_triage_result =
                    Some("Analyzing vulnerability using MCP AI tool...".to_string());

                let issue = &app.issues[app.selected_issue_index];
                let issue_id = issue.id.clone();
                let issue_title = issue.title.clone();
                let issue_desc = issue.description.clone();
                let sender = app.event_sender.clone();

                if let Some(mcp) = app.mcp_client.clone() {
                    tokio::spawn(async move {
                        let prompt = format!(
                            "Please analyze Issue #{}: {} - {}",
                            issue_id, issue_title, issue_desc
                        );
                        let args = serde_json::json!({
                            "prompt": prompt
                        });

                        let mut client = mcp.lock().await;
                        match client.call_tool("triage_vulnerability", args).await {
                            Ok(resp) => {
                                // Extract the string text from the MCP JSON-RPC response
                                let is_err = resp
                                    .get("result")
                                    .and_then(|r| r.get("isError"))
                                    .and_then(|ie| ie.as_bool())
                                    .unwrap_or(false);

                                let text = resp
                                    .get("result")
                                    .and_then(|r| r.get("content"))
                                    .and_then(|c| c.as_array())
                                    .and_then(|arr| arr.first())
                                    .and_then(|first| first.get("text"))
                                    .and_then(|t| t.as_str())
                                    .unwrap_or("No analysis returned from MCP.");

                                let (success, message) = if is_err {
                                    (
                                        false,
                                        format!(
                                            "AI Triage Failed for Issue #{}: {}",
                                            issue_id, text
                                        ),
                                    )
                                } else {
                                    (
                                        true,
                                        format!(
                                            "AI Triage Complete for Issue #{}:\n\n{}",
                                            issue_id, text
                                        ),
                                    )
                                };
                                let _ = sender.send(crate::app::AppEvent::AiTriageResult {
                                    message,
                                    success,
                                });
                            }
                            Err(e) => {
                                let message =
                                    format!("AI Triage Failed for Issue #{}: {}", issue_id, e);
                                let _ = sender.send(crate::app::AppEvent::AiTriageResult {
                                    message,
                                    success: false,
                                });
                            }
                        }
                    });
                } else {
                    let message =
                        "Error: AI Triage requires an active Live MCP connection.".to_string();
                    let _ = sender.send(crate::app::AppEvent::AiTriageResult {
                        message,
                        success: false,
                    });
                }
            }
        }

        KeyCode::Esc => app.close_popups(),
        _ => {}
    }
}
