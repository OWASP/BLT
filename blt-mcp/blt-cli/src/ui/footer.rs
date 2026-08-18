//! Status Bar and Interactive Keyboard Shortcuts Legend Footer.
//!
//! This module renders the persistent footer spanning the bottom of the TUI.
//! It displays the operational mode badge, real-time status message marquee,
//! and contextual keyboard shortcut hints based on the active tab and overlay.
//!
//! Key Components & Functions:
//! - `draw_footer(f, app, rect)`: Renders the 3-column footer bar:
//!   - Left pill (14 chars): Execution mode badge ("MCP" or "LIVE") in high-contrast styling.
//!   - Center area (42% width): Live status messages and asynchronous task completion alerts.
//!   - Right area (fill): Contextual hotkey reference legend dynamically adapted to the active tab.

use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Modifier, Style, Stylize},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};

use crate::app::{App, Tab};
use super::theme::{
    BLT_PRIMARY, BLT_TEXT_BODY, BLT_TEXT_HEADING, BLT_TEXT_MUTED, DARK_BORDER, DARK_SURFACE,
    SEVERITY_CRITICAL, SEVERITY_HIGH, STATUS_IN_REVIEW, STATUS_RESOLVED,
};

/// Renders the bottom status bar, mode indicator, and action shortcut legend.
pub fn draw_footer(f: &mut Frame, app: &App, rect: Rect) {
    let footer_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Length(14),     // Mode Pill
            Constraint::Percentage(42), // Status Message
            Constraint::Fill(1),        // Shortcut Toolbar
        ])
        .split(rect);

    let (mode_label, mode_bg) = match app.run_mode {
        crate::app::RunMode::Live => (" LIVE ", STATUS_IN_REVIEW),
        crate::app::RunMode::Mcp => (" MCP ", BLT_PRIMARY),
    };

    let left = Paragraph::new(Line::from(vec![
        Span::styled(" ", Style::default()),
        Span::styled(
            mode_label,
            Style::default()
                .fg(BLT_TEXT_HEADING)
                .bg(mode_bg)
                .add_modifier(Modifier::BOLD),
        ),
    ]))
    .block(
        Block::default()
            .borders(Borders::TOP)
            .border_style(Style::default().fg(DARK_BORDER))
            .bg(DARK_SURFACE),
    );
    f.render_widget(left, footer_chunks[0]);

    let middle = Paragraph::new(Span::styled(
        format!(" {}", app.status_message),
        Style::default().fg(BLT_TEXT_BODY),
    ))
    .block(
        Block::default()
            .borders(Borders::TOP)
            .border_style(Style::default().fg(DARK_BORDER))
            .bg(DARK_SURFACE),
    );
    f.render_widget(middle, footer_chunks[1]);

    let mut legend_spans = vec![
        Span::styled(
            "[Tab] ",
            Style::default()
                .fg(BLT_PRIMARY)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled("Nav ", Style::default().fg(BLT_TEXT_MUTED)),
        Span::styled(
            "[↑↓] ",
            Style::default()
                .fg(BLT_PRIMARY)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled("Scroll ", Style::default().fg(BLT_TEXT_MUTED)),
    ];

    match app.active_tab {
        Tab::Issues => {
            legend_spans.extend(vec![
                Span::styled(
                    "[Space] ",
                    Style::default()
                        .fg(BLT_PRIMARY)
                        .add_modifier(Modifier::BOLD),
                ),
                Span::styled("Sel ", Style::default().fg(BLT_TEXT_MUTED)),
                Span::styled(
                    "[t] ",
                    Style::default()
                        .fg(SEVERITY_HIGH)
                        .add_modifier(Modifier::BOLD),
                ),
                Span::styled("Triage ", Style::default().fg(BLT_TEXT_MUTED)),
                Span::styled(
                    "[a] ",
                    Style::default()
                        .fg(STATUS_IN_REVIEW)
                        .add_modifier(Modifier::BOLD),
                ),
                Span::styled("AI ", Style::default().fg(BLT_TEXT_MUTED)),
            ]);
        }
        Tab::Hunts => {
            legend_spans.extend(vec![
                Span::styled(
                    "[Enter] ",
                    Style::default()
                        .fg(BLT_PRIMARY)
                        .add_modifier(Modifier::BOLD),
                ),
                Span::styled("Details ", Style::default().fg(BLT_TEXT_MUTED)),
            ]);
        }
        Tab::Logs => {
            legend_spans.extend(vec![
                Span::styled(
                    "[e] ",
                    Style::default()
                        .fg(BLT_PRIMARY)
                        .add_modifier(Modifier::BOLD),
                ),
                Span::styled("Export ", Style::default().fg(BLT_TEXT_MUTED)),
            ]);
        }
        _ => {}
    }

    legend_spans.extend(vec![
        Span::styled(
            "[s] ",
            Style::default()
                .fg(STATUS_RESOLVED)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled("Report ", Style::default().fg(BLT_TEXT_MUTED)),
        Span::styled(
            "[p] ",
            Style::default()
                .fg(STATUS_IN_REVIEW)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled("Vision ", Style::default().fg(BLT_TEXT_MUTED)),
        Span::styled(
            "[?] ",
            Style::default()
                .fg(BLT_PRIMARY)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled("Help ", Style::default().fg(BLT_TEXT_MUTED)),
        Span::styled(
            "[q] ",
            Style::default()
                .fg(SEVERITY_CRITICAL)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled("Quit", Style::default().fg(BLT_TEXT_MUTED)),
    ]);

    let right = Paragraph::new(Line::from(legend_spans))
        .alignment(ratatui::layout::Alignment::Right)
        .block(
            Block::default()
                .borders(Borders::TOP)
                .border_style(Style::default().fg(DARK_BORDER))
                .bg(DARK_SURFACE),
        );
    f.render_widget(right, footer_chunks[2]);
}
