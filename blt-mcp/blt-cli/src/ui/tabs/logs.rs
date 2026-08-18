//! Audit Trail and Real-Time Event Stream View (Tab 4).
//!
//! This module renders security audit logs with severity color tags
//! and the real-time event feed for live operational monitoring.
//!
//! Key Components & Functions:
//! - `draw_logs_tab(f, app, rect)`: Renders the 2-row layout splitting the screen
//!   between the persistent audit trail (with export capability) and the live event stream.

use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Modifier, Style, Stylize},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem},
    Frame,
};

use crate::app::App;
use crate::ui::theme::{
    BLT_PRIMARY, BLT_TEXT_BODY, BLT_TEXT_HEADING, DARK_BORDER, DARK_SURFACE, SEVERITY_CRITICAL,
    SEVERITY_HIGH, STATUS_IN_REVIEW, STATUS_RESOLVED,
};

/// Renders the persistent audit log list and real-time event telemetry feed.
pub fn draw_logs_tab(f: &mut Frame, app: &App, rect: Rect) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(50), Constraint::Percentage(50)])
        .split(rect);

    // Audit Trail List
    let audit_items: Vec<ListItem> = app
        .audit_logs
        .iter()
        .map(|log| {
            let (tag, color) = if log.contains("Critical") || log.contains("ERROR") {
                ("[ALRT]", SEVERITY_CRITICAL)
            } else if log.contains("Warn") || log.contains("High") {
                ("[WARN]", SEVERITY_HIGH)
            } else if log.contains("Bacon") || log.contains("Verified") {
                ("[AUTH]", STATUS_RESOLVED)
            } else {
                ("[INFO]", STATUS_IN_REVIEW)
            };

            ListItem::new(Line::from(vec![
                Span::styled(
                    format!("{} ", tag),
                    Style::default().fg(color).add_modifier(Modifier::BOLD),
                ),
                Span::styled(log, Style::default().fg(BLT_TEXT_BODY)),
            ]))
        })
        .collect();

    let audit_list = List::new(audit_items).block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(DARK_BORDER))
            .title(Span::styled(
                " AUDIT LOG (Press [e] to Export) ",
                Style::default()
                    .fg(BLT_TEXT_HEADING)
                    .add_modifier(Modifier::BOLD),
            ))
            .bg(DARK_SURFACE),
    );
    f.render_widget(audit_list, chunks[0]);

    // Real-Time Event Feed
    let event_items: Vec<ListItem> = app
        .event_feed
        .iter()
        .map(|ev| {
            ListItem::new(Line::from(vec![
                Span::styled(
                    "[EVENT] ",
                    Style::default()
                        .fg(BLT_PRIMARY)
                        .add_modifier(Modifier::BOLD),
                ),
                Span::styled(ev, Style::default().fg(BLT_TEXT_BODY)),
            ]))
        })
        .collect();

    let event_list = List::new(event_items).block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(DARK_BORDER))
            .title(Span::styled(
                " EVENT FEED ",
                Style::default()
                    .fg(BLT_TEXT_HEADING)
                    .add_modifier(Modifier::BOLD),
            ))
            .bg(DARK_SURFACE),
    );
    f.render_widget(event_list, chunks[1]);
}
