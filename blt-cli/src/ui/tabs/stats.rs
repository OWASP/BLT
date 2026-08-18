//! Telemetry Metrics, Severity BarChart, and Contributor Leaderboard (Tab 3).
//!
//! This module renders live system statistics, authentic vulnerability severity
//! breakdowns using a Ratatui `BarChart`, and the top security contributor leaderboard.
//!
//! Key Functions:
//! - `draw_stats_tab(f, app, rect)`: Renders 4 authentic KPI cards (Total Issues,
//!   Active Repos, Contributors, Bacon Score), dynamic BarChart from loaded issues,
//!   and the hacker rank leaderboard table.

use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style, Stylize},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph, Row, Table},
    Frame,
};

use crate::app::App;
use crate::ui::theme::{
    BLT_PRIMARY, BLT_TEXT_BODY, BLT_TEXT_HEADING, BLT_TEXT_MUTED, DARK_BORDER, DARK_SURFACE,
    DARK_SURFACE_ALT, SEVERITY_HIGH, STATUS_IN_REVIEW, STATUS_RESOLVED,
};
use crate::ui::widgets::Cell;

/// Renders the statistics dashboard with KPI cards, severity chart, and leaderboard.
pub fn draw_stats_tab(f: &mut Frame, app: &App, rect: Rect) {
    let horizontal_layout = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(55), Constraint::Percentage(45)])
        .split(rect);

    // Left Panel: Authentic Metric Cards & Dynamic BarChart
    let vertical_chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Length(5), Constraint::Min(8)])
        .split(horizontal_layout[0]);

    let kpi_row = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(25),
            Constraint::Percentage(25),
            Constraint::Percentage(25),
            Constraint::Percentage(25),
        ])
        .split(vertical_chunks[0]);

    // KPI Card 1: Total Issues (Real Count)
    let total_issues_display = if app.stats.total_issues > 0 {
        app.stats.total_issues
    } else {
        app.issues.len() as u32
    };
    let card_1 = Paragraph::new(vec![
        Line::from(Span::styled(
            format!(" {}", total_issues_display),
            Style::default()
                .fg(BLT_PRIMARY)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from(Span::styled(
            " Total Issues",
            Style::default().fg(BLT_TEXT_MUTED),
        )),
    ])
    .block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(DARK_BORDER))
            .title(Span::styled(
                " ISSUES ",
                Style::default().fg(BLT_TEXT_MUTED),
            ))
            .bg(DARK_SURFACE),
    );
    f.render_widget(card_1, kpi_row[0]);

    // KPI Card 2: Active Repos (Real Count)
    let active_repos_display = if app.stats.active_repos > 0 {
        app.stats.active_repos
    } else {
        app.repos.len() as u32
    };
    let card_2 = Paragraph::new(vec![
        Line::from(Span::styled(
            format!(" {}", active_repos_display),
            Style::default()
                .fg(SEVERITY_HIGH)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from(Span::styled(
            " Active Repos",
            Style::default().fg(BLT_TEXT_MUTED),
        )),
    ])
    .block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(DARK_BORDER))
            .title(Span::styled(" REPOS ", Style::default().fg(BLT_TEXT_MUTED)))
            .bg(DARK_SURFACE),
    );
    f.render_widget(card_2, kpi_row[1]);

    // KPI Card 3: Contributors (Real Count)
    let card_3 = Paragraph::new(vec![
        Line::from(Span::styled(
            format!(" {}", app.stats.total_contributors),
            Style::default()
                .fg(STATUS_IN_REVIEW)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from(Span::styled(
            " Contributors",
            Style::default().fg(BLT_TEXT_MUTED),
        )),
    ])
    .block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(DARK_BORDER))
            .title(Span::styled(
                " COMMUNITY ",
                Style::default().fg(BLT_TEXT_MUTED),
            ))
            .bg(DARK_SURFACE),
    );
    f.render_widget(card_3, kpi_row[2]);

    // KPI Card 4: Bounty Score (Real Count)
    let card_4 = Paragraph::new(vec![
        Line::from(Span::styled(
            format!(" {} Bacon", app.stats.bacon),
            Style::default()
                .fg(STATUS_RESOLVED)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from(Span::styled(
            " Bacon Score",
            Style::default().fg(BLT_TEXT_MUTED),
        )),
    ])
    .block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(DARK_BORDER))
            .title(Span::styled(
                " REWARDS ",
                Style::default().fg(BLT_TEXT_MUTED),
            ))
            .bg(DARK_SURFACE),
    );
    f.render_widget(card_4, kpi_row[3]);

    // BarChart: Real Distribution from Loaded Issues
    let mut crit = 0;
    let mut high = 0;
    let mut med = 0;
    let mut low = 0;
    for issue in &app.issues {
        match issue.severity.to_lowercase().as_str() {
            "critical" => crit += 1,
            "high" => high += 1,
            "medium" => med += 1,
            _ => low += 1,
        }
    }
    let barchart_data = vec![
        ("Critical", crit as u64),
        ("High", high as u64),
        ("Medium", med as u64),
        ("Low", low as u64),
    ];
    let barchart = ratatui::widgets::BarChart::default()
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(DARK_BORDER))
                .title(Span::styled(
                    " SEVERITY BREAKDOWN ",
                    Style::default()
                        .fg(BLT_TEXT_HEADING)
                        .add_modifier(Modifier::BOLD),
                ))
                .bg(DARK_SURFACE),
        )
        .data(&barchart_data)
        .bar_width(10)
        .bar_gap(4)
        .value_style(
            Style::default()
                .fg(BLT_TEXT_HEADING)
                .add_modifier(Modifier::BOLD),
        )
        .label_style(Style::default().fg(BLT_TEXT_MUTED))
        .bar_style(Style::default().fg(BLT_PRIMARY));
    f.render_widget(barchart, vertical_chunks[1]);

    // Right Panel: Real Contributor Leaderboard
    let header_cells = vec!["RANK", "HACKER", "REPUTATION", "BACON"];
    let header = Row::new(header_cells)
        .style(
            Style::default()
                .fg(BLT_TEXT_MUTED)
                .bg(DARK_SURFACE_ALT)
                .add_modifier(Modifier::BOLD),
        )
        .bottom_margin(0);

    let rows = app.leaderboard.iter().map(|entry| {
        let rank_color = match entry.rank {
            1 => Color::Rgb(255, 215, 0),   // Gold
            2 => Color::Rgb(200, 210, 220), // Silver
            3 => Color::Rgb(205, 127, 50),  // Bronze
            _ => BLT_TEXT_MUTED,
        };

        let rank_display = format!("#{}", entry.rank);

        let cells = vec![
            Cell::from(Span::styled(
                rank_display,
                Style::default().fg(rank_color).add_modifier(Modifier::BOLD),
            )),
            Cell::from(Span::styled(
                entry.name.clone(),
                Style::default().fg(BLT_TEXT_BODY),
            )),
            Cell::from(Span::styled(
                entry.reputation.clone(),
                Style::default().fg(BLT_TEXT_MUTED),
            )),
            Cell::from(Span::styled(
                format!("{} Bacon", entry.bacon),
                Style::default()
                    .fg(STATUS_RESOLVED)
                    .add_modifier(Modifier::BOLD),
            )),
        ];

        Row::new(cells).style(Style::default().fg(BLT_TEXT_BODY))
    });

    if app.leaderboard.is_empty() {
        let empty_msg = Paragraph::new("\n\nNo contributor rankings loaded.")
            .alignment(ratatui::layout::Alignment::Center)
            .block(
                Block::default()
                    .borders(Borders::ALL)
                    .border_style(Style::default().fg(DARK_BORDER))
                    .title(Span::styled(
                        " LEADERBOARD ",
                        Style::default()
                            .fg(BLT_TEXT_HEADING)
                            .add_modifier(Modifier::BOLD),
                    ))
                    .bg(DARK_SURFACE),
            )
            .style(Style::default().fg(BLT_TEXT_MUTED));
        f.render_widget(empty_msg, horizontal_layout[1]);
    } else {
        let leaderboard_table = Table::new(
            rows,
            [
                Constraint::Length(6),
                Constraint::Percentage(40),
                Constraint::Percentage(25),
                Constraint::Percentage(27),
            ],
        )
        .header(header)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(DARK_BORDER))
                .title(Span::styled(
                    " LEADERBOARD ",
                    Style::default()
                        .fg(BLT_TEXT_HEADING)
                        .add_modifier(Modifier::BOLD),
                ))
                .bg(DARK_SURFACE),
        )
        .column_spacing(1);

        f.render_widget(leaderboard_table, horizontal_layout[1]);
    }
}
