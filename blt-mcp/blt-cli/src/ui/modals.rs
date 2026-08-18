//! Centered Overlay Modals and Popups.
//!
//! This module renders all centered dialogs, confirmation boxes, and forms:
//! - `draw_help_modal`: Quick reference guide for keyboard shortcuts.
//! - `draw_triage_modal`: Human-in-the-loop verification prompt for triage writes.
//! - `draw_submit_form_modal`: Multi-field submission form for reporting vulnerabilities.
//! - `draw_hunt_details_modal`: Modal popup for inspecting bounty hunt scopes.
//! - `draw_ai_triage_modal`: MCP AI-assisted automated triage recommendations dialog.
//! - `draw_bulk_triage_modal`: Confirmation overlay for updating multiple selected issues.
//! - `draw_agent_status_modal`: MCP subprocess agent status and telemetry dialog.
//! - `draw_vision_context_modal`: Optional context input box for AI Vision screenshot analysis.
//! - `draw_prompt_preview_modal`: Prompt template inspector for AI tools.
//! - `draw_easter_egg_modal`: Konami code reward dialog.

use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Modifier, Style, Stylize},
    text::{Line, Span},
    widgets::{Block, Borders, Clear, Paragraph, Row, Table, Wrap},
    Frame,
};

use super::markdown::{parse_inline_markdown, parse_markdown};
use super::theme::{
    BLT_PRIMARY, BLT_TEXT_BODY, BLT_TEXT_HEADING, BLT_TEXT_MUTED, DARK_BASE, DARK_BORDER,
    DARK_SURFACE, SEVERITY_CRITICAL, SEVERITY_HIGH, STATUS_IN_REVIEW, STATUS_RESOLVED,
};
use super::widgets::{centered_rect, Cell};
use crate::app::App;

/// Renders the keyboard shortcut reference modal.
pub fn draw_help_modal(f: &mut Frame, rect: Rect) {
    let help_area = centered_rect(65, 62, rect);
    f.render_widget(Clear, help_area);

    let rows = vec![
        Row::new(vec![
            Cell::from(Span::styled(
                "Tab / 1-5",
                Style::default()
                    .fg(BLT_PRIMARY)
                    .add_modifier(Modifier::BOLD),
            )),
            Cell::from(Span::styled(
                "Switch dashboard views (1=Issues, 2=Hunts, 3=Stats, 4=Logs, 5=Config)",
                Style::default().fg(BLT_TEXT_BODY),
            )),
        ]),
        Row::new(vec![
            Cell::from(Span::styled(
                "Up / Down Arrow (j/k)",
                Style::default()
                    .fg(BLT_PRIMARY)
                    .add_modifier(Modifier::BOLD),
            )),
            Cell::from(Span::styled(
                "Navigate and scroll through active items in tables/lists",
                Style::default().fg(BLT_TEXT_BODY),
            )),
        ]),
        Row::new(vec![
            Cell::from(Span::styled(
                "/ (Slash)",
                Style::default()
                    .fg(BLT_PRIMARY)
                    .add_modifier(Modifier::BOLD),
            )),
            Cell::from(Span::styled(
                "Open inline search filter bar",
                Style::default().fg(BLT_TEXT_BODY),
            )),
        ]),
        Row::new(vec![
            Cell::from(Span::styled(
                "Space",
                Style::default()
                    .fg(BLT_PRIMARY)
                    .add_modifier(Modifier::BOLD),
            )),
            Cell::from(Span::styled(
                "Select / Deselect vulnerability for Bulk Triage actions",
                Style::default().fg(BLT_TEXT_BODY),
            )),
        ]),
        Row::new(vec![
            Cell::from(Span::styled(
                "t",
                Style::default()
                    .fg(SEVERITY_HIGH)
                    .add_modifier(Modifier::BOLD),
            )),
            Cell::from(Span::styled(
                "Triage selected vulnerability (or bulk triage if multiple selected)",
                Style::default().fg(BLT_TEXT_BODY),
            )),
        ]),
        Row::new(vec![
            Cell::from(Span::styled(
                "a",
                Style::default()
                    .fg(STATUS_IN_REVIEW)
                    .add_modifier(Modifier::BOLD),
            )),
            Cell::from(Span::styled(
                "Trigger MCP AI-Assisted Automated Triage Analysis",
                Style::default().fg(BLT_TEXT_BODY),
            )),
        ]),
        Row::new(vec![
            Cell::from(Span::styled(
                "s / Ctrl+S",
                Style::default()
                    .fg(STATUS_RESOLVED)
                    .add_modifier(Modifier::BOLD),
            )),
            Cell::from(Span::styled(
                "Open 'Report New Vulnerability' submission form",
                Style::default().fg(BLT_TEXT_BODY),
            )),
        ]),
        Row::new(vec![
            Cell::from(Span::styled(
                "p / Ctrl+V",
                Style::default()
                    .fg(STATUS_IN_REVIEW)
                    .add_modifier(Modifier::BOLD),
            )),
            Cell::from(Span::styled(
                "Paste clipboard screenshot image & trigger AI Vision draft",
                Style::default().fg(BLT_TEXT_BODY),
            )),
        ]),
        Row::new(vec![
            Cell::from(Span::styled(
                "Enter",
                Style::default()
                    .fg(BLT_PRIMARY)
                    .add_modifier(Modifier::BOLD),
            )),
            Cell::from(Span::styled(
                "Inspect details modal for active Bounty Hunt or selection",
                Style::default().fg(BLT_TEXT_BODY),
            )),
        ]),
        Row::new(vec![
            Cell::from(Span::styled(
                "e",
                Style::default()
                    .fg(BLT_PRIMARY)
                    .add_modifier(Modifier::BOLD),
            )),
            Cell::from(Span::styled(
                "Export session audit logs to blt_export.log",
                Style::default().fg(BLT_TEXT_BODY),
            )),
        ]),
        Row::new(vec![
            Cell::from(Span::styled(
                "Esc",
                Style::default()
                    .fg(BLT_TEXT_MUTED)
                    .add_modifier(Modifier::BOLD),
            )),
            Cell::from(Span::styled(
                "Dismiss any active dialog, modal, or search filter",
                Style::default().fg(BLT_TEXT_BODY),
            )),
        ]),
        Row::new(vec![
            Cell::from(Span::styled(
                "q / Ctrl+C",
                Style::default()
                    .fg(SEVERITY_CRITICAL)
                    .add_modifier(Modifier::BOLD),
            )),
            Cell::from(Span::styled(
                "Safely disconnect and quit the CLI client",
                Style::default().fg(BLT_TEXT_BODY),
            )),
        ]),
    ];

    let table = Table::new(rows, [Constraint::Length(24), Constraint::Min(40)])
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(
                    Style::default()
                        .fg(BLT_PRIMARY)
                        .add_modifier(Modifier::BOLD),
                )
                .title(Span::styled(
                    " KEYBOARD SHORTCUTS ",
                    Style::default()
                        .fg(BLT_TEXT_HEADING)
                        .add_modifier(Modifier::BOLD),
                ))
                .bg(DARK_SURFACE),
        )
        .column_spacing(2);

    f.render_widget(table, help_area);
}

/// Renders the Human-In-The-Loop confirmation dialog for write operations.
pub fn draw_triage_modal(f: &mut Frame, app: &App, rect: Rect) {
    let modal_area = centered_rect(65, 36, rect);
    f.render_widget(Clear, modal_area);

    if app.issues.is_empty() {
        return;
    }

    let issue_id = &app.issues[app.selected_issue_index].id;

    let confirmation_text = vec![
        Line::from(""),
        Line::from(Span::styled(
            " HUMAN-IN-THE-LOOP VERIFICATION ",
            Style::default()
                .fg(BLT_PRIMARY)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from(" ────────────────────────────────────────────────────────"),
        Line::from(vec![
            Span::styled(
                " Setting Vulnerability ",
                Style::default().fg(BLT_TEXT_BODY),
            ),
            Span::styled(
                format!("#{}", issue_id),
                Style::default()
                    .fg(BLT_PRIMARY)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::styled(" Status to: ", Style::default().fg(BLT_TEXT_BODY)),
            Span::styled(
                "'In Review'",
                Style::default()
                    .fg(SEVERITY_HIGH)
                    .add_modifier(Modifier::BOLD),
            ),
        ]),
        Line::from(""),
        Line::from(Span::styled(
            " All write operations trigger audit logging and require explicit confirmation.",
            Style::default().fg(BLT_TEXT_MUTED),
        )),
        Line::from(""),
        Line::from(vec![
            Span::styled(
                " [Enter] ",
                Style::default()
                    .fg(STATUS_RESOLVED)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::styled(
                "Confirm Triage Update  │  ",
                Style::default().fg(BLT_TEXT_BODY),
            ),
            Span::styled(
                "[Esc] ",
                Style::default()
                    .fg(SEVERITY_CRITICAL)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::styled("Abort Operation", Style::default().fg(BLT_TEXT_BODY)),
        ]),
    ];

    let p = Paragraph::new(confirmation_text)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(
                    Style::default()
                        .fg(BLT_PRIMARY)
                        .add_modifier(Modifier::BOLD),
                )
                .title(Span::styled(
                    " CONFIRM TRIAGE ",
                    Style::default().fg(BLT_PRIMARY),
                ))
                .bg(DARK_SURFACE),
        )
        .alignment(ratatui::layout::Alignment::Center)
        .wrap(Wrap { trim: false });

    f.render_widget(p, modal_area);
}

/// Renders the multi-field vulnerability submission form.
pub fn draw_submit_form_modal(f: &mut Frame, app: &App, rect: Rect) {
    let modal_area = centered_rect(85, 90, rect);
    f.render_widget(Clear, modal_area);

    let block = Block::default()
        .borders(Borders::ALL)
        .border_style(
            Style::default()
                .fg(BLT_PRIMARY)
                .add_modifier(Modifier::BOLD),
        )
        .title(Span::styled(
            " REPORT VULNERABILITY ",
            Style::default()
                .fg(BLT_TEXT_HEADING)
                .add_modifier(Modifier::BOLD),
        ))
        .bg(DARK_SURFACE);
    f.render_widget(block, modal_area);

    let inner_area = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Min(0), Constraint::Length(2)])
        .margin(1)
        .split(modal_area);

    let columns = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(50), Constraint::Percentage(50)])
        .split(inner_area[0]);

    let left_chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3), // Title
            Constraint::Length(3), // URL
            Constraint::Length(3), // Severity
            Constraint::Length(3), // Bug Type
            Constraint::Length(3), // Screenshot
        ])
        .split(columns[0]);

    let right_chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Percentage(50), // Description
            Constraint::Percentage(50), // Steps to Reproduce
        ])
        .split(columns[1]);

    let active = &app.submit_form.active_field;

    let style_active = Style::default()
        .fg(BLT_PRIMARY)
        .add_modifier(Modifier::BOLD);
    let style_inactive = Style::default().fg(DARK_BORDER);

    // Title Field
    let title_style = if *active == crate::app::FormField::Title {
        style_active
    } else {
        style_inactive
    };
    let title_text = if *active == crate::app::FormField::Title {
        format!("{}█", app.submit_form.title)
    } else {
        app.submit_form.title.clone()
    };
    let title_p = Paragraph::new(title_text).block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(title_style)
            .title(" Vulnerability Title * "),
    );
    f.render_widget(title_p, left_chunks[0]);

    // URL Field
    let url_style = if *active == crate::app::FormField::Url {
        style_active
    } else {
        style_inactive
    };
    let url_text = if *active == crate::app::FormField::Url {
        format!("{}█", app.submit_form.url)
    } else {
        app.submit_form.url.clone()
    };
    let url_p = Paragraph::new(url_text).block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(url_style)
            .title(" Vulnerable Target URL * "),
    );
    f.render_widget(url_p, left_chunks[1]);

    // Severity Field
    let sev_style = if *active == crate::app::FormField::Severity {
        style_active
    } else {
        style_inactive
    };
    let sev_text = if *active == crate::app::FormField::Severity {
        format!("{}█", app.submit_form.severity)
    } else {
        app.submit_form.severity.clone()
    };
    let sev_p = Paragraph::new(sev_text).block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(sev_style)
            .title(" Severity (Critical / High / Medium / Low) "),
    );
    f.render_widget(sev_p, left_chunks[2]);

    // Bug Type Field
    let type_style = if *active == crate::app::FormField::BugType {
        style_active
    } else {
        style_inactive
    };
    let type_text = if *active == crate::app::FormField::BugType {
        format!("{}█", app.submit_form.bug_type)
    } else {
        app.submit_form.bug_type.clone()
    };
    let type_p = Paragraph::new(type_text).block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(type_style)
            .title(" Vulnerability Category / Type "),
    );
    f.render_widget(type_p, left_chunks[3]);

    // Screenshot Field
    let ss_style = if *active == crate::app::FormField::Screenshot {
        style_active
    } else {
        style_inactive
    };
    let ss_text = if *active == crate::app::FormField::Screenshot {
        format!("{}█", app.submit_form.screenshot_path)
    } else {
        app.submit_form.screenshot_path.clone()
    };
    let ss_p = Paragraph::new(ss_text).block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(ss_style)
            .title(" Screenshot Image Path "),
    );
    f.render_widget(ss_p, left_chunks[4]);

    // Description Field
    let desc_style = if *active == crate::app::FormField::Description {
        style_active
    } else {
        style_inactive
    };
    let desc_text = if *active == crate::app::FormField::Description {
        format!("{}█", app.submit_form.description)
    } else {
        app.submit_form.description.clone()
    };
    let desc_lines_count = desc_text.lines().count() as u16;
    let desc_inner_height = right_chunks[0].height.saturating_sub(2);
    let desc_scroll = if desc_lines_count > desc_inner_height {
        desc_lines_count.saturating_sub(desc_inner_height)
    } else {
        0
    };
    let desc_p = Paragraph::new(desc_text)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(desc_style)
                .title(" Detailed Description * "),
        )
        .wrap(Wrap { trim: false })
        .scroll((desc_scroll, 0));
    f.render_widget(desc_p, right_chunks[0]);

    // Steps to Reproduce Field
    let steps_style = if *active == crate::app::FormField::StepsToReproduce {
        style_active
    } else {
        style_inactive
    };
    let steps_text = if *active == crate::app::FormField::StepsToReproduce {
        format!("{}█", app.submit_form.steps_to_reproduce)
    } else {
        app.submit_form.steps_to_reproduce.clone()
    };
    let steps_lines_count = steps_text.lines().count() as u16;
    let steps_inner_height = right_chunks[1].height.saturating_sub(2);
    let steps_scroll = if steps_lines_count > steps_inner_height {
        steps_lines_count.saturating_sub(steps_inner_height)
    } else {
        0
    };
    let steps_p = Paragraph::new(steps_text)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(steps_style)
                .title(" Steps to Reproduce (PoC) "),
        )
        .wrap(Wrap { trim: false })
        .scroll((steps_scroll, 0));
    f.render_widget(steps_p, right_chunks[1]);

    // Form Navigation Instructions
    let instr_p = Paragraph::new(Line::from(vec![
        Span::styled(
            "[Tab] ",
            Style::default()
                .fg(BLT_PRIMARY)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled("Next  │  ", Style::default().fg(BLT_TEXT_BODY)),
        Span::styled(
            "[BackTab] ",
            Style::default()
                .fg(BLT_PRIMARY)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled("Prev  │  ", Style::default().fg(BLT_TEXT_BODY)),
        Span::styled(
            "[Ctrl+S] ",
            Style::default()
                .fg(STATUS_RESOLVED)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled("Submit Report  │  ", Style::default().fg(BLT_TEXT_BODY)),
        Span::styled(
            "[Esc] ",
            Style::default()
                .fg(BLT_TEXT_MUTED)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled("Cancel", Style::default().fg(BLT_TEXT_BODY)),
    ]))
    .alignment(ratatui::layout::Alignment::Center);
    f.render_widget(instr_p, inner_area[1]);
}

/// Renders the active bounty hunt details overlay dialog.
pub fn draw_hunt_details_modal(f: &mut Frame, app: &App, rect: Rect) {
    let modal_area = centered_rect(65, 62, rect);
    f.render_widget(Clear, modal_area);

    if app.hunts.is_empty() {
        return;
    }

    let hunt = &app.hunts[app.selected_hunt_index];

    let mut lines = vec![
        Line::from(""),
        Line::from(vec![
            Span::styled("Program: ", Style::default().fg(BLT_TEXT_MUTED)),
            Span::styled(
                hunt.name.clone(),
                Style::default()
                    .fg(BLT_TEXT_HEADING)
                    .add_modifier(Modifier::BOLD),
            ),
        ]),
        Line::from(vec![
            Span::styled("Status:  ", Style::default().fg(BLT_TEXT_MUTED)),
            Span::styled(
                hunt.status.clone(),
                Style::default()
                    .fg(STATUS_RESOLVED)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::styled("  │  Reward: ", Style::default().fg(BLT_TEXT_MUTED)),
            Span::styled(
                format!("{} Bacon", hunt.reward),
                Style::default()
                    .fg(STATUS_RESOLVED)
                    .add_modifier(Modifier::BOLD),
            ),
        ]),
        Line::from(""),
        Line::from(Span::styled(
            "Specifications & Scope:",
            Style::default()
                .fg(BLT_TEXT_HEADING)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from(""),
    ];

    let mut parsed_desc = parse_markdown(&hunt.description);
    lines.append(&mut parsed_desc);

    lines.push(Line::from(""));
    lines.push(Line::from(
        " ────────────────────────────────────────────────────────",
    ));
    lines.push(Line::from(vec![
        Span::styled(
            " [s] ",
            Style::default()
                .fg(STATUS_RESOLVED)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled(
            "Report Bug for Hunt  │  ",
            Style::default().fg(BLT_TEXT_BODY),
        ),
        Span::styled(
            "[Esc] ",
            Style::default()
                .fg(BLT_TEXT_MUTED)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled("Close", Style::default().fg(BLT_TEXT_BODY)),
    ]));

    let p = Paragraph::new(lines)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(DARK_BORDER))
                .title(Span::styled(
                    " BOUNTY HUNT SPECIFICATIONS ",
                    Style::default().fg(BLT_TEXT_MUTED),
                ))
                .bg(DARK_SURFACE),
        )
        .wrap(Wrap { trim: false });

    f.render_widget(p, modal_area);
}

/// Renders the AI-assisted automated triage recommendations dialog.
pub fn draw_ai_triage_modal(f: &mut Frame, app: &App, rect: Rect) {
    let modal_area = centered_rect(68, 65, rect);
    f.render_widget(Clear, modal_area);

    let content = app
        .ai_triage_result
        .clone()
        .unwrap_or_else(|| "Querying MCP AI Triage Agent...".to_string());

    let mut lines = parse_inline_markdown(&content);

    lines.push(Line::from(""));
    lines.push(Line::from(
        " ────────────────────────────────────────────────────────",
    ));
    lines.push(Line::from(vec![
        Span::styled(
            " [Esc] ",
            Style::default()
                .fg(BLT_TEXT_MUTED)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled("Close Analysis Dialog", Style::default().fg(BLT_TEXT_BODY)),
    ]));

    let p = Paragraph::new(lines)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(DARK_BORDER))
                .title(Span::styled(
                    " AI-ASSISTED TRIAGE ",
                    Style::default()
                        .fg(BLT_TEXT_HEADING)
                        .add_modifier(Modifier::BOLD),
                ))
                .bg(DARK_SURFACE),
        )
        .wrap(Wrap { trim: false });

    f.render_widget(p, modal_area);
}

/// Renders the bulk triage confirmation overlay dialog.
pub fn draw_bulk_triage_modal(f: &mut Frame, app: &App, rect: Rect) {
    let area = centered_rect(54, 22, rect);
    f.render_widget(Clear, area);

    let text = vec![
        Line::from(""),
        Line::from(vec![
            Span::styled(" Bulk Triaging ", Style::default().fg(BLT_TEXT_BODY)),
            Span::styled(
                format!("{} Selected Vulnerabilities", app.selected_issues.len()),
                Style::default()
                    .fg(BLT_PRIMARY)
                    .add_modifier(Modifier::BOLD),
            ),
        ]),
        Line::from(""),
        Line::from(vec![
            Span::styled(" Target Status: ", Style::default().fg(BLT_TEXT_MUTED)),
            Span::styled(
                format!("[{}]", app.triage_target_status),
                Style::default()
                    .fg(SEVERITY_HIGH)
                    .add_modifier(Modifier::BOLD),
            ),
        ]),
        Line::from(""),
        Line::from(Span::styled(
            " [1] Open  [2] In Review  [3] Resolved",
            Style::default().fg(BLT_TEXT_BODY),
        )),
        Line::from(""),
        Line::from(vec![
            Span::styled(
                " [Enter] ",
                Style::default()
                    .fg(STATUS_RESOLVED)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::styled(
                "Confirm Bulk Action  │  ",
                Style::default().fg(BLT_TEXT_BODY),
            ),
            Span::styled(
                "[Esc] ",
                Style::default()
                    .fg(SEVERITY_CRITICAL)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::styled("Cancel", Style::default().fg(BLT_TEXT_BODY)),
        ]),
    ];
    let p = Paragraph::new(text).block(
        Block::default()
            .borders(Borders::ALL)
            .title(Span::styled(
                " BULK TRIAGE ",
                Style::default().fg(SEVERITY_HIGH),
            ))
            .border_style(
                Style::default()
                    .fg(SEVERITY_HIGH)
                    .add_modifier(Modifier::BOLD),
            )
            .bg(DARK_SURFACE),
    );
    f.render_widget(p, area);
}

/// Renders the MCP subprocess agent status and telemetry dialog.
pub fn draw_agent_status_modal(f: &mut Frame, app: &App, rect: Rect) {
    let modal_area = centered_rect(62, 42, rect);
    f.render_widget(Clear, modal_area);

    let lines: Vec<Line> = app
        .agent_status_data
        .split('\n')
        .map(|s| {
            Line::from(Span::styled(
                s.to_string(),
                Style::default().fg(BLT_TEXT_BODY),
            ))
        })
        .collect();

    let p = Paragraph::new(lines)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(DARK_BORDER))
                .title(Span::styled(
                    " MCP AGENT TELEMETRY ",
                    Style::default().fg(BLT_TEXT_MUTED),
                ))
                .bg(DARK_SURFACE),
        )
        .wrap(Wrap { trim: false });

    f.render_widget(p, modal_area);
}

/// Renders the vision context input modal for screenshot parsing.
pub fn draw_vision_context_modal(f: &mut Frame, app: &App, rect: Rect) {
    let area = centered_rect(62, 18, rect);
    f.render_widget(Clear, area);

    let text = vec![
        Line::from(""),
        Line::from(Span::styled(
            " Enter optional context or vulnerability hints for AI Vision parsing:",
            Style::default().fg(BLT_TEXT_BODY),
        )),
        Line::from(vec![
            Span::styled(
                " > ",
                Style::default()
                    .fg(BLT_PRIMARY)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::styled(
                &app.vision_context_input,
                Style::default().fg(BLT_TEXT_HEADING),
            ),
            Span::styled("█", Style::default().fg(BLT_PRIMARY)),
        ]),
        Line::from(""),
        Line::from(vec![
            Span::styled(
                " [Enter] ",
                Style::default()
                    .fg(STATUS_RESOLVED)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::styled(
                "Run Vision Analysis  │  ",
                Style::default().fg(BLT_TEXT_BODY),
            ),
            Span::styled(
                "[Esc] ",
                Style::default()
                    .fg(BLT_TEXT_MUTED)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::styled("Skip & Run Directly", Style::default().fg(BLT_TEXT_BODY)),
        ]),
    ];

    let p = Paragraph::new(text).block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(
                Style::default()
                    .fg(BLT_PRIMARY)
                    .add_modifier(Modifier::BOLD),
            )
            .title(Span::styled(
                " VISION AI CONTEXT ",
                Style::default().fg(BLT_PRIMARY),
            ))
            .bg(DARK_SURFACE),
    );
    f.render_widget(p, area);
}

/// Renders the prompt inspection preview modal.
pub fn draw_prompt_preview_modal(f: &mut Frame, app: &App, rect: Rect) {
    let modal_area = centered_rect(72, 60, rect);
    f.render_widget(Clear, modal_area);

    let lines: Vec<Line> = app
        .prompt_preview_data
        .split('\n')
        .map(|s| {
            Line::from(Span::styled(
                s.to_string(),
                Style::default().fg(BLT_TEXT_BODY),
            ))
        })
        .collect();

    let p = Paragraph::new(lines)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(DARK_BORDER))
                .title(Span::styled(
                    " PROMPT PREVIEW ",
                    Style::default().fg(BLT_TEXT_MUTED),
                ))
                .bg(DARK_SURFACE),
        )
        .wrap(Wrap { trim: false });

    f.render_widget(p, modal_area);
}

/// Renders the Konami code easter egg modal overlay.
pub fn draw_easter_egg_modal(f: &mut Frame, rect: Rect) {
    let modal_area = centered_rect(60, 50, rect);
    f.render_widget(Clear, modal_area);

    let art = vec![
        Line::from(Span::styled(
            r#"  ____    _    ____ ___  _   _ "#,
            Style::default()
                .fg(BLT_PRIMARY)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from(Span::styled(
            r#" | __ )  / \  / ___/ _ \| \ | |"#,
            Style::default()
                .fg(BLT_PRIMARY)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from(Span::styled(
            r#" |  _ \ / _ \| |  | | | |  \| |"#,
            Style::default()
                .fg(BLT_PRIMARY)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from(Span::styled(
            r#" | |_) / ___ \ |__| |_| | |\  |"#,
            Style::default()
                .fg(BLT_PRIMARY)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from(Span::styled(
            r#" |____/_/   \_\____\___/|_| \_|"#,
            Style::default()
                .fg(BLT_PRIMARY)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from(""),
        Line::from(Span::styled(
            "You unlocked the BLT Konami Code! +100 Bacon Points!",
            Style::default()
                .fg(STATUS_RESOLVED)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from(""),
        Line::from(Span::styled(
            "[ Press Any Key to Continue ]",
            Style::default().fg(BLT_TEXT_MUTED),
        )),
    ];

    let p = Paragraph::new(art)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(STATUS_RESOLVED))
                .bg(DARK_BASE),
        )
        .alignment(ratatui::layout::Alignment::Center)
        .wrap(Wrap { trim: false });

    f.render_widget(p, modal_area);
}
