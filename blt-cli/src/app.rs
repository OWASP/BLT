//! Application State Management and Event Coordination for the TUI Client.
//!
//! This module defines the main `App` state machine and coordinating event structures
//! that drive the Ratatui TUI client application.
//!
//! Key Data Types:
//! - `Tab`: Enum representing the current active dashboard view: `Issues`, `Hunts`, `Stats`, `Logs`, `Settings`, or `Onboarding`.
//! - `ActiveOverlay`: Enum for overlapping modal screens: `Help`, `Triage`, `SubmitForm`, `HuntDetail`, `AiTriage`, `CommandPalette`, etc.
//! - `FormField`: Enum indicating which input textbox has active focus in the submission form.
//! - `VulnerabilityForm`: Captures fields for title, url, severity, type, description, and local screenshot file path.
//! - `AppEvent`: Internal events dispatched by asynchronous tokio tasks (e.g. scanner completions, tool call responses, API refreshes).
//! - `App`: Main orchestrator structure. Manages loaded issues, active hunts, audit logs, communication channels (`UnboundedSender`/`UnboundedReceiver`),
//!   the local subprocess `McpSubprocessClient` pointer, and local session details.
//!
//! Key Functions:
//! - `App::new(mcp_path, api_base)`: Initializes channel communication buffers and loads system info.
//! - `App::save_session()` & `load_session()`: Persists audit logs and event history into `blt_session.json` to keep state between restarts.
//! - `App::export_logs()`: Outputs execution histories into `blt_export.log`.
//! - `App::confirm_triage()`: Spawns async tokio tasks to invoke issues triage commands.
//!
//! Unit Tests:
//! - Includes module tests to verify navigation tabs and modal toggle operations.

#![allow(dead_code)]

use crate::models::{Hunt, Issue, Repo, Stats};

#[derive(Copy, Clone, Debug, PartialEq)]
pub enum Tab {
    Issues,
    Hunts,
    Onboarding,
    Stats,
    Logs,
    Settings,
}

impl Tab {
    pub fn name(&self) -> &'static str {
        match self {
            Tab::Issues => "Issues",
            Tab::Hunts => "Active Hunts",
            Tab::Onboarding => "Onboarding",
            Tab::Stats => "BLT Stats",
            Tab::Logs => "Logs & Events",
            Tab::Settings => "Settings",
        }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub enum RunMode {
    Mcp,
    Live,
}

#[derive(Clone, Debug, PartialEq)]
pub enum FormField {
    Title,
    Url,
    Severity,
    BugType,
    Description,
    StepsToReproduce,
    Screenshot,
}

impl Default for FormField {
    fn default() -> Self {
        FormField::Title
    }
}

#[derive(Clone, Debug, Default)]
pub struct VulnerabilityForm {
    pub title: String,
    pub url: String,
    pub severity: String,
    pub bug_type: String,
    pub description: String,
    pub steps_to_reproduce: String,
    pub screenshot_path: String,
    pub active_field: FormField,
}

#[derive(Clone, Debug, PartialEq)]
pub enum ActiveOverlay {
    None,
    Help,
    Triage,
    SubmitForm,
    HuntDetail,
    AiTriage,
    SearchInput,
    BulkTriageConfirm,
    AgentStatus,
    PromptPreview,
    EasterEgg,
    VisionContext,
}

pub enum AppEvent {
    TriageConfirmed {
        issue_id: String,
        success: bool,
        message: String,
        target_status: String,
    },
    SubmitResult {
        success: bool,
        message: String,
    },
    IssuesRefreshed {
        issues: Vec<crate::models::Issue>,
        total: u32,
    },
    VisionDraftComplete {
        result: String,
        success: bool,
    },
    AiTriageResult {
        message: String,
        success: bool,
    },
    ScanComplete {
        health: crate::scanner::SecurityHealth,
    },
}

pub struct App {
    pub active_tab: Tab,
    pub issues: Vec<Issue>,
    pub repos: Vec<Repo>,
    pub hunts: Vec<Hunt>,
    pub stats: Stats,
    pub leaderboard: Vec<crate::models::LeaderboardEntry>,
    pub good_first_issues: Vec<crate::models::GoodFirstIssue>,
    pub selected_issue_index: usize,
    pub selected_repo_index: usize,
    pub selected_hunt_index: usize,
    pub should_quit: bool,
    pub active_overlay: ActiveOverlay,
    pub submit_form: VulnerabilityForm,
    pub ai_triage_result: Option<String>,
    pub search_query: String,
    pub selected_issues: std::collections::HashSet<String>,
    pub audit_logs: Vec<String>,
    pub event_feed: Vec<String>,
    pub triage_target_status: String,
    pub event_sender: tokio::sync::mpsc::UnboundedSender<AppEvent>,
    pub event_receiver: tokio::sync::mpsc::UnboundedReceiver<AppEvent>,
    pub run_mode: RunMode,
    pub mcp_path: Option<String>,
    pub api_base: String,
    pub status_message: String,
    pub auth_user: String,
    pub is_live: bool,
    pub mcp_client:
        Option<std::sync::Arc<tokio::sync::Mutex<crate::mcp_client::McpSubprocessClient>>>,
    pub security_health: Option<crate::scanner::SecurityHealth>,
    pub konami_index: usize,
    pub agent_status_data: String,
    pub prompt_preview_data: String,
    pub vision_context_input: String,
    pub vision_image_path: String,
}

impl App {
    pub fn new(mcp_path: Option<String>, api_base: String) -> App {
        let (event_sender, event_receiver) = tokio::sync::mpsc::unbounded_channel();
        let run_mode = if mcp_path.is_some() {
            RunMode::Mcp
        } else {
            RunMode::Live
        };

        let system_user = std::env::var("USER")
            .or_else(|_| std::env::var("USERNAME"))
            .unwrap_or_else(|_| "Local User".to_string());
        let auth_user = if run_mode == RunMode::Mcp {
            format!("Local System User: {} (MCP Mode)", system_user)
        } else {
            format!("Local System User: {} (REST)", system_user)
        };

        let status_message = match run_mode {
            RunMode::Mcp => {
                "Initialized CLI in MCP Host Mode. Spawning subprocess server...".to_string()
            }
            RunMode::Live => format!("Connected directly to BLT API at {}", api_base),
        };

        let mut app = App {
            active_tab: Tab::Issues,
            issues: Vec::new(),
            repos: Vec::new(),
            hunts: Vec::new(),
            stats: Stats {
                total_issues: 0,
                active_repos: 0,
                total_contributors: 0,
                bacon_points: 0,
            },
            leaderboard: Vec::new(),
            good_first_issues: Vec::new(),
            selected_issue_index: 0,
            selected_repo_index: 0,
            selected_hunt_index: 0,
            should_quit: false,
            active_overlay: ActiveOverlay::None,
            submit_form: VulnerabilityForm::default(),
            ai_triage_result: None,
            search_query: String::new(),
            selected_issues: std::collections::HashSet::new(),
            audit_logs: Vec::new(),
            event_feed: Vec::new(),
            triage_target_status: "In Review".to_string(),
            event_sender,
            event_receiver,
            run_mode,
            mcp_path,
            api_base,
            status_message,
            auth_user,
            is_live: false,
            mcp_client: None,
            security_health: None,
            konami_index: 0,
            agent_status_data: "Agent Status: Idle\nConnected: false\nUptime: 0m\nMemory: 0MB"
                .to_string(),
            prompt_preview_data: "Loading prompt preview...".to_string(),
            vision_context_input: String::new(),
            vision_image_path: String::new(),
        };
        app.load_session();
        app
    }

    pub fn next_tab(&mut self) {
        if self.active_overlay != ActiveOverlay::None {
            return;
        }
        self.active_tab = match self.active_tab {
            Tab::Issues => Tab::Hunts,
            Tab::Hunts => Tab::Onboarding,
            Tab::Onboarding => Tab::Stats,
            Tab::Stats => Tab::Logs,
            Tab::Logs => Tab::Settings,
            Tab::Settings => Tab::Issues,
        };
        self.status_message = format!("Switched to tab: {}", self.active_tab.name());
    }

    pub fn prev_tab(&mut self) {
        if self.active_overlay != ActiveOverlay::None {
            return;
        }
        self.active_tab = match self.active_tab {
            Tab::Issues => Tab::Settings,
            Tab::Hunts => Tab::Issues,
            Tab::Onboarding => Tab::Hunts,
            Tab::Stats => Tab::Onboarding,
            Tab::Logs => Tab::Stats,
            Tab::Settings => Tab::Logs,
        };
        self.status_message = format!("Switched to tab: {}", self.active_tab.name());
    }

    pub fn get_visible_issue_indices(&self) -> Vec<usize> {
        let mut indices = Vec::new();
        for (idx, issue) in self.issues.iter().enumerate() {
            if !self.search_query.is_empty() {
                let q = self.search_query.to_lowercase();
                if !issue.title.to_lowercase().contains(&q)
                    && !issue.url.to_lowercase().contains(&q)
                    && !issue.status.to_lowercase().contains(&q)
                    && !issue.severity.to_lowercase().contains(&q)
                    && !issue.id.to_lowercase().contains(&q)
                {
                    continue;
                }
            }
            indices.push(idx);
        }
        indices
    }

    pub fn get_visible_hunt_indices(&self) -> Vec<usize> {
        let mut indices = Vec::new();
        for (idx, hunt) in self.hunts.iter().enumerate() {
            if !self.search_query.is_empty() {
                let q = self.search_query.to_lowercase();
                if !hunt.name.to_lowercase().contains(&q)
                    && !hunt.description.to_lowercase().contains(&q)
                    && !hunt.status.to_lowercase().contains(&q)
                    && !hunt.reward.to_lowercase().contains(&q)
                {
                    continue;
                }
            }
            indices.push(idx);
        }
        indices
    }

    pub fn scroll_down(&mut self) {
        if self.active_overlay != ActiveOverlay::None {
            return;
        }
        match self.active_tab {
            Tab::Issues => {
                let visible = self.get_visible_issue_indices();
                if !visible.is_empty() {
                    let current_pos = visible.iter().position(|&x| x == self.selected_issue_index).unwrap_or(0);
                    let next_pos = (current_pos + 1) % visible.len();
                    self.selected_issue_index = visible[next_pos];
                }
            }
            Tab::Hunts => {
                let visible = self.get_visible_hunt_indices();
                if !visible.is_empty() {
                    let current_pos = visible.iter().position(|&x| x == self.selected_hunt_index).unwrap_or(0);
                    let next_pos = (current_pos + 1) % visible.len();
                    self.selected_hunt_index = visible[next_pos];
                }
            }
            _ => {}
        }
    }

    pub fn scroll_up(&mut self) {
        if self.active_overlay != ActiveOverlay::None {
            return;
        }
        match self.active_tab {
            Tab::Issues => {
                let visible = self.get_visible_issue_indices();
                if !visible.is_empty() {
                    let current_pos = visible.iter().position(|&x| x == self.selected_issue_index).unwrap_or(0);
                    let next_pos = if current_pos == 0 {
                        visible.len() - 1
                    } else {
                        current_pos - 1
                    };
                    self.selected_issue_index = visible[next_pos];
                }
            }
            Tab::Hunts => {
                let visible = self.get_visible_hunt_indices();
                if !visible.is_empty() {
                    let current_pos = visible.iter().position(|&x| x == self.selected_hunt_index).unwrap_or(0);
                    let next_pos = if current_pos == 0 {
                        visible.len() - 1
                    } else {
                        current_pos - 1
                    };
                    self.selected_hunt_index = visible[next_pos];
                }
            }
            _ => {}
        }
    }

    pub fn toggle_help(&mut self) {
        if self.active_overlay != ActiveOverlay::None && self.active_overlay != ActiveOverlay::Help
        {
            return;
        }
        if self.active_overlay == ActiveOverlay::Help {
            self.active_overlay = ActiveOverlay::None;
        } else {
            self.active_overlay = ActiveOverlay::Help;
        }
    }

    pub fn toggle_agent_status(&mut self) {
        if self.active_overlay != ActiveOverlay::None
            && self.active_overlay != ActiveOverlay::AgentStatus
        {
            return;
        }
        if self.active_overlay == ActiveOverlay::AgentStatus {
            self.active_overlay = ActiveOverlay::None;
        } else {
            self.active_overlay = ActiveOverlay::AgentStatus;
        }
    }

    pub fn toggle_prompt_preview(&mut self) {
        if self.active_overlay != ActiveOverlay::None
            && self.active_overlay != ActiveOverlay::PromptPreview
        {
            return;
        }
        if self.active_overlay == ActiveOverlay::PromptPreview {
            self.active_overlay = ActiveOverlay::None;
        } else {
            self.active_overlay = ActiveOverlay::PromptPreview;
            self.prompt_preview_data =
                "AI Prompt Preview will appear here once connected.".to_string();
        }
    }

    pub fn close_popups(&mut self) {
        self.active_overlay = ActiveOverlay::None;
    }

    pub fn trigger_triage(&mut self) {
        if self.active_tab != Tab::Issues || self.issues.is_empty() {
            return;
        }

        let issue = &self.issues[self.selected_issue_index];
        if issue.status == "In Review" {
            self.status_message = "Notice: Issue is already 'In Review'.".to_string();
            return;
        }

        self.active_overlay = ActiveOverlay::Triage;
    }

    pub fn confirm_triage(&mut self) {
        if self.active_overlay != ActiveOverlay::Triage {
            return;
        }
        self.active_overlay = ActiveOverlay::None;

        let issue = &self.issues[self.selected_issue_index];
        let issue_id = issue.id.clone();
        let api_base = self.api_base.clone();
        let sender = self.event_sender.clone();
        let target_status = self.triage_target_status.clone();

        self.status_message = format!("Triaging Issue #{}...", issue_id);

        tokio::spawn(async move {
            let res = crate::api::submit_issue_triage(&api_base, &issue_id, &target_status).await;

            let (success, message) = match res {
                Ok(_) => (
                    true,
                    format!(
                        "SUCCESS: Triage for Issue #{} was submitted successfully.",
                        issue_id
                    ),
                ),
                Err(e) => (
                    false,
                    format!(
                        "ERROR: Failed to submit triage for Issue #{}: {}",
                        issue_id, e
                    ),
                ),
            };

            let _ = sender.send(AppEvent::TriageConfirmed {
                issue_id,
                success,
                message,
                target_status,
            });
        });
    }

    pub fn save_session(&self) {
        #[derive(serde::Serialize)]
        struct SessionData<'a> {
            audit_logs: &'a Vec<String>,
            event_feed: &'a Vec<String>,
        }
        let data = SessionData {
            audit_logs: &self.audit_logs,
            event_feed: &self.event_feed,
        };
        if let Ok(json) = serde_json::to_string(&data) {
            let temp_file = format!("blt_session_{}.json.tmp", std::process::id());
            if std::fs::write(&temp_file, &json).is_ok() {
                let _ = std::fs::rename(&temp_file, "blt_session.json");
            }
        }
    }

    pub fn load_session(&mut self) {
        #[derive(serde::Deserialize)]
        struct SessionData {
            audit_logs: Vec<String>,
            event_feed: Vec<String>,
        }
        if let Ok(content) = std::fs::read_to_string("blt_session.json") {
            if let Ok(data) = serde_json::from_str::<SessionData>(&content) {
                self.audit_logs = data.audit_logs;
                self.event_feed = data.event_feed;
            }
        }
    }

    pub fn export_logs(&self) {
        let mut out = String::new();
        out.push_str("=== AUDIT LOGS ===\n");
        for log in &self.audit_logs {
            out.push_str(log);
            out.push('\n');
        }
        out.push_str("\n=== EVENT FEED ===\n");
        for ev in &self.event_feed {
            out.push_str(ev);
            out.push('\n');
        }
        let _ = std::fs::write("blt_export.log", out);
    }

    pub fn reset_data(&mut self) {
        self.issues.clear();
        self.selected_issue_index = 0;
        self.selected_issues.clear();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_app_initialization() {
        let app = App::new(None, "https://api.owaspblt.org".to_string());
        assert_eq!(app.active_tab, Tab::Issues);
        assert_eq!(app.active_overlay, ActiveOverlay::None);
    }

    #[test]
    fn test_modal_toggles() {
        let mut app = App::new(None, "https://api.owaspblt.org".to_string());
        assert_eq!(app.active_overlay, ActiveOverlay::None);

        app.toggle_help();
        assert_eq!(app.active_overlay, ActiveOverlay::Help);
        app.toggle_help();
        assert_eq!(app.active_overlay, ActiveOverlay::None);
    }

    #[test]
    fn test_tab_navigation() {
        let mut app = App::new(None, "".to_string());
        assert_eq!(app.active_tab, Tab::Issues);
        app.next_tab();
        assert_eq!(app.active_tab, Tab::Hunts);
        app.next_tab();
        assert_eq!(app.active_tab, Tab::Onboarding);
        app.prev_tab();
        assert_eq!(app.active_tab, Tab::Hunts);
    }

    #[test]
    fn test_issue_selection() {
        let mut app = App::new(None, "".to_string());
        app.issues = vec![
            Issue {
                id: "1".to_string(),
                url: "url".to_string(),
                title: "title".to_string(),
                description: "desc".to_string(),
                status: "Open".to_string(),
                severity: "Low".to_string(),
                author: "author".to_string(),
                comments: vec![],
            },
            Issue {
                id: "2".to_string(),
                url: "url".to_string(),
                title: "title2".to_string(),
                description: "desc2".to_string(),
                status: "Open".to_string(),
                severity: "Low".to_string(),
                author: "author".to_string(),
                comments: vec![],
            },
        ];
        let initial_len = app.issues.len();

        if initial_len > 1 {
            assert_eq!(app.selected_issue_index, 0);
            app.scroll_down();
            assert_eq!(app.selected_issue_index, 1);
            app.scroll_up();
            assert_eq!(app.selected_issue_index, 0);
        }
    }
}
