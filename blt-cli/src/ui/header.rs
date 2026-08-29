//! Brand Header, Live Telemetry Counters, and Navigation Tabs.
//!
//! This module renders the top header bar of the OWASP BLT TUI dashboard.
//! It includes brand identity typography, live MCP / REST mode status indicators,
//! real-time vulnerability summary counters, and interactive navigation tab buttons.
//!
//! Key Components & Functions:
//! - `draw_header(f, app, rect)`: Main entry point for drawing the 2-column header layout.
//!   - Left column (52 chars): Brand title ("OWASP BLT v1.0"), active execution mode badge
//!     ("● MCP Mode" or "● Live Mode"), current authenticated user, and live issue counters
//!     (Open, Critical, High).
//!   - Right column: Interactive navigation tabs with shortcut markers ([1] Issues, [2] Hunts,
//!     [3] Stats, [4] Logs, [5] Config) styled with official `#E10101` active highlighting.

use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Modifier, Style, Stylize},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph, Tabs},
    Frame,
};

use super::theme::{
    BLT_PRIMARY, BLT_TEXT_DIM, BLT_TEXT_HEADING, BLT_TEXT_MUTED, DARK_BORDER, DARK_SURFACE,
    SEVERITY_CRITICAL, SEVERITY_HIGH, STATUS_IN_REVIEW, STATUS_RESOLVED,
};
use crate::app::{App, Tab};

/// Renders the top brand header, live connection state, counters, and navigation tabs.
pub fn draw_header(f: &mut Frame, app: &App, rect: Rect) {
    let header_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Length(52), // Brand Logo + User + Live Telemetry
            Constraint::Min(30),    // Navigation Tabs with Hotkeys
        ])
        .split(rect);

    let (mode_badge, mode_color) = if app.run_mode == crate::app::RunMode::Mcp {
        ("● MCP Mode", STATUS_RESOLVED)
    } else {
        ("● Live Mode", STATUS_IN_REVIEW)
    };

    let open_count = app
        .issues
        .iter()
        .filter(|i| !i.status.eq_ignore_ascii_case("resolved"))
        .count();
    let crit_count = app
        .issues
        .iter()
        .filter(|i| i.severity.eq_ignore_ascii_case("critical"))
        .count();
    let high_count = app
        .issues
        .iter()
        .filter(|i| i.severity.eq_ignore_ascii_case("high"))
        .count();

    let header_lines = vec![
        Line::from(vec![
            Span::styled(
                " OWASP BLT ",
                Style::default()
                    .fg(BLT_TEXT_HEADING)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::styled("v1.0 ", Style::default().fg(BLT_TEXT_DIM)),
            Span::styled("│ ", Style::default().fg(DARK_BORDER)),
            Span::styled(
                format!("{} ", mode_badge),
                Style::default().fg(mode_color).add_modifier(Modifier::BOLD),
            ),
            Span::styled("│ ", Style::default().fg(DARK_BORDER)),
            Span::styled("User: ", Style::default().fg(BLT_TEXT_MUTED)),
            Span::styled(
                &app.auth_user,
                Style::default()
                    .fg(BLT_TEXT_HEADING)
                    .add_modifier(Modifier::BOLD),
            ),
        ]),
        Line::from(vec![
            Span::styled(" ", Style::default()),
            Span::styled(
                format!("Open: {} ", open_count),
                Style::default().fg(BLT_TEXT_MUTED),
            ),
            Span::styled("│ ", Style::default().fg(DARK_BORDER)),
            Span::styled(
                format!("Critical: {} ", crit_count),
                Style::default()
                    .fg(SEVERITY_CRITICAL)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::styled("│ ", Style::default().fg(DARK_BORDER)),
            Span::styled(
                format!("High: {} ", high_count),
                Style::default()
                    .fg(SEVERITY_HIGH)
                    .add_modifier(Modifier::BOLD),
            ),
        ]),
    ];

    let header_block = Block::default()
        .borders(Borders::BOTTOM)
        .border_style(Style::default().fg(DARK_BORDER))
        .bg(DARK_SURFACE);

    let title_widget = Paragraph::new(header_lines).block(header_block);
    f.render_widget(title_widget, header_chunks[0]);

    // Navigation Tabs with Official BLT Red for Active State
    let tab_titles = vec![
        format!(" [1] Issues ({}) ", app.issues.len()),
        format!(" [2] Hunts ({}) ", app.hunts.len()),
        " [3] Stats ".to_string(),
        " [4] Logs ".to_string(),
        " [5] Config ".to_string(),
    ];

    let tab_index = match app.active_tab {
        Tab::Issues => 0,
        Tab::Hunts => 1,
        Tab::Stats => 2,
        Tab::Logs => 3,
        Tab::Settings => 4,
    };

    let tabs_block = Block::default()
        .borders(Borders::BOTTOM)
        .border_style(Style::default().fg(DARK_BORDER))
        .bg(DARK_SURFACE);

    let tabs = Tabs::new(tab_titles)
        .select(tab_index)
        .block(tabs_block)
        .style(Style::default().fg(BLT_TEXT_MUTED))
        .highlight_style(
            Style::default()
                .fg(BLT_TEXT_HEADING)
                .bg(BLT_PRIMARY)
                .add_modifier(Modifier::BOLD),
        )
        .divider(Span::styled("│", Style::default().fg(DARK_BORDER)));

    f.render_widget(tabs, header_chunks[1]);
}
