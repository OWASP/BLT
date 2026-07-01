#![allow(dead_code)]
use crate::models::{self, Issue, Repo, Hunt, Stats};

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
    Mcp,
    Live,
}

#[derive(Clone, Debug, PartialEq)]
pub enum FormField {
    Url,
    Severity,
    Description,
}

impl Default for FormField {
    fn default() -> Self {
        FormField::Url
    }
}

#[derive(Clone, Debug, Default)]
pub struct VulnerabilityForm {
    pub url: String,
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
    CommandPalette,
    AgentStatus,
    PromptPreview,
    EasterEgg,
}

pub enum AppEvent {
    TriageConfirmed { issue_id: String, success: bool, message: String },
    SubmitResult { success: bool, message: String },
    IssuesRefreshed { issues: Vec<crate::models::Issue>, total: u32 },
    AiTriageResult { message: String },
    ScanComplete { health: crate::scanner::SecurityHealth },
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
    pub leaderboard: Vec<models::LeaderboardEntry>,
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
    pub mcp_client: Option<std::sync::Arc<tokio::sync::Mutex<crate::mcp_client::McpSubprocessClient>>>,
    pub security_health: Option<crate::scanner::SecurityHealth>,
    pub command_input: String,
    pub konami_index: usize,
    pub agent_status_data: String,
    pub prompt_preview_data: String,
}

impl App {
    pub fn new(mcp_path: Option<String>, api_base: String) -> App {
        let (event_sender, event_receiver) = tokio::sync::mpsc::unbounded_channel();
        let run_mode = if mcp_path.is_some() {
            RunMode::Mcp
        } else {
            RunMode::Live
        };

        let auth_user = if run_mode == RunMode::Mcp {
            "Local User (MCP Mode)".to_string()
        } else {
            "Local User (REST)".to_string()
        };

        let status_message = match run_mode {
            RunMode::Mcp => "Initialized CLI in MCP Host Mode. Spawning subprocess server...".to_string(),
            RunMode::Live => format!("Connected directly to BLT API at {}", api_base),
        };

        let mut app = App {
            active_tab: Tab::Issues,
            issues: Vec::new(),
            repos: Vec::new(),
            hunts: Vec::new(),
            stats: Stats { total_issues: 0, active_repos: 0, total_contributors: 0, bacon_points: 0 },
            selected_issue_index: 0,
            selected_repo_index: 0,
            selected_hunt_index: 0,
            should_quit: false,
            active_overlay: ActiveOverlay::None,
            submit_form: VulnerabilityForm::default(),
            leaderboard: Vec::new(),
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
            command_input: String::new(),
            konami_index: 0,
            agent_status_data: "Agent Status: Idle\nConnected: false\nUptime: 0m\nMemory: 0MB".to_string(),
            prompt_preview_data: "Loading prompt preview...".to_string(),
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

    pub fn toggle_agent_status(&mut self) {
        if self.active_overlay != ActiveOverlay::None && self.active_overlay != ActiveOverlay::AgentStatus {
            return;
        }
        if self.active_overlay == ActiveOverlay::AgentStatus {
            self.active_overlay = ActiveOverlay::None;
        } else {
            self.active_overlay = ActiveOverlay::AgentStatus;
        }
    }

    pub fn toggle_prompt_preview(&mut self) {
        if self.active_overlay != ActiveOverlay::None && self.active_overlay != ActiveOverlay::PromptPreview {
            return;
        }
        if self.active_overlay == ActiveOverlay::PromptPreview {
            self.active_overlay = ActiveOverlay::None;
        } else {
            self.active_overlay = ActiveOverlay::PromptPreview;
            self.prompt_preview_data = "AI Prompt Preview will appear here once connected.".to_string();
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
        
        self.status_message = format!("Triaging Issue #{}...", issue_id);

        tokio::spawn(async move {
            let res = crate::api::submit_issue_triage(&api_base, &issue_id).await;

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
    
    pub fn reset_data(&mut self) {
        self.issues.clear();
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
        assert_eq!(app.active_tab, Tab::Stats);
        app.prev_tab();
        assert_eq!(app.active_tab, Tab::Hunts);
    }

    #[test]
    fn test_issue_selection() {
        let mut app = App::new(None, "".to_string());
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
