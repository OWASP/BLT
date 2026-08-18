//! Vulnerabilities and Interactive Triage Dashboard View (Tab 1).
//!
//! This module renders the primary Vulnerabilities view of the OWASP BLT TUI.
//! It provides an interactive, searchable vulnerability table with bulk selection support,
//! coupled with a comprehensive real-time metadata inspector and activity audit timeline.
//!
//! Key Components & Functions:
//! - `draw_issues_tab(f, app, rect)`: Main drawing function for Tab 1:
//!   - Filter Header: Inline query input bar activated with `/` key.
//!   - Left Column (46%): Scrollable vulnerability table with selection indicators (`▎`),
//!     checkbox toggles (`[✓]`), severity badges (Critical, High, Medium, Low),
//!     status badges (Resolved, In Review, Pending), target host URL, and issue title.
//!   - Right Column (54%): 3-tier inspection view:
//!     1. Metadata Card: ID, target URL, reporter username, severity, status, and action hotkeys.
//!     2. Technical Description: Full PoC details and advisory text.
//!     3. Activity Log & Audit Trail: Comment history and audit events.

use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Modifier, Style, Stylize},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph, Row, Table, Wrap},
    Frame,
};

use crate::app::App;
use crate::ui::theme::{
    BLT_PRIMARY, BLT_TEXT_BODY, BLT_TEXT_DIM, BLT_TEXT_HEADING, BLT_TEXT_MUTED, DARK_BASE,
    DARK_BORDER, DARK_CARD_SELECTED, DARK_SURFACE, DARK_SURFACE_ALT, SEVERITY_CRITICAL,
    SEVERITY_HIGH, SEVERITY_LOW, SEVERITY_MEDIUM, STATUS_IN_REVIEW, STATUS_PENDING,
    STATUS_RESOLVED,
};
use crate::ui::widgets::Cell;

/// Draws the main vulnerability table and side inspector panel.
pub fn draw_issues_tab(f: &mut Frame, app: &App, rect: Rect) {
    let mut main_rect = rect;

    // Inline Filter Bar
    if app.active_overlay == crate::app::ActiveOverlay::SearchInput || !app.search_query.is_empty()
    {
        let search_layout = Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Length(3), Constraint::Min(0)])
            .split(rect);

        let prefix = if app.active_overlay == crate::app::ActiveOverlay::SearchInput {
            " Filter > "
        } else {
            " Filter: "
        };
        let border_style = if app.active_overlay == crate::app::ActiveOverlay::SearchInput {
            Style::default().fg(BLT_PRIMARY).add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(DARK_BORDER)
        };

        let search_p = Paragraph::new(Line::from(vec![
            Span::styled(
                prefix,
                Style::default()
                    .fg(BLT_PRIMARY)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::styled(
                &app.search_query,
                Style::default()
                    .fg(BLT_TEXT_HEADING)
                    .add_modifier(Modifier::BOLD),
            ),
            if app.active_overlay == crate::app::ActiveOverlay::SearchInput {
                Span::styled("█", Style::default().fg(BLT_PRIMARY))
            } else {
                Span::raw("")
            },
            Span::styled("  (Press [Esc] to reset)", Style::default().fg(BLT_TEXT_DIM)),
        ]))
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(border_style)
                .title(Span::styled(
                    " SEARCH FILTER ",
                    Style::default().fg(BLT_TEXT_MUTED),
                ))
                .bg(DARK_SURFACE),
        );

        f.render_widget(search_p, search_layout[0]);
        main_rect = search_layout[1];
    }

    let horizontal_layout = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(46), Constraint::Percentage(54)])
        .split(main_rect);

    if app.issues.is_empty() {
        let empty_msg = Paragraph::new(vec![
            Line::from(""),
            Line::from(""),
            Line::from(Span::styled(
                "No active vulnerability reports found.",
                Style::default()
                    .fg(BLT_TEXT_MUTED)
                    .add_modifier(Modifier::BOLD),
            )),
            Line::from(""),
            Line::from(Span::styled(
                "Press [s] to report a vulnerability or [p] to paste a screenshot.",
                Style::default().fg(BLT_TEXT_DIM),
            )),
        ])
        .alignment(ratatui::layout::Alignment::Center)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(DARK_BORDER))
                .title(Span::styled(
                    " VULNERABILITIES ",
                    Style::default()
                        .fg(BLT_TEXT_HEADING)
                        .add_modifier(Modifier::BOLD),
                ))
                .bg(DARK_SURFACE),
        );
        f.render_widget(empty_msg, horizontal_layout[0]);
    } else {
        // Table Header
        let header_cells = vec!["SEL", "ID", "SEVERITY", "STATUS", "TARGET", "TITLE"];
        let header = Row::new(header_cells)
            .style(
                Style::default()
                    .fg(BLT_TEXT_MUTED)
                    .bg(DARK_SURFACE_ALT)
                    .add_modifier(Modifier::BOLD),
            )
            .bottom_margin(0);

        let rows = app.issues.iter().enumerate().filter_map(|(idx, issue)| {
            if !app.search_query.is_empty() {
                let q = app.search_query.to_lowercase();
                if !issue.title.to_lowercase().contains(&q)
                    && !issue.url.to_lowercase().contains(&q)
                    && !issue.status.to_lowercase().contains(&q)
                    && !issue.severity.to_lowercase().contains(&q)
                    && !issue.id.to_lowercase().contains(&q)
                {
                    return None;
                }
            }

            let is_selected = idx == app.selected_issue_index;
            let is_checked = app.selected_issues.contains(&issue.id);

            let (sev_badge, sev_color) = match issue.severity.to_lowercase().as_str() {
                "critical" => ("Critical", SEVERITY_CRITICAL),
                "high" => ("High", SEVERITY_HIGH),
                "medium" => ("Medium", SEVERITY_MEDIUM),
                _ => ("Low", SEVERITY_LOW),
            };

            let (status_badge, status_color) = match issue.status.to_lowercase().as_str() {
                "resolved" => ("Resolved", STATUS_RESOLVED),
                "in review" | "triaged" | "validated" => ("In Review", STATUS_IN_REVIEW),
                "closed" => ("Closed", BLT_TEXT_DIM),
                _ => ("Pending", STATUS_PENDING),
            };

            let check_mark = if is_checked {
                Span::styled(
                    "[✓] ",
                    Style::default()
                        .fg(BLT_PRIMARY)
                        .add_modifier(Modifier::BOLD),
                )
            } else {
                Span::styled("[ ] ", Style::default().fg(BLT_TEXT_DIM))
            };

            let row_selector = if is_selected {
                Span::styled(
                    "▎",
                    Style::default()
                        .fg(BLT_PRIMARY)
                        .add_modifier(Modifier::BOLD),
                )
            } else {
                Span::raw(" ")
            };

            let id_display = format!("#{}", issue.id);

            let clean_url = issue
                .url
                .trim_start_matches("https://")
                .trim_start_matches("http://");
            let truncated_url = if clean_url.chars().count() > 14 {
                format!("{}…", clean_url.chars().take(13).collect::<String>())
            } else {
                clean_url.to_string()
            };

            let truncated_title = if issue.title.chars().count() > 22 {
                format!("{}…", issue.title.chars().take(21).collect::<String>())
            } else {
                issue.title.clone()
            };

            let cells = vec![
                Cell::from(Line::from(vec![row_selector, check_mark])),
                Cell::from(Span::styled(
                    id_display,
                    Style::default()
                        .fg(BLT_TEXT_BODY)
                        .add_modifier(Modifier::BOLD),
                )),
                Cell::from(Span::styled(
                    sev_badge,
                    Style::default().fg(sev_color).add_modifier(Modifier::BOLD),
                )),
                Cell::from(Span::styled(
                    status_badge,
                    Style::default().fg(status_color),
                )),
                Cell::from(Span::styled(
                    truncated_url,
                    Style::default().fg(BLT_TEXT_MUTED),
                )),
                Cell::from(Span::styled(
                    truncated_title,
                    if is_selected {
                        Style::default()
                            .fg(BLT_TEXT_HEADING)
                            .add_modifier(Modifier::BOLD)
                    } else {
                        Style::default().fg(BLT_TEXT_BODY)
                    },
                )),
            ];

            let row_style = if is_selected {
                Style::default().bg(DARK_CARD_SELECTED)
            } else if idx % 2 == 0 {
                Style::default().bg(DARK_SURFACE)
            } else {
                Style::default().bg(DARK_BASE)
            };

            Some(Row::new(cells).style(row_style))
        });

        let table = Table::new(
            rows,
            [
                Constraint::Length(6),
                Constraint::Length(7),
                Constraint::Length(10),
                Constraint::Length(12),
                Constraint::Length(16),
                Constraint::Fill(1),
            ],
        )
        .header(header)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(DARK_BORDER))
                .title(Span::styled(
                    " VULNERABILITIES ",
                    Style::default()
                        .fg(BLT_TEXT_HEADING)
                        .add_modifier(Modifier::BOLD),
                ))
                .bg(DARK_SURFACE),
        )
        .column_spacing(1);

        f.render_widget(table, horizontal_layout[0]);
    }

    // 2. Right Pane: Vulnerability Inspector & Activity Timeline
    if !app.issues.is_empty() {
        let issue = &app.issues[app.selected_issue_index];
        let right_pane_chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(6), // Metadata Card
                Constraint::Percentage(52), // Description
                Constraint::Percentage(48), // Activity Log & Audit Trail
            ])
            .split(horizontal_layout[1]);

        let (sev_badge, sev_color) = match issue.severity.to_lowercase().as_str() {
            "critical" => ("Critical", SEVERITY_CRITICAL),
            "high" => ("High", SEVERITY_HIGH),
            "medium" => ("Medium", SEVERITY_MEDIUM),
            _ => ("Low", SEVERITY_LOW),
        };

        // Top Metadata Card
        let meta_lines = vec![
            Line::from(vec![
                Span::styled(
                    format!("#{}  ", issue.id),
                    Style::default()
                        .fg(BLT_PRIMARY)
                        .add_modifier(Modifier::BOLD),
                ),
                Span::styled(
                    &issue.title,
                    Style::default()
                        .fg(BLT_TEXT_HEADING)
                        .add_modifier(Modifier::BOLD),
                ),
            ]),
            Line::from(vec![
                Span::styled("Target URL: ", Style::default().fg(BLT_TEXT_MUTED)),
                Span::styled(&issue.url, Style::default().fg(BLT_TEXT_BODY)),
                Span::styled("  │  Reporter: ", Style::default().fg(BLT_TEXT_MUTED)),
                Span::styled(
                    format!("@{}", issue.author),
                    Style::default().fg(BLT_TEXT_BODY),
                ),
            ]),
            Line::from(vec![
                Span::styled("Severity:   ", Style::default().fg(BLT_TEXT_MUTED)),
                Span::styled(
                    sev_badge,
                    Style::default().fg(sev_color).add_modifier(Modifier::BOLD),
                ),
                Span::styled("  │  Status: ", Style::default().fg(BLT_TEXT_MUTED)),
                Span::styled(
                    &issue.status,
                    Style::default()
                        .fg(if issue.status.eq_ignore_ascii_case("resolved") {
                            STATUS_RESOLVED
                        } else {
                            STATUS_PENDING
                        })
                        .add_modifier(Modifier::BOLD),
                ),
            ]),
            Line::from(vec![
                Span::styled("Actions:    ", Style::default().fg(BLT_TEXT_MUTED)),
                Span::styled(
                    "[t] Triage  [a] AI Analysis  [Space] Select",
                    Style::default().fg(BLT_TEXT_DIM),
                ),
            ]),
        ];

        let meta_p = Paragraph::new(meta_lines).block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(DARK_BORDER))
                .title(Span::styled(
                    " OVERVIEW ",
                    Style::default()
                        .fg(BLT_TEXT_HEADING)
                        .add_modifier(Modifier::BOLD),
                ))
                .bg(DARK_SURFACE),
        );
        f.render_widget(meta_p, right_pane_chunks[0]);

        // Description Body
        let mut desc_lines = vec![
            Line::from(Span::styled(
                "Technical Description:",
                Style::default()
                    .fg(BLT_TEXT_HEADING)
                    .add_modifier(Modifier::BOLD),
            )),
            Line::from(""),
        ];

        for line in issue.description.lines() {
            desc_lines.push(Line::from(Span::styled(
                format!("  {}", line),
                Style::default().fg(BLT_TEXT_BODY),
            )));
        }

        let desc_p = Paragraph::new(desc_lines)
            .block(
                Block::default()
                    .borders(Borders::ALL)
                    .border_style(Style::default().fg(DARK_BORDER))
                    .title(Span::styled(
                        " DETAILS ",
                        Style::default().fg(BLT_TEXT_MUTED),
                    ))
                    .bg(DARK_SURFACE),
            )
            .wrap(Wrap { trim: false });
        f.render_widget(desc_p, right_pane_chunks[1]);

        // Activity & Comment Timeline
        let mut timeline_lines = vec![
            Line::from(Span::styled(
                "Audit Trail & Comments:",
                Style::default()
                    .fg(BLT_TEXT_HEADING)
                    .add_modifier(Modifier::BOLD),
            )),
            Line::from(""),
        ];

        if app.audit_logs.is_empty() && issue.comments.is_empty() {
            timeline_lines.push(Line::from(Span::styled(
                "  No activity recorded yet for this report.",
                Style::default().fg(BLT_TEXT_DIM),
            )));
        } else {
            for comment in &issue.comments {
                timeline_lines.push(Line::from(vec![
                    Span::styled("  • ", Style::default().fg(BLT_PRIMARY)),
                    Span::styled(comment, Style::default().fg(BLT_TEXT_BODY)),
                ]));
            }
            for log in app.audit_logs.iter().rev().take(8) {
                timeline_lines.push(Line::from(vec![
                    Span::styled("  • ", Style::default().fg(BLT_TEXT_MUTED)),
                    Span::styled(log, Style::default().fg(BLT_TEXT_MUTED)),
                ]));
            }
        }

        let timeline_p = Paragraph::new(timeline_lines)
            .block(
                Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(DARK_BORDER))
                .title(Span::styled(
                    " ACTIVITY ",
                    Style::default().fg(BLT_TEXT_MUTED),
                ))
                .bg(DARK_SURFACE),
            )
            .wrap(Wrap { trim: false });
        f.render_widget(timeline_p, right_pane_chunks[2]);
    }
}
