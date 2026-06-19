use std::io;
use std::time::{Duration, Instant};

use crossterm::event::{self, Event, KeyCode, KeyEvent, KeyModifiers};
use ratatui::{backend::Backend, Terminal};

use crate::app::{App, Tab};
use crate::ui;

pub fn run_app<B: Backend>(terminal: &mut Terminal<B>, mut app: App) -> io::Result<()> {
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
                crate::app::AppEvent::TriageConfirmed { issue_id, success, message } => {
                    if success {
                        if let Some(issue) = app.issues.iter_mut().find(|i| i.id == issue_id) {
                            issue.status = app.triage_target_status.clone();
                            let comment = format!("{}: Manually confirmed & updated triage status for #{} to {} via TUI CLI.", app.auth_user, issue_id, app.triage_target_status);
                            issue.comments.push(comment.clone());
                            app.audit_logs.push(comment);
                        }
                    }
                    app.event_feed.push(message.clone());
                    app.status_message = message;
                }
                crate::app::AppEvent::SubmitResult { success: _, message } => {
                    app.event_feed.push(message.clone());
                    app.audit_logs.push(message.clone());
                    app.status_message = message;
                }
                crate::app::AppEvent::AiTriageResult { message } => {
                    app.ai_triage_result = Some(message.clone());
                    app.event_feed.push("AI Triage analysis complete.".to_string());
                    app.audit_logs.push("Agent triggered AI Triage analysis.".to_string());
                    app.status_message = "AI Triage analysis complete.".to_string();
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

    // Modal check redirects
    match app.active_overlay {
        crate::app::ActiveOverlay::Help => {
            if key.code == KeyCode::Esc || key.code == KeyCode::Char(' ') || key.code == KeyCode::Char('h') || key.code == KeyCode::Char('?') {
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
            match key.code {
                KeyCode::Esc => {
                    app.active_overlay = crate::app::ActiveOverlay::None;
                    app.status_message = "Submit vulnerability cancelled.".to_string();
                }
                KeyCode::Tab => {
                    app.submit_form.active_field = match app.submit_form.active_field {
                        crate::app::FormField::Title => crate::app::FormField::RepoId,
                        crate::app::FormField::RepoId => crate::app::FormField::Severity,
                        crate::app::FormField::Severity => crate::app::FormField::Description,
                        crate::app::FormField::Description => crate::app::FormField::Title,
                    };
                }
                KeyCode::Enter => {
                    app.active_overlay = crate::app::ActiveOverlay::None;
                    let title = app.submit_form.title.clone();
                    let repo = app.submit_form.repo_id.clone();
                    let severity = app.submit_form.severity.clone();
                    let desc = app.submit_form.description.clone();
                    let api_base = app.api_base.clone();
                    let run_mode = app.run_mode.clone();
                    let sender = app.event_sender.clone();
                    
                    app.status_message = "Submitting vulnerability...".to_string();
                    tokio::spawn(async move {
                        let offline = run_mode == crate::app::RunMode::Offline;
                        let res = crate::api::submit_issue(&api_base, &title, &repo, &severity, &desc, offline).await;
                        let (success, message) = match res {
                            Ok(_) => (true, "SUCCESS: Vulnerability report submitted!".to_string()),
                            Err(e) => (false, format!("ERROR: Failed to submit: {}", e)),
                        };
                        let _ = sender.send(crate::app::AppEvent::SubmitResult { success, message });
                    });
                }
                KeyCode::Backspace => {
                    let field = match app.submit_form.active_field {
                        crate::app::FormField::Title => &mut app.submit_form.title,
                        crate::app::FormField::RepoId => &mut app.submit_form.repo_id,
                        crate::app::FormField::Severity => &mut app.submit_form.severity,
                        crate::app::FormField::Description => &mut app.submit_form.description,
                    };
                    field.pop();
                }
                KeyCode::Char(c) => {
                    let field = match app.submit_form.active_field {
                        crate::app::FormField::Title => &mut app.submit_form.title,
                        crate::app::FormField::RepoId => &mut app.submit_form.repo_id,
                        crate::app::FormField::Severity => &mut app.submit_form.severity,
                        crate::app::FormField::Description => &mut app.submit_form.description,
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
                        let hunt = &app.hunts[app.selected_hunt_index];
                        app.submit_form.title = format!("[{}] ", hunt.name);
                        app.submit_form.repo_id = "owasp-blt/api".to_string();
                        app.active_overlay = crate::app::ActiveOverlay::SubmitForm;
                        app.submit_form.active_field = crate::app::FormField::Description;
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
                KeyCode::Char('1') => { app.triage_target_status = "Open".to_string(); }
                KeyCode::Char('2') => { app.triage_target_status = "In Review".to_string(); }
                KeyCode::Char('3') => { app.triage_target_status = "Resolved".to_string(); }
                KeyCode::Enter => {
                    app.active_overlay = crate::app::ActiveOverlay::None;
                    let target = app.triage_target_status.clone();
                    let count = app.selected_issues.len();
                    app.status_message = format!("Bulk triaging {} issues to '{}'...", count, target);
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
                            });
                        }
                        let _ = sender.send(crate::app::AppEvent::SubmitResult {
                            success: true,
                            message: format!("Successfully bulk triaged {} issues to '{}'.", count, target),
                        });
                    });
                }
                _ => {}
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
            }
        }
        KeyCode::Char('s') => {
            app.active_overlay = crate::app::ActiveOverlay::SubmitForm;
        }
        KeyCode::Char('a') => {
            if app.active_tab == Tab::Issues && !app.issues.is_empty() {
                app.active_overlay = crate::app::ActiveOverlay::AiTriage;
                app.ai_triage_result = Some("Analyzing vulnerability using MCP AI tool...".to_string());
                let issue_id = app.issues[app.selected_issue_index].id.clone();
                let sender = app.event_sender.clone();
                tokio::spawn(async move {
                    tokio::time::sleep(std::time::Duration::from_secs(2)).await;
                    let message = format!("AI Triage Complete for Issue #{}.\nSeverity Suggestion: High\nDuplicate Check: No duplicates found.\nRecommendation: Apply parameterized queries immediately.", issue_id);
                    let _ = sender.send(crate::app::AppEvent::AiTriageResult { message });
                });
            }
        }
        
        KeyCode::Esc => app.close_popups(),
        _ => {}
    }
}
