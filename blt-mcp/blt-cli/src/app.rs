#![allow(dead_code)]
use crate::mock_data::{self, Issue, Repo, Hunt, Stats};

#[derive(Copy, Clone, Debug, PartialEq)]
pub enum Tab {
    Issues,
    Hunts,
    Stats,
    Settings,
}

impl Tab {
    pub fn name(&self) -> &'static str {
        match self {
            Tab::Issues => "Issues",
            Tab::Hunts => "Active Hunts",
            Tab::Stats => "BLT Stats",
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
    pub show_help: bool,
    pub show_triage_modal: bool,
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

        App {
            active_tab: Tab::Issues,
            issues,
            repos,
            hunts,
            stats,
            selected_issue_index: 0,
            selected_repo_index: 0,
            selected_hunt_index: 0,
            should_quit: false,
            show_help: false,
            show_triage_modal: false,
            run_mode,
            mcp_path,
            api_base,
            status_message,
            auth_user,
            is_live: false,
        }
    }

    pub fn next_tab(&mut self) {
        if self.show_help || self.show_triage_modal {
            return;
        }
        self.active_tab = match self.active_tab {
            Tab::Issues => Tab::Hunts,
            Tab::Hunts => Tab::Stats,
            Tab::Stats => Tab::Settings,
            Tab::Settings => Tab::Issues,
        };
        self.status_message = format!("Switched to tab: {}", self.active_tab.name());
    }

    pub fn prev_tab(&mut self) {
        if self.show_help || self.show_triage_modal {
            return;
        }
        self.active_tab = match self.active_tab {
            Tab::Issues => Tab::Settings,
            Tab::Hunts => Tab::Issues,
            Tab::Stats => Tab::Hunts,
            Tab::Settings => Tab::Stats,
        };
        self.status_message = format!("Switched to tab: {}", self.active_tab.name());
    }

    pub fn scroll_down(&mut self) {
        if self.show_help || self.show_triage_modal {
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
        if self.show_help || self.show_triage_modal {
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
        if self.show_triage_modal {
            return;
        }
        self.show_help = !self.show_help;
    }

    pub fn close_popups(&mut self) {
        self.show_help = false;
        self.show_triage_modal = false;
    }

    pub fn trigger_triage(&mut self) {
        if self.active_tab != Tab::Issues || self.issues.is_empty() {
            return;
        }
        self.show_triage_modal = true;
    }

    pub fn confirm_triage(&mut self) {
        if !self.show_triage_modal {
            return;
        }
        self.show_triage_modal = false;
        let issue = &mut self.issues[self.selected_issue_index];
        issue.status = "In Review".to_string();
        let update_msg = format!("Triage confirmed: Status of Issue #{} set to 'In Review'!", issue.id);
        
        // Push an audit log comment representing human-in-the-loop triage confirmation
        issue.comments.push(format!("{}: Manually confirmed & updated triage status via TUI CLI.", self.auth_user));
        self.status_message = update_msg;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_app_initialization() {
        let app = App::new(true, None, "https://api.owaspblt.org".to_string());
        assert_eq!(app.run_mode, RunMode::Offline);
        assert_eq!(app.active_tab, Tab::Issues);
        assert!(!app.issues.is_empty());
        assert!(!app.repos.is_empty());
        assert!(!app.hunts.is_empty());
        assert!(!app.show_help);
        assert!(!app.show_triage_modal);
        assert!(app.auth_user.contains("Offline Mode"));
    }

    #[test]
    fn test_tab_navigation() {
        let mut app = App::new(true, None, "https://api.owaspblt.org".to_string());
        
        // Next tabs loop: Issues -> Hunts -> Stats -> Settings -> Issues
        app.next_tab();
        assert_eq!(app.active_tab, Tab::Hunts);
        app.next_tab();
        assert_eq!(app.active_tab, Tab::Stats);
        app.next_tab();
        assert_eq!(app.active_tab, Tab::Settings);
        app.next_tab();
        assert_eq!(app.active_tab, Tab::Issues);

        // Prev tabs loop: Issues -> Settings -> Stats -> Hunts -> Issues
        app.prev_tab();
        assert_eq!(app.active_tab, Tab::Settings);
        app.prev_tab();
        assert_eq!(app.active_tab, Tab::Stats);
        app.prev_tab();
        assert_eq!(app.active_tab, Tab::Hunts);
        app.prev_tab();
        assert_eq!(app.active_tab, Tab::Issues);
    }

    #[test]
    fn test_list_scrolling() {
        let mut app = App::new(true, None, "https://api.owaspblt.org".to_string());
        let total_issues = app.issues.len();
        
        // Assert initial selected row
        assert_eq!(app.selected_issue_index, 0);

        // Scroll down
        app.scroll_down();
        assert_eq!(app.selected_issue_index, 1);

        // Scroll up
        app.scroll_up();
        assert_eq!(app.selected_issue_index, 0);

        // Scroll up loops to the end
        app.scroll_up();
        assert_eq!(app.selected_issue_index, total_issues - 1);

        // Scroll down loops to the start
        app.scroll_down();
        assert_eq!(app.selected_issue_index, 0);
    }

    #[test]
    fn test_modal_toggles() {
        let mut app = App::new(true, None, "https://api.owaspblt.org".to_string());
        assert!(!app.show_help);

        // Help popup toggle
        app.toggle_help();
        assert!(app.show_help);
        app.toggle_help();
        assert!(!app.show_help);

        // Help should not switch tabs
        app.toggle_help();
        app.next_tab();
        assert_eq!(app.active_tab, Tab::Issues);
        app.close_popups();
        assert!(!app.show_help);
    }

    #[test]
    fn test_triage_confirmation_flow() {
        let mut app = App::new(true, None, "https://api.owaspblt.org".to_string());
        
        // Triage modal triggers
        app.trigger_triage();
        assert!(app.show_triage_modal);

        let initial_status = app.issues[0].status.clone();
        assert_ne!(initial_status, "In Review");
        let initial_comments_len = app.issues[0].comments.len();

        // Confirming triage sets status and appends comment
        app.confirm_triage();
        assert!(!app.show_triage_modal);
        assert_eq!(app.issues[0].status, "In Review");
        assert_eq!(app.issues[0].comments.len(), initial_comments_len + 1);
        assert!(app.issues[0].comments.last().unwrap().contains("Manually confirmed"));
    }
}
