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
                                .push("+10 Bacon Points (Pending Verification)".to_string());
                        }
                    }
                    app.event_feed.push(message.clone());
                    app.status_message = message;
                }
                crate::app::AppEvent::SubmitResult { success, message } => {
                    app.event_feed.push(message.clone());
                    app.audit_logs.push(message.clone());
                    if success {
                        app.status_message =
                            "✓ Bug submitted! Refreshing issues list...".to_string();
                        app.audit_logs
                            .push("+50 Bacon Points (Pending Verification)".to_string());
                    } else {
                        app.status_message = message;
                    }
                    app.save_session();
                }
                crate::app::AppEvent::IssuesRefreshed { issues, total } => {
                    app.issues = issues;
                    app.stats.total_issues = total;
                    app.selected_issue_index = 0;
                    app.status_message = "✓ Issues refreshed with live data.".to_string();
                    app.audit_logs
                        .push("Issues list refreshed after submission.".to_string());
                    app.save_session();
                }
                crate::app::AppEvent::VisionDraftComplete { result } => {
                    app.submit_form.description = result;
                    app.status_message =
                        "Vision AI drafting complete. Review and submit.".to_string();
                    app.audit_logs
                        .push("Vision AI generated issue draft.".to_string());
                    app.save_session();
                }
                crate::app::AppEvent::AiTriageResult { message } => {
                    app.ai_triage_result = Some(message.clone());
                    app.event_feed
                        .push("AI Triage analysis complete.".to_string());
                    app.audit_logs
                        .push("Agent triggered AI Triage analysis.".to_string());
                    app.status_message = "AI Triage analysis complete.".to_string();
                    app.save_session();
                }
                crate::app::AppEvent::ScanComplete { health } => {
                    app.security_health = Some(health);
                    app.event_feed
                        .push("Security Health Scan complete.".to_string());
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
        || app.active_overlay == crate::app::ActiveOverlay::CommandPalette;

    if key.code == KeyCode::Char('q') && !is_text_input {
        if app.active_overlay != crate::app::ActiveOverlay::None {
            app.active_overlay = crate::app::ActiveOverlay::None;
            return;
        }
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
                }

                let api_base = app.api_base.clone();
                let run_mode = app.run_mode.clone();
                let sender = app.event_sender.clone();
                let mcp_client_clone = app.mcp_client.clone();

                app.status_message = "Submitting vulnerability...".to_string();
                tokio::spawn(async move {
                    let is_mcp = run_mode == crate::app::RunMode::Mcp;

                    let (success, message) = if is_mcp && mcp_client_clone.is_some() {
                        let mcp = mcp_client_clone.unwrap();
                        let mut client_guard = mcp.lock().await;
                        let mut payload = serde_json::Map::new();
                        payload.insert("url".to_string(), serde_json::Value::String(url.clone()));
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
                        match crate::api::get_issues(&api_base).await {
                            Ok(fresh_issues) => {
                                let total = fresh_issues.len() as u32;
                                let _ = sender.send(crate::app::AppEvent::IssuesRefreshed {
                                    issues: fresh_issues,
                                    total,
                                });
                            }
                            Err(_) => {} // silently ignore; user still got the success message
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
                KeyCode::Char('s') => {
                    if !app.hunts.is_empty() {
                        app.submit_form.url = "".to_string();
                        app.active_overlay = crate::app::ActiveOverlay::SubmitForm;
                        app.submit_form.active_field = crate::app::FormField::Url;
                        app.status_message = "Opened Submit Form for Hunt Context".to_string();
                    }
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
                    app.selected_issues.clear();

                    tokio::spawn(async move {
                        tokio::time::sleep(std::time::Duration::from_millis(800)).await;
                        for id in &issue_ids {
                            let _ = sender.send(crate::app::AppEvent::TriageConfirmed {
                                issue_id: id.clone(),
                                success: true,
                                message: format!("Bulk action complete for #{}", id),
                                target_status: target.clone(),
                            });
                        }
                        let _ = sender.send(crate::app::AppEvent::SubmitResult {
                            success: true,
                            message: format!(
                                "Successfully bulk triaged {} issues to '{}'.",
                                count, target
                            ),
                        });
                    });
                }
                _ => {}
            }
            return;
        }
        crate::app::ActiveOverlay::CommandPalette => {
            match key.code {
                KeyCode::Esc => {
                    app.active_overlay = crate::app::ActiveOverlay::None;
                    app.command_input.clear();
                }
                KeyCode::Backspace => {
                    app.command_input.pop();
                }
                KeyCode::Char(c) => {
                    app.command_input.push(c);
                }
                KeyCode::Enter => {
                    app.active_overlay = crate::app::ActiveOverlay::None;
                    let cmd = app.command_input.clone();
                    app.command_input.clear();
                    app.status_message = format!("Executed command: {}", cmd);
                    app.audit_logs
                        .push(format!("Command Palette execution: {}", cmd));

                    // Command execution logic
                    if cmd.starts_with("search ") {
                        app.search_query = cmd.replace("search ", "");
                        app.active_tab = Tab::Issues;
                    } else if cmd == "triage issue" {
                        app.active_tab = Tab::Issues;
                        app.trigger_triage();
                    } else if cmd == "add comment" {
                        app.status_message = "Not Implemented: Feature coming soon".to_string();
                    } else if cmd == "open hunt" {
                        app.active_tab = Tab::Hunts;
                    } else if cmd.starts_with("vision ") {
                        let args = cmd.replace("vision ", "");
                        let mut parts = args.split_whitespace();
                        if let Some(path) = parts.next() {
                            let path = path.to_string();
                            let gl_id = parts.next().map(|s| s.to_string());

                            app.status_message = format!("Drafting issue from image {}...", path);
                            app.active_overlay = crate::app::ActiveOverlay::SubmitForm;
                            app.submit_form.url = format!("Image: {}", path);
                            app.submit_form.description =
                                "Analyzing image with Vision AI...".to_string();

                            let mcp_client_clone = app.mcp_client.clone();
                            let sender = app.event_sender.clone();

                            tokio::spawn(async move {
                                if let Some(mcp) = mcp_client_clone {
                                    let mut client_guard = mcp.lock().await;
                                    let mut payload = serde_json::Map::new();
                                    payload.insert(
                                        "image_path".to_string(),
                                        serde_json::Value::String(path),
                                    );
                                    if let Some(gid) = gl_id {
                                        payload.insert(
                                            "gitlab_project_id".to_string(),
                                            serde_json::Value::String(gid),
                                        );
                                    }

                                    match client_guard
                                        .call_tool(
                                            "draft_vision_issue",
                                            serde_json::Value::Object(payload),
                                        )
                                        .await
                                    {
                                        Ok(res) => {
                                            let content_str = if let Some(result) =
                                                res.get("result")
                                            {
                                                result
                                                    .get("content")
                                                    .and_then(|c| c.as_array())
                                                    .and_then(|c| c.first())
                                                    .and_then(|c| c.get("text"))
                                                    .and_then(|t| t.as_str())
                                                    .unwrap_or("Unknown response from MCP")
                                                    .to_string()
                                            } else {
                                                "ERROR: Invalid response structure from MCP server"
                                                    .to_string()
                                            };

                                            let _ = sender.send(
                                                crate::app::AppEvent::VisionDraftComplete {
                                                    result: content_str,
                                                },
                                            );
                                        }
                                        Err(e) => {
                                            let _ = sender.send(
                                                crate::app::AppEvent::VisionDraftComplete {
                                                    result: format!("ERROR: {}", e),
                                                },
                                            );
                                        }
                                    }
                                } else {
                                    let _ =
                                        sender.send(crate::app::AppEvent::VisionDraftComplete {
                                            result: "ERROR: MCP is not connected.".to_string(),
                                        });
                                }
                            });
                        }
                    } else if cmd == "run mcp tool" {
                        app.status_message = "Not Implemented: Feature coming soon".to_string();
                    }
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
            app.active_tab = Tab::Stats;
            app.status_message = "Switched to tab: BLT Stats".to_string();
        }
        KeyCode::Char('4') => {
            app.active_tab = Tab::Logs;
            app.status_message = "Switched to tab: Logs & Events".to_string();
        }
        KeyCode::Char('5') => {
            app.active_tab = Tab::Settings;
            app.status_message = "Switched to tab: Settings".to_string();
        }
        KeyCode::Char('6') => {
            app.active_tab = Tab::Onboarding;
            app.status_message = "Switched to tab: Onboarding".to_string();
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
        KeyCode::Char(':') | KeyCode::Char('p')
            if key.code == KeyCode::Char(':')
                || (key.code == KeyCode::Char('p')
                    && key.modifiers.contains(KeyModifiers::CONTROL)) =>
        {
            app.active_overlay = crate::app::ActiveOverlay::CommandPalette;
        }
        KeyCode::Char(' ') => {
            if app.active_tab == Tab::Issues && !app.issues.is_empty() {
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
            if app.active_tab == Tab::Hunts && !app.hunts.is_empty() {
                app.active_overlay = crate::app::ActiveOverlay::HuntDetail;
            } else if app.active_tab == Tab::Issues && !app.issues.is_empty() {
                app.trigger_triage();
            } else if app.active_tab == Tab::Settings {
                if let Some(health) = &app.security_health {
                    if !health.findings.is_empty() {
                        app.active_overlay = crate::app::ActiveOverlay::SubmitForm;
                        app.submit_form.url = "System Scan Findings".to_string();
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
            app.active_overlay = crate::app::ActiveOverlay::SubmitForm;
        }
        KeyCode::Char('A') => app.toggle_agent_status(),
        KeyCode::Char('P') => app.toggle_prompt_preview(),
        KeyCode::Char('a') => {
            if app.active_tab == Tab::Issues && !app.issues.is_empty() {
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
                                let text = resp
                                    .get("result")
                                    .and_then(|r| r.get("content"))
                                    .and_then(|c| c.as_array())
                                    .and_then(|arr| arr.first())
                                    .and_then(|first| first.get("text"))
                                    .and_then(|t| t.as_str())
                                    .unwrap_or("No analysis returned from MCP.");

                                let message = format!(
                                    "AI Triage Complete for Issue #{}:\n\n{}",
                                    issue_id, text
                                );
                                let _ =
                                    sender.send(crate::app::AppEvent::AiTriageResult { message });
                            }
                            Err(e) => {
                                let message =
                                    format!("AI Triage Failed for Issue #{}: {}", issue_id, e);
                                let _ =
                                    sender.send(crate::app::AppEvent::AiTriageResult { message });
                            }
                        }
                    });
                } else {
                    let message =
                        "Error: AI Triage requires an active Live MCP connection.".to_string();
                    let _ = sender.send(crate::app::AppEvent::AiTriageResult { message });
                }
            }
        }

        KeyCode::Esc => app.close_popups(),
        _ => {}
    }
}
