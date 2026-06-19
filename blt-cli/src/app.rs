#![allow(dead_code)]
use crate::mock_data::{self, Issue, Repo, Hunt, Stats};

#[derive(Copy, Clone, Debug, PartialEq)]
pub enum Tab {
    Issues,
    Hunts,
    Stats,
    Logs,
    Settings,
}

impl Tab {
    pub fn name(&self) -> &'static str {
        match self {
            Tab::Issues => "Issues",
            Tab::Hunts => "Active Hunts",
            Tab::Stats => "BLT Stats",
            Tab::Logs => "Logs & Events",
            Tab::Settings => "Settings",
        }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub enum RunMode {
    Offline,
    Standalone,
    Mcp,
}

#[derive(Clone, Debug, PartialEq)]
pub enum FormField {
    Title,
    RepoId,
    Severity,
    Description,
}

impl Default for FormField {
    fn default() -> Self {
        FormField::Title
    }
}

#[derive(Clone, Debug, Default)]
pub struct VulnerabilityForm {
    pub title: String,
    pub repo_id: String,
    pub severity: String,
    pub description: String,
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
}

pub enum AppEvent {
    TriageConfirmed { issue_id: String, success: bool, message: String },
    SubmitResult { success: bool, message: String },
    AiTriageResult { message: String },
}

pub struct App {
    pub active_tab: Tab,
    pub issues: Vec<Issue>,
    pub repos: Vec<Repo>,
    pub hunts: Vec<Hunt>,
    pub stats: Stats,
    pub selected_issue_index: usize,
    pub selected_repo_index: usize,
    pub selected_hunt_index: usize,
    pub should_quit: bool,
    pub active_overlay: ActiveOverlay,
    pub submit_form: VulnerabilityForm,
    pub leaderboard: Vec<mock_data::LeaderboardEntry>,
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
}

impl App {
    pub fn new(offline: bool, mcp_path: Option<String>, api_base: String) -> Self {
        let run_mode = if offline {
            RunMode::Offline
        } else if mcp_path.is_some() {
            RunMode::Mcp
        } else {
            RunMode::Standalone
        };

        // Populate with mock data for offline testing by default
        let issues = mock_data::get_mock_issues();
        let repos = mock_data::get_mock_repos();
        let hunts = mock_data::get_mock_hunts();
        let stats = mock_data::get_mock_stats();

        let auth_user = match run_mode {
            RunMode::Offline => "NachiketRoy (Offline Mode)".to_string(),
            RunMode::Mcp => "AI Agent (MCP Mode)".to_string(),
            RunMode::Standalone => "NachiketRoy (OAuth 2.0)".to_string(),
        };

        let status_message = match run_mode {
            RunMode::Offline => "Initialized CLI in Offline Mode. Hit [h] for help.".to_string(),
            RunMode::Mcp => "Initialized CLI in MCP Host Mode. Spawning subprocess server...".to_string(),
            RunMode::Standalone => format!("Connected directly to BLT API at {}", api_base),
        };

        let (event_sender, event_receiver) = tokio::sync::mpsc::unbounded_channel();

        let mut app = App {
            active_tab: Tab::Issues,
            issues,
            repos,
            hunts,
            stats,
            selected_issue_index: 0,
            selected_repo_index: 0,
            selected_hunt_index: 0,
            should_quit: false,
            active_overlay: ActiveOverlay::None,
            submit_form: VulnerabilityForm::default(),
            leaderboard: mock_data::get_mock_leaderboard(),
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
            Tab::Hunts => Tab::Stats,
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
            Tab::Stats => Tab::Hunts,
            Tab::Logs => Tab::Stats,
            Tab::Settings => Tab::Logs,
        };
        self.status_message = format!("Switched to tab: {}", self.active_tab.name());
    }

    pub fn scroll_down(&mut self) {
        if self.active_overlay != ActiveOverlay::None {
            return;
        }
        match self.active_tab {
            Tab::Issues => {
                if !self.issues.is_empty() {
                    self.selected_issue_index = (self.selected_issue_index + 1) % self.issues.len();
                }
            }
            Tab::Hunts => {
                if !self.hunts.is_empty() {
                    self.selected_hunt_index = (self.selected_hunt_index + 1) % self.hunts.len();
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
                if !self.issues.is_empty() {
                    if self.selected_issue_index == 0 {
                        self.selected_issue_index = self.issues.len() - 1;
                    } else {
                        self.selected_issue_index -= 1;
                    }
                }
            }
            Tab::Hunts => {
                if !self.hunts.is_empty() {
                    if self.selected_hunt_index == 0 {
                        self.selected_hunt_index = self.hunts.len() - 1;
                    } else {
                        self.selected_hunt_index -= 1;
                    }
                }
            }
            _ => {}
        }
    }

    pub fn toggle_help(&mut self) {
        if self.active_overlay != ActiveOverlay::None && self.active_overlay != ActiveOverlay::Help {
            return;
        }
        if self.active_overlay == ActiveOverlay::Help {
            self.active_overlay = ActiveOverlay::None;
        } else {
            self.active_overlay = ActiveOverlay::Help;
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
        let run_mode = self.run_mode.clone();
        let sender = self.event_sender.clone();
        
        self.status_message = format!("Triaging Issue #{}...", issue_id);

        tokio::spawn(async move {
            let offline = run_mode == RunMode::Offline;
            let res = crate::api::submit_issue_triage(&api_base, &issue_id, offline).await;

            let (success, message) = match res {
                Ok(_) => (true, format!("SUCCESS: Triage for Issue #{} was submitted successfully.", issue_id)),
                Err(e) => (false, format!("ERROR: Failed to submit triage for Issue #{}: {}", issue_id, e)),
            };

            let _ = sender.send(AppEvent::TriageConfirmed { issue_id, success, message });
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
            let _ = std::fs::write("blt_session.json", json);
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
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_app_initialization() {
        let app = App::new(true, None, "https://api.owaspblt.org".to_string());
        assert_eq!(app.active_tab, Tab::Issues);
        assert_eq!(app.active_overlay, ActiveOverlay::None);
    }

    #[test]
    fn test_modal_toggles() {
        let mut app = App::new(true, None, "https://api.owaspblt.org".to_string());
        assert_eq!(app.active_overlay, ActiveOverlay::None);

        app.toggle_help();
        assert_eq!(app.active_overlay, ActiveOverlay::Help);
        app.toggle_help();
        assert_eq!(app.active_overlay, ActiveOverlay::None);
    }

    #[test]
    fn test_tab_navigation() {
        let mut app = App::new(true, None, "".to_string());
        assert_eq!(app.active_tab, Tab::Issues);
        app.next_tab();
        assert_eq!(app.active_tab, Tab::Hunts);
        app.next_tab();
        assert_eq!(app.active_tab, Tab::Stats);
        app.prev_tab();
        assert_eq!(app.active_tab, Tab::Hunts);
    }

    #[test]
    fn test_issue_selection() {
        let mut app = App::new(true, None, "".to_string());
        app.issues = crate::mock_data::get_mock_issues();
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
