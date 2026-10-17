//! User Interface Rendering and Layout Engine for OWASP BLT CLI.
//!
//! This module coordinates the entire drawing pipeline for the Ratatui-based
//! terminal client. It splits the screen into header, main workspace, and footer,
//! dispatches tab views, and renders centered overlay modals.
//!
//! Module Structure:
//! - `theme`: Color tokens adhering to official OWASP BLT Foundations.
//! - `widgets`: Layout centering (`centered_rect`) and generic `Cell` conversion traits.
//! - `markdown`: Multi-line and inline bold markdown syntax highlighters.
//! - `header`: Top brand header, connection status pill, real-time counters, and tabs.
//! - `footer`: Bottom status bar and interactive keyboard shortcut toolbar.
//! - `tabs`: Submodules for each view (Issues, Hunts, Stats, Logs, Settings).
//! - `modals`: Centered dialog overlays and forms.
//!
//! Key Functions:
//! - `draw(frame, app)`: Root rendering function called on each terminal tick.

pub mod footer;
pub mod header;
pub mod markdown;
pub mod modals;
pub mod tabs;
pub mod theme;
pub mod widgets;

use ratatui::{
    layout::{Constraint, Direction, Layout},
    style::Stylize,
    widgets::Block,
    Frame,
};

use crate::app::{App, Tab};
use footer::draw_footer;
use header::draw_header;
use modals::*;
use tabs::{draw_hunts_tab, draw_issues_tab, draw_logs_tab, draw_settings_tab, draw_stats_tab};
use theme::DARK_BASE;

/// Root rendering method. Sets the viewport canvas background, splits layout,
/// renders active tab content, footer status bar, and active modal overlays.
pub fn draw(f: &mut Frame, app: &mut App) {
    // Fill entire terminal viewport with official Dark Base (#0D0F12)
    let bg_block = Block::default().bg(DARK_BASE);
    f.render_widget(bg_block, f.area());

    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(4), // Header + Live Telemetry + Nav Tabs
            Constraint::Min(10),   // Active Tab Canvas
            Constraint::Length(3), // Status Bar & Footer
        ])
        .split(f.area());

    // 1. Top Header & Navigation
    draw_header(f, app, chunks[0]);

    // 2. Active Tab View
    match app.active_tab {
        Tab::Issues => draw_issues_tab(f, app, chunks[1]),
        Tab::Hunts => draw_hunts_tab(f, app, chunks[1]),
        Tab::Stats => draw_stats_tab(f, app, chunks[1]),
        Tab::Logs => draw_logs_tab(f, app, chunks[1]),
        Tab::Settings => draw_settings_tab(f, app, chunks[1]),
    }

    // 3. Status Bar & Keybinding Guide
    draw_footer(f, app, chunks[2]);

    // 4. Modal Overlays
    match app.active_overlay {
        crate::app::ActiveOverlay::Help => draw_help_modal(f, chunks[1]),
        crate::app::ActiveOverlay::Triage => draw_triage_modal(f, app, chunks[1]),
        crate::app::ActiveOverlay::SubmitForm => draw_submit_form_modal(f, app, chunks[1]),
        crate::app::ActiveOverlay::HuntDetail => draw_hunt_details_modal(f, app, chunks[1]),
        crate::app::ActiveOverlay::AiTriage => draw_ai_triage_modal(f, app, chunks[1]),
        crate::app::ActiveOverlay::BulkTriageConfirm => draw_bulk_triage_modal(f, app, chunks[1]),
        crate::app::ActiveOverlay::AgentStatus => draw_agent_status_modal(f, app, chunks[1]),
        crate::app::ActiveOverlay::PromptPreview => draw_prompt_preview_modal(f, app, chunks[1]),
        crate::app::ActiveOverlay::EasterEgg => draw_easter_egg_modal(f, chunks[1]),
        crate::app::ActiveOverlay::VisionContext => draw_vision_context_modal(f, app, chunks[1]),
        _ => {}
    }
}
