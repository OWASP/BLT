use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Clear, List, ListItem, Paragraph, Row, Table, Tabs, Wrap},
    Frame,
};

use crate::app::{App, Tab, RunMode};
use ratatui::style::Stylize;

// Define BLT brand color palette
const BLT_RED: Color = Color::Rgb(225, 1, 1);
const SLATE_BG: Color = Color::Rgb(30, 30, 35);
const SLATE_SURFACE: Color = Color::Rgb(45, 45, 50);
const MUTED_BORDER: Color = Color::Rgb(80, 80, 85);
const TEXT_LIGHT: Color = Color::Rgb(240, 240, 240);
const SEVERITY_CRITICAL: Color = Color::Rgb(255, 60, 60);
const SEVERITY_HIGH: Color = Color::Rgb(255, 120, 60);

pub fn draw(f: &mut Frame, app: &mut App) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3), // Header
            Constraint::Min(10),   // Content
            Constraint::Length(3), // Footer
        ])
        .split(f.size());

    // 1. Draw Header
    draw_header(f, app, chunks[0]);

    // 2. Draw Main Content based on active tab
    match app.active_tab {
        Tab::Issues => draw_issues_tab(f, app, chunks[1]),
        Tab::Hunts => draw_hunts_tab(f, app, chunks[1]),
        Tab::Stats => draw_stats_tab(f, app, chunks[1]),
        Tab::Settings => draw_settings_tab(f, app, chunks[1]),
    }

    // 3. Draw Footer / Status Bar
    draw_footer(f, app, chunks[2]);

    // 4. Draw Overlay Modals if active
    if app.show_help {
        draw_help_modal(f, chunks[1]);
    } else if app.show_triage_modal {
        draw_triage_modal(f, app, chunks[1]);
    }
}

fn draw_header(f: &mut Frame, app: &App, rect: Rect) {
    let header_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Length(25),
            Constraint::Min(20),
            Constraint::Length(48),
        ])
        .split(rect);

    // Title Block
    let title_block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(MUTED_BORDER))
        .bg(SLATE_SURFACE);
    
    let title_p = Paragraph::new(Line::from(vec![
        Span::styled(" OWASP BLT ", Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD)),
        Span::styled("TUI v1.0.0", Style::default().fg(TEXT_LIGHT)),
    ]))
    .block(title_block);
    f.render_widget(title_p, header_chunks[0]);

    // Connection Status Block
    let badge_block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(MUTED_BORDER))
        .bg(SLATE_SURFACE);

    let (status_text, status_style) = match app.run_mode {
        RunMode::Offline => (
            " ○ OFFLINE (MOCK) ",
            Style::default().fg(Color::DarkGray).add_modifier(Modifier::BOLD),
        ),
        RunMode::Mcp => {
            if app.is_live {
                (
                    " ● LIVE (MCP) ",
                    Style::default().fg(Color::Green).add_modifier(Modifier::BOLD),
                )
            } else {
                (
                    " ● MOCK FALLBACK (MCP FAILED) ",
                    Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
                )
            }
        }
        RunMode::Standalone => {
            if app.is_live {
                (
                    " ● LIVE (API) ",
                    Style::default().fg(Color::Green).add_modifier(Modifier::BOLD),
                )
            } else {
                (
                    " ● MOCK FALLBACK (API FAILED) ",
                    Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
                )
            }
        }
    };

    let badge_p = Paragraph::new(Line::from(vec![
        Span::styled(" Status: ", Style::default().fg(Color::Gray)),
        Span::styled(status_text, status_style),
    ]))
    .block(badge_block);
    f.render_widget(badge_p, header_chunks[1]);

    // Tabs Block
    let tab_titles = vec!["[1] Issues", "[2] Hunts", "[3] Stats", "[4] Settings"];
    let tab_index = match app.active_tab {
        Tab::Issues => 0,
        Tab::Hunts => 1,
        Tab::Stats => 2,
        Tab::Settings => 3,
    };

    let tabs = Tabs::new(tab_titles)
        .block(Block::default().borders(Borders::ALL).border_style(Style::default().fg(MUTED_BORDER)).bg(SLATE_SURFACE))
        .select(tab_index)
        .style(Style::default().fg(Color::Gray))
        .highlight_style(Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD));
    
    f.render_widget(tabs, header_chunks[2]);
}

fn draw_issues_tab(f: &mut Frame, app: &App, rect: Rect) {
    let vertical_layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(55), Constraint::Percentage(45)])
        .split(rect);

    // 1. Draw Issues Table
    let header_cells = vec!["ID", "Repository", "Severity", "Status", "Issue Title"];
    let header = Row::new(header_cells)
        .style(Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))
        .bottom_margin(1);

    let rows = app.issues.iter().enumerate().map(|(idx, issue)| {
        let is_selected = idx == app.selected_issue_index;
        
        let severity_color = match issue.severity.as_str() {
            "Critical" => SEVERITY_CRITICAL,
            "High" => SEVERITY_HIGH,
            _ => Color::Yellow,
        };

        let cells = vec![
            Cell::from(issue.id.clone()),
            Cell::from(issue.repository.clone()),
            Cell::from(Span::styled(issue.severity.clone(), Style::default().fg(severity_color).add_modifier(Modifier::BOLD))),
            Cell::from(issue.status.clone()),
            Cell::from(issue.title.clone()),
        ];

        let mut row_style = Style::default().fg(TEXT_LIGHT);
        if is_selected {
            row_style = row_style.bg(SLATE_SURFACE).fg(BLT_RED).add_modifier(Modifier::BOLD);
        }

        Row::new(cells).style(row_style)
    });

    let table = Table::new(rows, [
        Constraint::Length(6),
        Constraint::Length(20),
        Constraint::Length(10),
        Constraint::Length(12),
        Constraint::Min(30),
    ])
    .header(header)
    .block(Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(MUTED_BORDER))
        .title(" Vulnerabilities Log ")
        .title_style(Style::default().fg(TEXT_LIGHT).add_modifier(Modifier::BOLD))
        .bg(SLATE_BG))
    .column_spacing(1);

    f.render_widget(table, vertical_layout[0]);

    // 2. Draw Selected Issue Details Panel
    if !app.issues.is_empty() {
        let issue = &app.issues[app.selected_issue_index];
        let detail_chunks = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([Constraint::Percentage(60), Constraint::Percentage(40)])
            .split(vertical_layout[1]);

        // Description Box
        let desc_text = vec![
            Line::from(vec![
                Span::styled("Title: ", Style::default().fg(Color::Gray)),
                Span::styled(&issue.title, Style::default().fg(TEXT_LIGHT).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::styled("Author: ", Style::default().fg(Color::Gray)),
                Span::styled(&issue.author, Style::default().fg(Color::Cyan)),
                Span::styled("  |  Severity: ", Style::default().fg(Color::Gray)),
                Span::styled(&issue.severity, Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(""),
            Line::from(Span::styled("Description:", Style::default().fg(Color::Yellow).add_modifier(Modifier::UNDERLINED))),
            Line::from(Span::styled(&issue.description, Style::default().fg(TEXT_LIGHT))),
        ];

        let desc_p = Paragraph::new(desc_text)
            .block(Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(MUTED_BORDER))
                .title(" Vulnerability Description ")
                .title_style(Style::default().fg(TEXT_LIGHT))
                .bg(SLATE_BG))
            .wrap(Wrap { trim: true });
        
        f.render_widget(desc_p, detail_chunks[0]);

        // Comments/Audit Log Box
        let comments_items: Vec<ListItem> = issue
            .comments
            .iter()
            .map(|comment| {
                ListItem::new(Span::styled(comment.clone(), Style::default().fg(TEXT_LIGHT)))
            })
            .collect();

        let comments_list = List::new(comments_items)
            .block(Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(MUTED_BORDER))
                .title(" Agent Audit Log & Comments ")
                .title_style(Style::default().fg(TEXT_LIGHT))
                .bg(SLATE_BG));
        
        f.render_widget(comments_list, detail_chunks[1]);
    }
}

fn draw_hunts_tab(f: &mut Frame, app: &App, rect: Rect) {
    let header_cells = vec!["Hunt Title", "Target Area / Goal", "Bacon Prize Reward", "Status"];
    let header = Row::new(header_cells)
        .style(Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))
        .bottom_margin(1);

    let rows = app.hunts.iter().enumerate().map(|(idx, hunt)| {
        let is_selected = idx == app.selected_hunt_index;
        let cells = vec![
            Cell::from(hunt.name.clone()),
            Cell::from(hunt.description.clone()),
            Cell::from(Span::styled(hunt.reward.clone(), Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD))),
            Cell::from(hunt.status.clone()),
        ];

        let mut row_style = Style::default().fg(TEXT_LIGHT);
        if is_selected {
            row_style = row_style.bg(SLATE_SURFACE).fg(BLT_RED).add_modifier(Modifier::BOLD);
        }

        Row::new(cells).style(row_style)
    });

    let table = Table::new(rows, [
        Constraint::Percentage(25),
        Constraint::Percentage(45),
        Constraint::Percentage(18),
        Constraint::Percentage(12),
    ])
    .header(header)
    .block(Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(MUTED_BORDER))
        .title(" Active Bounty Hunts ")
        .title_style(Style::default().fg(TEXT_LIGHT))
        .bg(SLATE_BG))
    .column_spacing(1);

    f.render_widget(table, rect);
}

fn draw_stats_tab(f: &mut Frame, app: &App, rect: Rect) {
    let horizontal_layout = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(60), Constraint::Percentage(40)])
        .split(rect);

    // Left Panel: Stats Grid
    let vertical_chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(50), Constraint::Percentage(50)])
        .split(horizontal_layout[0]);

    let row_1 = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(50), Constraint::Percentage(50)])
        .split(vertical_chunks[0]);

    let row_2 = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(50), Constraint::Percentage(50)])
        .split(vertical_chunks[1]);

    let widget_style = Style::default().fg(MUTED_BORDER);

    // Card 1
    let card_1 = Paragraph::new(vec![
        Line::from(""),
        Line::from(Span::styled(format!("  {}", app.stats.total_issues), Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD))),
        Line::from("  Total Vulnerabilities Logged"),
    ])
    .block(Block::default().borders(Borders::ALL).border_style(widget_style).title(" Issues Counter ").bg(SLATE_SURFACE));
    f.render_widget(card_1, row_1[0]);

    // Card 2
    let card_2 = Paragraph::new(vec![
        Line::from(""),
        Line::from(Span::styled(format!("  {}", app.stats.active_repos), Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))),
        Line::from("  Tracked Code Repositories"),
    ])
    .block(Block::default().borders(Borders::ALL).border_style(widget_style).title(" Active Repos ").bg(SLATE_SURFACE));
    f.render_widget(card_2, row_1[1]);

    // Card 3
    let card_3 = Paragraph::new(vec![
        Line::from(""),
        Line::from(Span::styled(format!("  {}", app.stats.total_contributors), Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD))),
        Line::from("  Active Community Contributors"),
    ])
    .block(Block::default().borders(Borders::ALL).border_style(widget_style).title(" Contributor Community ").bg(SLATE_SURFACE));
    f.render_widget(card_3, row_2[0]);

    // Card 4
    let card_4 = Paragraph::new(vec![
        Line::from(""),
        Line::from(Span::styled(format!("  {} 🥓", app.stats.bacon_points), Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD))),
        Line::from("  Total Bacon Points Awarded"),
    ])
    .block(Block::default().borders(Borders::ALL).border_style(widget_style).title(" Bacon Economy ").bg(SLATE_SURFACE));
    f.render_widget(card_4, row_2[1]);

    // Right Panel: BLT ASCII Art
    let blt_lines = vec![
        Line::from(""),
        Line::from(""),
        Line::from(""),
        Line::from(""),
        Line::from(Span::styled("  ######   ##       ########  ", Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD))),
        Line::from(Span::styled("  ##   ##  ##          ##     ", Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD))),
        Line::from(Span::styled("  ######   ##          ##     ", Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD))),
        Line::from(Span::styled("  ##   ##  ##          ##     ", Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD))),
        Line::from(Span::styled("  ######   #######     ##     ", Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD))),
        Line::from(""),
    ];

    let blt_p = Paragraph::new(blt_lines)
        .block(Block::default()
            .borders(Borders::ALL)
            .border_style(widget_style)
            .title(" OWASP BLT ")
            .bg(SLATE_BG))
        .alignment(ratatui::layout::Alignment::Center);
    f.render_widget(blt_p, horizontal_layout[1]);
}

fn draw_settings_tab(f: &mut Frame, app: &App, rect: Rect) {
    let mode_str = match app.run_mode {
        RunMode::Offline => "Offline Mode (Mock Data)",
        RunMode::Standalone => "Standalone mode (REST API Connection)",
        RunMode::Mcp => "MCP Client Subprocess Host mode",
    };

    let settings_text = vec![
        Line::from(""),
        Line::from(vec![
            Span::styled("  Execution Mode:     ", Style::default().fg(Color::Gray)),
            Span::styled(mode_str, Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
        ]),
        Line::from(vec![
            Span::styled("  Target BLT API:     ", Style::default().fg(Color::Gray)),
            Span::styled(&app.api_base, Style::default().fg(Color::Cyan)),
        ]),
        Line::from(vec![
            Span::styled("  MCP Server Subpath: ", Style::default().fg(Color::Gray)),
            Span::styled(app.mcp_path.as_deref().unwrap_or("None (Not spawned)"), Style::default().fg(Color::Gray)),
        ]),
        Line::from(vec![
            Span::styled("  Authenticated User: ", Style::default().fg(Color::Gray)),
            Span::styled(&app.auth_user, Style::default().fg(TEXT_LIGHT).add_modifier(Modifier::BOLD)),
        ]),
        Line::from(""),
        Line::from(Span::styled("  To change execution mode, relaunch CLI with flags:", Style::default().fg(Color::DarkGray))),
        Line::from(Span::styled("  - Standalone REST API:   blt-cli --api-base <url>", Style::default().fg(Color::DarkGray))),
        Line::from(Span::styled("  - MCP Subprocess Mode:   blt-cli --mcp-path <path_to_server.py>", Style::default().fg(Color::DarkGray))),
        Line::from(Span::styled("  - Offline Sandbox:       blt-cli --offline", Style::default().fg(Color::DarkGray))),
    ];

    let p = Paragraph::new(settings_text)
        .block(Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(MUTED_BORDER))
            .title(" System Configurations & Auth Status ")
            .title_style(Style::default().fg(TEXT_LIGHT))
            .bg(SLATE_BG));
    f.render_widget(p, rect);
}

fn draw_footer(f: &mut Frame, app: &App, rect: Rect) {
    let footer_chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Length(1), Constraint::Length(2)])
        .split(rect);

    // Status Log bar
    let status_bar = Paragraph::new(Span::styled(format!("  Log: {}", app.status_message), Style::default().fg(TEXT_LIGHT)))
        .bg(SLATE_SURFACE);
    f.render_widget(status_bar, footer_chunks[0]);

    // Controls Legend
    let legend = Paragraph::new(Line::from(vec![
        Span::styled(" [Tab] ", Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD)),
        Span::styled("Next Tab   ", Style::default().fg(TEXT_LIGHT)),
        Span::styled(" [↑/↓] ", Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD)),
        Span::styled("Navigate   ", Style::default().fg(TEXT_LIGHT)),
        Span::styled(" [h] ", Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD)),
        Span::styled("Help Menu   ", Style::default().fg(TEXT_LIGHT)),
        Span::styled(" [t] ", Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD)),
        Span::styled("Triage Issue   ", Style::default().fg(TEXT_LIGHT)),
        Span::styled(" [Esc] ", Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD)),
        Span::styled("Close Dialog   ", Style::default().fg(TEXT_LIGHT)),
        Span::styled(" [q] ", Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD)),
        Span::styled("Quit App", Style::default().fg(TEXT_LIGHT)),
    ]))
    .block(Block::default().bg(SLATE_BG));
    f.render_widget(legend, footer_chunks[1]);
}

fn draw_help_modal(f: &mut Frame, rect: Rect) {
    let help_area = centered_rect(55, 40, rect);
    
    // Clear background space behind help box
    f.render_widget(Clear, help_area);

    let help_text = vec![
        Line::from(""),
        Line::from(Span::styled(" Keyboard Shortcuts Quick Reference", Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD))),
        Line::from(" ────────────────────────────────────────────────"),
        Line::from(vec![
            Span::styled("  Tab / Shift+Tab    ", Style::default().fg(Color::Yellow)),
            Span::styled("Navigate between views", Style::default().fg(TEXT_LIGHT)),
        ]),
        Line::from(vec![
            Span::styled("  Up / Down Arrow    ", Style::default().fg(Color::Yellow)),
            Span::styled("Scroll items in active list/table", Style::default().fg(TEXT_LIGHT)),
        ]),
        Line::from(vec![
            Span::styled("  h / ?              ", Style::default().fg(Color::Yellow)),
            Span::styled("Toggle this help dialog overlay", Style::default().fg(TEXT_LIGHT)),
        ]),
        Line::from(vec![
            Span::styled("  t                  ", Style::default().fg(Color::Yellow)),
            Span::styled("Triage selected issue (requires confirm)", Style::default().fg(TEXT_LIGHT)),
        ]),
        Line::from(vec![
            Span::styled("  Esc                ", Style::default().fg(Color::Yellow)),
            Span::styled("Dismiss any open dialog or modal", Style::default().fg(TEXT_LIGHT)),
        ]),
        Line::from(vec![
            Span::styled("  q / Ctrl+C         ", Style::default().fg(Color::Yellow)),
            Span::styled("Exit/Quit the CLI client securely", Style::default().fg(TEXT_LIGHT)),
        ]),
    ];

    let p = Paragraph::new(help_text)
        .block(Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD))
            .title(" Help Legend Menu ")
            .bg(SLATE_SURFACE));
    
    f.render_widget(p, help_area);
}

fn draw_triage_modal(f: &mut Frame, app: &App, rect: Rect) {
    let modal_area = centered_rect(50, 25, rect);
    f.render_widget(Clear, modal_area);

    if app.issues.is_empty() {
        return;
    }
    
    let issue_id = &app.issues[app.selected_issue_index].id;

    let confirmation_text = vec![
        Line::from(""),
        Line::from(Span::styled("  Manually Confirm Write Triage Action  ", Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD))),
        Line::from(" ──────────────────────────────────────────"),
        Line::from(format!("  Setting Issue #{} Status to 'In Review'!", issue_id)),
        Line::from(""),
        Line::from(Span::styled("  All write operations require human verification.", Style::default().fg(Color::Gray))),
        Line::from(""),
        Line::from(vec![
            Span::styled("  [Enter] ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
            Span::styled("Confirm Triage  |  ", Style::default().fg(TEXT_LIGHT)),
            Span::styled("[Esc] ", Style::default().fg(Color::Red).add_modifier(Modifier::BOLD)),
            Span::styled("Abort Operation", Style::default().fg(TEXT_LIGHT)),
        ]),
    ];

    let p = Paragraph::new(confirmation_text)
        .block(Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD))
            .title(" HUMAN-IN-THE-LOOP VERIFICATION ")
            .bg(SLATE_SURFACE))
        .alignment(ratatui::layout::Alignment::Center);
    
    f.render_widget(p, modal_area);
}

// Helper to center widgets on screen
fn centered_rect(percent_x: u16, percent_y: u16, r: Rect) -> Rect {
    let popup_layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Percentage((100 - percent_y) / 2),
            Constraint::Percentage(percent_y),
            Constraint::Percentage((100 - percent_y) / 2),
        ])
        .split(r);

    Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage((100 - percent_x) / 2),
            Constraint::Percentage(percent_x),
            Constraint::Percentage((100 - percent_x) / 2),
        ])
        .split(popup_layout[1])[1]
}

// Minimal Cell and Cell conversion implementations for simple layout construction
enum Cell {
    Text(String),
    Styled(Span<'static>),
}

impl From<String> for Cell {
    fn from(s: String) -> Self {
        Cell::Text(s)
    }
}

impl From<&str> for Cell {
    fn from(s: &str) -> Self {
        Cell::Text(s.to_string())
    }
}

impl From<Span<'static>> for Cell {
    fn from(span: Span<'static>) -> Self {
        Cell::Styled(span)
    }
}

impl<'a> From<Cell> for ratatui::widgets::Cell<'a> {
    fn from(val: Cell) -> Self {
        match val {
            Cell::Text(s) => ratatui::widgets::Cell::from(s),
            Cell::Styled(span) => ratatui::widgets::Cell::from(span),
        }
    }
}
