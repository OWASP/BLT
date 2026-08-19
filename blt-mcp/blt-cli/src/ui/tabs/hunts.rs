//! Active Bounty Hunts and Security Program Specifications (Tab 2).
//!
//! This module renders the Bounty Hunts view, allowing security researchers
//! to browse active target programs, view reward bacon points, and inspect
//! detailed rules of engagement and scope specifications.
//!
//! Key Functions:
//! - `draw_hunts_tab(f, app, rect)`: Renders the 2-column layout consisting of
//!   the searchable bounty hunts table on the left and the markdown-rendered
//!   program scope specifications on the right.

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
    DARK_BORDER, DARK_CARD_SELECTED, DARK_SURFACE, DARK_SURFACE_ALT, STATUS_PENDING,
    STATUS_RESOLVED,
};
use crate::ui::widgets::Cell;

/// Renders the active bounty hunt list and detailed program specifications.
pub fn draw_hunts_tab(f: &mut Frame, app: &App, rect: Rect) {
    let mut main_rect = rect;

    if app.active_overlay == crate::app::ActiveOverlay::SearchInput || !app.search_query.is_empty()
    {
        let search_layout = Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Length(3), Constraint::Min(0)])
            .split(rect);

        let prefix = if app.active_overlay == crate::app::ActiveOverlay::SearchInput {
            " Search Hunts > "
        } else {
            " Search Hunts: "
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
            Span::styled(
                "  (Press [Esc] to reset)",
                Style::default().fg(BLT_TEXT_DIM),
            ),
        ]))
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(BLT_PRIMARY))
                .bg(DARK_SURFACE),
        );

        f.render_widget(search_p, search_layout[0]);
        main_rect = search_layout[1];
    }

    let horizontal_layout = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(45), Constraint::Percentage(55)])
        .split(main_rect);

    if app.hunts.is_empty() {
        let empty_msg = Paragraph::new(vec![
            Line::from(""),
            Line::from(""),
            Line::from(Span::styled(
                "No active bounty hunt programs available.",
                Style::default().fg(BLT_TEXT_MUTED),
            )),
        ])
        .alignment(ratatui::layout::Alignment::Center)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(DARK_BORDER))
                .title(" BOUNTY HUNTS ")
                .bg(DARK_SURFACE),
        );
        f.render_widget(empty_msg, horizontal_layout[0]);
    } else {
        let header_cells = vec!["PROGRAM / TARGET", "REWARD", "STATUS"];
        let header = Row::new(header_cells)
            .style(
                Style::default()
                    .fg(BLT_TEXT_MUTED)
                    .bg(DARK_SURFACE_ALT)
                    .add_modifier(Modifier::BOLD),
            )
            .bottom_margin(0);

        let rows = app.hunts.iter().enumerate().filter_map(|(idx, hunt)| {
            if !app.search_query.is_empty() {
                let q = app.search_query.to_lowercase();
                if !hunt.name.to_lowercase().contains(&q)
                    && !hunt.description.to_lowercase().contains(&q)
                    && !hunt.status.to_lowercase().contains(&q)
                    && !hunt.reward.to_lowercase().contains(&q)
                {
                    return None;
                }
            }

            let is_selected = idx == app.selected_hunt_index;

            let row_selector = if is_selected {
                Span::styled(
                    "▎ ",
                    Style::default()
                        .fg(BLT_PRIMARY)
                        .add_modifier(Modifier::BOLD),
                )
            } else {
                Span::raw("  ")
            };

            let title_span = Span::styled(
                &hunt.name,
                if is_selected {
                    Style::default()
                        .fg(BLT_TEXT_HEADING)
                        .add_modifier(Modifier::BOLD)
                } else {
                    Style::default().fg(BLT_TEXT_BODY)
                },
            );

            let reward_display = Span::styled(
                format!("{} Bacon", hunt.reward),
                Style::default()
                    .fg(STATUS_RESOLVED)
                    .add_modifier(Modifier::BOLD),
            );

            let status_span = Span::styled(
                &hunt.status,
                Style::default().fg(if hunt.status.eq_ignore_ascii_case("active") {
                    STATUS_RESOLVED
                } else {
                    STATUS_PENDING
                }),
            );

            let cells = vec![
                Cell::from(Line::from(vec![row_selector, title_span])),
                Cell::from(reward_display),
                Cell::from(status_span),
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
                Constraint::Fill(3),
                Constraint::Length(16),
                Constraint::Length(12),
            ],
        )
        .header(header)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(DARK_BORDER))
                .title(Span::styled(
                    " BOUNTY HUNTS ",
                    Style::default()
                        .fg(BLT_TEXT_HEADING)
                        .add_modifier(Modifier::BOLD),
                ))
                .bg(DARK_SURFACE),
        )
        .column_spacing(1);

        f.render_widget(table, horizontal_layout[0]);
    }

    // Right Pane: Bounty Hunt Scope & Rules
    if !app.hunts.is_empty() {
        let hunt = &app.hunts[app.selected_hunt_index];

        let mut desc_lines = vec![
            Line::from(vec![
                Span::styled("Target Program: ", Style::default().fg(BLT_TEXT_MUTED)),
                Span::styled(
                    &hunt.name,
                    Style::default()
                        .fg(BLT_TEXT_HEADING)
                        .add_modifier(Modifier::BOLD),
                ),
            ]),
            Line::from(vec![
                Span::styled("Reward:         ", Style::default().fg(BLT_TEXT_MUTED)),
                Span::styled(
                    format!("{} Bacon Points", hunt.reward),
                    Style::default()
                        .fg(STATUS_RESOLVED)
                        .add_modifier(Modifier::BOLD),
                ),
                Span::styled("  │  Status: ", Style::default().fg(BLT_TEXT_MUTED)),
                Span::styled(
                    &hunt.status,
                    Style::default()
                        .fg(BLT_TEXT_HEADING)
                        .add_modifier(Modifier::BOLD),
                ),
            ]),
            Line::from(""),
            Line::from(Span::styled(
                "Scope & Rules of Engagement:",
                Style::default()
                    .fg(BLT_TEXT_HEADING)
                    .add_modifier(Modifier::BOLD),
            )),
            Line::from(""),
        ];

        desc_lines.extend(crate::ui::markdown::parse_markdown(&hunt.description));

        desc_lines.push(Line::from(""));
        desc_lines.push(Line::from(vec![
            Span::styled(
                "[Enter] ",
                Style::default()
                    .fg(BLT_PRIMARY)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::styled("View Details Modal   ", Style::default().fg(BLT_TEXT_DIM)),
            Span::styled(
                "[s] ",
                Style::default()
                    .fg(STATUS_RESOLVED)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::styled(
                "Submit Bug for this Hunt",
                Style::default().fg(BLT_TEXT_DIM),
            ),
        ]));

        let desc_p = Paragraph::new(desc_lines)
            .block(
                Block::default()
                    .borders(Borders::ALL)
                    .border_style(Style::default().fg(DARK_BORDER))
                    .title(Span::styled(
                        " SPECIFICATIONS ",
                        Style::default().fg(BLT_TEXT_MUTED),
                    ))
                    .bg(DARK_SURFACE),
            )
            .wrap(Wrap { trim: false });

        f.render_widget(desc_p, horizontal_layout[1]);
    }
}
