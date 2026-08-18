//! Global Keyboard Navigation, Modal Interceptors, and Form Input Handling.
//!
//! This module handles all raw keyboard input events from crossterm, dispatching them
//! to active modal overlays, multi-field text inputs, tab navigators, or background actions.
//!
//! Key Functions:
//! - `handle_keys(key, app)`: Main keystroke router handling:
//!   - Global application termination (`q`, `Ctrl+C`).
//!   - Konami Code sequence detection for easter egg triggers.
//!   - Modal interceptors (Help, Triage, Submit Form, Search, Bulk Triage, AI Triage).
//!   - Tab navigation (Tab, BackTab, 1-5 numeric shortcuts).
//!   - List scrolling (Up/Down arrows, j/k vim keys).
//!   - Action triggers (reporting, triage, AI analysis, clipboard paste).

use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};

use crate::app::{ActiveOverlay, App, FormField, Tab, VulnerabilityForm};
use super::actions::{
    ai_triage_action, bulk_triage_action, extract_clipboard_action, handle_vision_draft,
    submit_issue_action,
};

/// Dispatches a key event to the appropriate modal, text input field, or global navigation handler.
pub fn handle_keys(key: KeyEvent, app: &mut App) {
    // 1. Global quit key
    if key.code == KeyCode::Char('q') && app.active_overlay == ActiveOverlay::None {
        app.should_quit = true;
        return;
    }
    if key.code == KeyCode::Char('c') && key.modifiers.contains(KeyModifiers::CONTROL) {
        app.should_quit = true;
        return;
    }

    let is_text_input = app.active_overlay == ActiveOverlay::SubmitForm
        || app.active_overlay == ActiveOverlay::SearchInput
        || app.active_overlay == ActiveOverlay::VisionContext;

    if key.code == KeyCode::Char('q')
        && !is_text_input
        && app.active_overlay != ActiveOverlay::None
    {
        app.active_overlay = ActiveOverlay::None;
        return;
    }

    // 2. Konami code check sequence
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
            app.active_overlay = ActiveOverlay::EasterEgg;
            app.konami_index = 0;
            return;
        }
    } else {
        app.konami_index = 0;
    }

    // 3. Modal Key Interceptors
    match app.active_overlay {
        ActiveOverlay::Help => {
            if key.code == KeyCode::Esc || key.code == KeyCode::Char(' ') {
                app.active_overlay = ActiveOverlay::None;
            }
            return;
        }
        ActiveOverlay::Triage => {
            match key.code {
                KeyCode::Enter => {
                    app.confirm_triage();
                }
                KeyCode::Esc => {
                    app.active_overlay = ActiveOverlay::None;
                    app.status_message = "Triage write operation cancelled.".to_string();
                }
                _ => {}
            }
            return;
        }
        ActiveOverlay::VisionContext => {
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
        ActiveOverlay::SubmitForm => {
            if key.code == KeyCode::Char('s') && key.modifiers.contains(KeyModifiers::CONTROL) {
                submit_issue_action(app);
                return;
            }

            if key.modifiers.contains(KeyModifiers::CONTROL) {
                return;
            }

            match key.code {
                KeyCode::Esc => {
                    app.active_overlay = ActiveOverlay::None;
                    app.status_message = "Submit vulnerability cancelled.".to_string();
                }
                KeyCode::Tab => {
                    app.submit_form.active_field = match app.submit_form.active_field {
                        FormField::Title => FormField::Url,
                        FormField::Url => FormField::Severity,
                        FormField::Severity => FormField::BugType,
                        FormField::BugType => FormField::Description,
                        FormField::Description => FormField::StepsToReproduce,
                        FormField::StepsToReproduce => FormField::Screenshot,
                        FormField::Screenshot => FormField::Title,
                    };
                }
                KeyCode::Enter => {
                    let field = match app.submit_form.active_field {
                        FormField::Title => &mut app.submit_form.title,
                        FormField::Url => &mut app.submit_form.url,
                        FormField::Severity => &mut app.submit_form.severity,
                        FormField::BugType => &mut app.submit_form.bug_type,
                        FormField::Description => &mut app.submit_form.description,
                        FormField::StepsToReproduce => &mut app.submit_form.steps_to_reproduce,
                        FormField::Screenshot => &mut app.submit_form.screenshot_path,
                    };
                    if app.submit_form.active_field == FormField::Description
                        || app.submit_form.active_field == FormField::StepsToReproduce
                    {
                        field.push('\n');
                    } else {
                        app.submit_form.active_field = match app.submit_form.active_field {
                            FormField::Title => FormField::Url,
                            FormField::Url => FormField::Severity,
                            FormField::Severity => FormField::BugType,
                            FormField::BugType => FormField::Description,
                            FormField::Description => FormField::StepsToReproduce,
                            FormField::StepsToReproduce => FormField::Screenshot,
                            FormField::Screenshot => FormField::Title,
                        };
                    }
                }
                KeyCode::Backspace => {
                    let field = match app.submit_form.active_field {
                        FormField::Title => &mut app.submit_form.title,
                        FormField::Url => &mut app.submit_form.url,
                        FormField::Severity => &mut app.submit_form.severity,
                        FormField::BugType => &mut app.submit_form.bug_type,
                        FormField::Description => &mut app.submit_form.description,
                        FormField::StepsToReproduce => &mut app.submit_form.steps_to_reproduce,
                        FormField::Screenshot => &mut app.submit_form.screenshot_path,
                    };
                    field.pop();
                }
                KeyCode::Char(c) => {
                    let field = match app.submit_form.active_field {
                        FormField::Title => &mut app.submit_form.title,
                        FormField::Url => &mut app.submit_form.url,
                        FormField::Severity => &mut app.submit_form.severity,
                        FormField::BugType => &mut app.submit_form.bug_type,
                        FormField::Description => &mut app.submit_form.description,
                        FormField::StepsToReproduce => &mut app.submit_form.steps_to_reproduce,
                        FormField::Screenshot => &mut app.submit_form.screenshot_path,
                    };
                    field.push(c);
                }
                _ => {}
            }
            return;
        }
        ActiveOverlay::HuntDetail => {
            match key.code {
                KeyCode::Esc => {
                    app.active_overlay = ActiveOverlay::None;
                }
                KeyCode::Char('s') if !app.hunts.is_empty() => {
                    app.submit_form = VulnerabilityForm::default();
                    app.submit_form.url = "".to_string();
                    app.active_overlay = ActiveOverlay::SubmitForm;
                    app.submit_form.active_field = FormField::Url;
                    app.status_message = "Opened Submit Form for Hunt Context".to_string();
                }
                _ => {}
            }
            return;
        }
        ActiveOverlay::AiTriage => {
            if key.code == KeyCode::Esc {
                app.active_overlay = ActiveOverlay::None;
            }
            return;
        }
        ActiveOverlay::SearchInput => {
            match key.code {
                KeyCode::Esc => {
                    app.active_overlay = ActiveOverlay::None;
                    app.search_query.clear();
                }
                KeyCode::Enter => {
                    app.active_overlay = ActiveOverlay::None;
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
        ActiveOverlay::BulkTriageConfirm => {
            match key.code {
                KeyCode::Esc => {
                    app.active_overlay = ActiveOverlay::None;
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
                    bulk_triage_action(app);
                }
                _ => {}
            }
            return;
        }
        ActiveOverlay::AgentStatus => {
            if key.code == KeyCode::Esc || key.code == KeyCode::Char('A') {
                app.active_overlay = ActiveOverlay::None;
            }
            return;
        }
        ActiveOverlay::PromptPreview => {
            if key.code == KeyCode::Esc || key.code == KeyCode::Char('P') {
                app.active_overlay = ActiveOverlay::None;
            }
            return;
        }
        ActiveOverlay::EasterEgg => {
            if key.code == KeyCode::Esc
                || key.code == KeyCode::Enter
                || key.code == KeyCode::Char(' ')
            {
                app.active_overlay = ActiveOverlay::None;
            }
            return;
        }
        _ => {}
    }

    // 4. Navigation and Main Workspace Operations
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

        // Dialog overlays and actions
        KeyCode::Char('e') => {
            if app.active_tab == Tab::Logs {
                app.export_logs();
                app.status_message = "Logs exported to blt_export.log".to_string();
            }
        }
        KeyCode::Char('/') => {
            app.active_overlay = ActiveOverlay::SearchInput;
        }
        KeyCode::Char('p') | KeyCode::Char('v')
            if key.code == KeyCode::Char('p')
                || (key.code == KeyCode::Char('v')
                    && key.modifiers.contains(KeyModifiers::CONTROL)) =>
        {
            extract_clipboard_action(app);
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
                app.active_overlay = ActiveOverlay::BulkTriageConfirm;
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
                app.active_overlay = ActiveOverlay::HuntDetail;
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
                        app.submit_form = VulnerabilityForm::default();
                        app.active_overlay = ActiveOverlay::SubmitForm;
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
            if key.modifiers.is_empty() {
                app.submit_form = VulnerabilityForm::default();
                app.active_overlay = ActiveOverlay::SubmitForm;
            }
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
                app.active_overlay = ActiveOverlay::AiTriage;
                app.ai_triage_result =
                    Some("Analyzing vulnerability using MCP AI tool...".to_string());

                let issue = &app.issues[app.selected_issue_index];
                let issue_id = issue.id.clone();
                let issue_title = issue.title.clone();
                let issue_desc = issue.description.clone();
                let sender = app.event_sender.clone();
                let mcp_client_clone = app.mcp_client.clone();

                ai_triage_action(
                    mcp_client_clone,
                    sender,
                    issue_id,
                    issue_title,
                    issue_desc,
                );
            }
        }
        KeyCode::Esc => app.close_popups(),
        _ => {}
    }
}
