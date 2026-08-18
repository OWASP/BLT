//! System Configurations, Connection Parameters, and Host Security Scanners (Tab 5).
//!
//! This module displays the active CLI execution mode, backend API endpoints,
//! MCP subprocess paths, authenticated user identity, and local host security scan results.
//!
//! Key Components & Functions:
//! - `draw_settings_tab(f, app, rect)`: Renders a 2-column layout showing runtime configuration
//!   on the left and the local security scanner status (Trivy, Semgrep, Bandit) on the right.

use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Modifier, Style, Stylize},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};

use crate::app::{App, RunMode};
use crate::ui::theme::{
    BLT_PRIMARY, BLT_TEXT_BODY, BLT_TEXT_DIM, BLT_TEXT_HEADING, BLT_TEXT_MUTED, DARK_BORDER,
    DARK_SURFACE, SEVERITY_CRITICAL, STATUS_PENDING, STATUS_RESOLVED,
};

/// Renders the configuration and host security scanner dashboard tab.
pub fn draw_settings_tab(f: &mut Frame, app: &App, rect: Rect) {
    let chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(50), Constraint::Percentage(50)])
        .split(rect);

    let mode_str = match app.run_mode {
        RunMode::Live => "Live REST API Mode",
        RunMode::Mcp => "MCP Subprocess Agent Mode",
    };

    let settings_text = vec![
        Line::from(""),
        Line::from(vec![
            Span::styled(
                "  Execution Mode:     ",
                Style::default().fg(BLT_TEXT_MUTED),
            ),
            Span::styled(
                mode_str,
                Style::default()
                    .fg(BLT_PRIMARY)
                    .add_modifier(Modifier::BOLD),
            ),
        ]),
        Line::from(vec![
            Span::styled(
                "  Target BLT API:     ",
                Style::default().fg(BLT_TEXT_MUTED),
            ),
            Span::styled(&app.api_base, Style::default().fg(BLT_TEXT_BODY)),
        ]),
        Line::from(vec![
            Span::styled(
                "  MCP Server Path:    ",
                Style::default().fg(BLT_TEXT_MUTED),
            ),
            Span::styled(
                app.mcp_path.as_deref().unwrap_or("None (Not spawned)"),
                Style::default().fg(BLT_TEXT_DIM),
            ),
        ]),
        Line::from(vec![
            Span::styled(
                "  Authenticated User: ",
                Style::default().fg(BLT_TEXT_MUTED),
            ),
            Span::styled(
                &app.auth_user,
                Style::default()
                    .fg(BLT_TEXT_HEADING)
                    .add_modifier(Modifier::BOLD),
            ),
        ]),
        Line::from(""),
        Line::from(Span::styled(
            "  Launch Options:",
            Style::default()
                .fg(BLT_TEXT_HEADING)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from(Span::styled(
            "  - REST API:   blt-cli --api-base <url>",
            Style::default().fg(BLT_TEXT_MUTED),
        )),
        Line::from(Span::styled(
            "  - MCP Server: blt-cli --mcp-path <path_to_server>",
            Style::default().fg(BLT_TEXT_MUTED),
        )),
        Line::from(""),
        Line::from(Span::styled(
            "  Session Persistence: Synced to blt_session.json",
            Style::default().fg(BLT_TEXT_DIM),
        )),
    ];

    let p = Paragraph::new(settings_text).block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(DARK_BORDER))
            .title(Span::styled(
                " CONFIGURATION ",
                Style::default()
                    .fg(BLT_TEXT_HEADING)
                    .add_modifier(Modifier::BOLD),
            ))
            .bg(DARK_SURFACE),
    );
    f.render_widget(p, chunks[0]);

    // Local Security Health Scan
    let mut health_text = vec![Line::from("")];
    if let Some(health) = &app.security_health {
        let status_to_span = |s: &crate::scanner::ToolStatus| match s {
            crate::scanner::ToolStatus::Pending => {
                Span::styled("Scanning...", Style::default().fg(STATUS_PENDING))
            }
            crate::scanner::ToolStatus::Missing => {
                Span::styled("Not Installed", Style::default().fg(BLT_TEXT_DIM))
            }
            crate::scanner::ToolStatus::Skipped => {
                Span::styled("Skipped", Style::default().fg(BLT_TEXT_DIM))
            }
            crate::scanner::ToolStatus::Error(e) => Span::styled(
                format!("Error: {}", e),
                Style::default().fg(SEVERITY_CRITICAL),
            ),
            crate::scanner::ToolStatus::Success => {
                Span::styled("Operational", Style::default().fg(STATUS_RESOLVED))
            }
        };

        health_text.push(Line::from(vec![
            Span::styled("  Trivy:   ", Style::default().fg(BLT_TEXT_MUTED)),
            status_to_span(&health.trivy_status),
        ]));
        health_text.push(Line::from(vec![
            Span::styled("  Semgrep: ", Style::default().fg(BLT_TEXT_MUTED)),
            status_to_span(&health.semgrep_status),
        ]));
        health_text.push(Line::from(vec![
            Span::styled("  Bandit:  ", Style::default().fg(BLT_TEXT_MUTED)),
            status_to_span(&health.bandit_status),
        ]));
        health_text.push(Line::from(""));

        let all_success = health.trivy_status == crate::scanner::ToolStatus::Success
            && health.semgrep_status == crate::scanner::ToolStatus::Success
            && health.bandit_status == crate::scanner::ToolStatus::Success;

        if health.findings.is_empty() && health.scan_complete && all_success {
            health_text.push(Line::from(Span::styled(
                "  Host Health: PASS (Zero findings detected)",
                Style::default()
                    .fg(STATUS_RESOLVED)
                    .add_modifier(Modifier::BOLD),
            )));
        } else if health.findings.is_empty() && health.scan_complete {
            health_text.push(Line::from(Span::styled(
                "  Host Health: INCOMPLETE",
                Style::default()
                    .fg(BLT_TEXT_DIM)
                    .add_modifier(Modifier::BOLD),
            )));
        } else if !health.findings.is_empty() {
            health_text.push(Line::from(Span::styled(
                format!(
                    "  Host Health: WARNING ({} findings)",
                    health.findings.len()
                ),
                Style::default()
                    .fg(SEVERITY_CRITICAL)
                    .add_modifier(Modifier::BOLD),
            )));
            for finding in health.findings.iter().take(8) {
                health_text.push(Line::from(format!("   • {}", finding)));
            }
        }
    } else {
        health_text.push(Line::from(Span::styled(
            "  Initializing security scan...",
            Style::default().fg(BLT_TEXT_MUTED),
        )));
    }

    let h = Paragraph::new(health_text).block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(DARK_BORDER))
            .title(Span::styled(
                " LOCAL SCANNER HEALTH ",
                Style::default().fg(BLT_TEXT_MUTED),
            ))
            .bg(DARK_SURFACE),
    );
    f.render_widget(h, chunks[1]);
}
