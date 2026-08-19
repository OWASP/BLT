//! Dashboard Tab Renderers for the OWASP BLT CLI.
//!
//! Submodules:
//! - `issues`: Vulnerabilities list & triage inspector (Tab 1).
//! - `hunts`: Active bounty hunts & program scopes (Tab 2).
//! - `stats`: Authentic metrics, BarChart, and hacker leaderboard (Tab 3).
//! - `logs`: Audit log stream and real-time event feed (Tab 4).
//! - `settings`: System configuration and host security scanner (Tab 5).

pub mod hunts;
pub mod issues;
pub mod logs;
pub mod settings;
pub mod stats;

pub use hunts::draw_hunts_tab;
pub use issues::draw_issues_tab;
pub use logs::draw_logs_tab;
pub use settings::draw_settings_tab;
pub use stats::draw_stats_tab;
