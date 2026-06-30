use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Clear, List, ListItem, Paragraph, Row, Table, Tabs, Wrap, Sparkline},
    Frame,
};

use crate::app::{App, Tab, RunMode};
use ratatui::style::Stylize;

// Define BLT brand color palette (Modern Catppuccin-inspired)
const BLT_RED: Color = Color::Rgb(243, 139, 168); // Soft Red / Pink
const SLATE_BG: Color = Color::Rgb(36, 39, 58);   // Deep Macchiato Base
const SLATE_SURFACE: Color = Color::Rgb(48, 52, 70); // Surface level 1
const MUTED_BORDER: Color = Color::Rgb(91, 96, 120); // Overlay 1
const TEXT_LIGHT: Color = Color::Rgb(202, 211, 245); // Text
const SEVERITY_CRITICAL: Color = Color::Rgb(237, 135, 150); // Red
const SEVERITY_HIGH: Color = Color::Rgb(245, 169, 127); // Peach

pub fn draw(f: &mut Frame, app: &mut App) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(4), // Header + Stats combined
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
        Tab::Logs => draw_logs_tab(f, app, chunks[1]),
        Tab::Settings => draw_settings_tab(f, app, chunks[1]),
    }

    // 3. Draw Footer / Status Bar
    draw_footer(f, app, chunks[2]);

    // 4. Draw Overlay Modals if active
    match app.active_overlay {
        crate::app::ActiveOverlay::Help => draw_help_modal(f, chunks[1]),
        crate::app::ActiveOverlay::Triage => draw_triage_modal(f, app, chunks[1]),
        crate::app::ActiveOverlay::SubmitForm => draw_submit_form_modal(f, app, chunks[1]),
        crate::app::ActiveOverlay::HuntDetail => draw_hunt_details_modal(f, app, chunks[1]),
        crate::app::ActiveOverlay::AiTriage => draw_ai_triage_modal(f, app, chunks[1]),
        crate::app::ActiveOverlay::BulkTriageConfirm => draw_bulk_triage_modal(f, app, chunks[1]),
        crate::app::ActiveOverlay::CommandPalette => draw_command_palette_modal(f, app, chunks[1]),
        _ => {}
    }
}

fn draw_header(f: &mut Frame, app: &App, rect: Rect) {
    let header_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Length(45), // Title + User + Stats
            Constraint::Min(20),    // Tabs
        ])
        .split(rect);

    let mcp_status = if app.run_mode == crate::app::RunMode::Mcp && app.is_live { "Connected" } else { "Mock Fallback" };
    let open_count = app.issues.iter().filter(|i| i.status != "Resolved").count();
    let crit_count = app.issues.iter().filter(|i| i.severity == "Critical").count();
    let high_count = app.issues.iter().filter(|i| i.severity == "High").count();

    let header_text = vec![
        Line::from(vec![
            Span::styled(" BLT CLI v1.0        ", Style::default().fg(TEXT_LIGHT).add_modifier(Modifier::BOLD)),
            Span::styled(format!("● {}", mcp_status), Style::default().fg(if app.is_live { Color::Green } else { Color::Yellow })),
        ]),
        Line::from(Span::styled(format!(" User: {}", app.auth_user), Style::default().fg(Color::Gray))),
        Line::from(Span::styled(format!(" Open: {}  Critical: {}  High: {}", open_count, crit_count, high_count), Style::default().fg(Color::Gray))),
    ];
    
    let title_p = Paragraph::new(header_text).bg(SLATE_BG);
    f.render_widget(title_p, header_chunks[0]);

    // Tabs Block
    let tab_titles = vec![
        format!("Issues({})", app.issues.len()),
        format!("Hunts({})", app.hunts.len()),
        "Stats".to_string(),
        "Logs".to_string(),
        "Config".to_string(),
    ];
    let tab_index = match app.active_tab {
        Tab::Issues => 0,
        Tab::Hunts => 1,
        Tab::Stats => 2,
        Tab::Logs => 3,
        Tab::Settings => 4,
    };

    let tabs = Tabs::new(tab_titles)
        .select(tab_index)
        .style(Style::default().fg(Color::Gray))
        .highlight_style(Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD))
        .divider(" ");
    
    f.render_widget(tabs, header_chunks[1]);
}

fn draw_issues_tab(f: &mut Frame, app: &App, rect: Rect) {
    let mut main_rect = rect;
    
    // Draw inline search bar if active or populated
    if app.active_overlay == crate::app::ActiveOverlay::SearchInput || !app.search_query.is_empty() {
        let search_layout = Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Length(3), Constraint::Min(0)])
            .split(rect);
            
        let prefix = if app.active_overlay == crate::app::ActiveOverlay::SearchInput { " > " } else { " " };
        let style = if app.active_overlay == crate::app::ActiveOverlay::SearchInput { Style::default().fg(Color::Yellow) } else { Style::default().fg(Color::DarkGray) };
        
        let p = Paragraph::new(format!("{}{}", prefix, app.search_query))
            .block(Block::default().borders(Borders::ALL).border_style(style).title(" Inline Search Filter "));
        
        f.render_widget(p, search_layout[0]);
        main_rect = search_layout[1];
    }

    let horizontal_layout = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(40), Constraint::Percentage(60)])
        .split(main_rect);

    // 1. Draw Issues Table
    let header_cells = vec!["ID", "Repo", "Severity", "Status", "Title"];
    let header = Row::new(header_cells)
        .style(Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))
        .bottom_margin(1);

    let rows = app.issues.iter().enumerate().filter_map(|(idx, issue)| {
        if !app.search_query.is_empty() {
            let q = app.search_query.to_lowercase();
            if !issue.title.to_lowercase().contains(&q) 
                && !issue.repository.to_lowercase().contains(&q)
                && !issue.status.to_lowercase().contains(&q)
                && !issue.severity.to_lowercase().contains(&q)
                && !issue.id.to_lowercase().contains(&q) {
                return None;
            }
        }

        let is_selected = idx == app.selected_issue_index;
        let is_checked = app.selected_issues.contains(&issue.id);
        
        let severity_color = match issue.severity.as_str() {
            "Critical" => SEVERITY_CRITICAL,
            "High" => SEVERITY_HIGH,
            _ => Color::Yellow,
        };

        let severity_badge = match issue.severity.as_str() {
            "Critical" => "🔴 Critical",
            "High" => "🟠 High",
            "Medium" => "🟡 Medium",
            _ => "🟢 Low",
        };

        let truncated_title = if issue.title.chars().count() > 25 {
            format!("{}...", issue.title.chars().take(22).collect::<String>())
        } else {
            issue.title.clone()
        };

        let title_display = if is_selected {
            format!("▶ {}", truncated_title)
        } else if is_checked {
            format!("* {}", truncated_title)
        } else {
            format!("  {}", truncated_title)
        };

        let status_badge = format!("[{}]", issue.status.to_uppercase());

        let cells = vec![
            Cell::from(issue.id.clone()),
            Cell::from(issue.repository.clone()),
            Cell::from(Span::styled(severity_badge, Style::default().fg(severity_color).add_modifier(Modifier::BOLD))),
            Cell::from(status_badge),
            Cell::from(title_display),
        ];

        let mut row_style = Style::default().fg(TEXT_LIGHT);
        if is_selected {
            row_style = row_style.bg(SLATE_SURFACE).fg(BLT_RED).add_modifier(Modifier::BOLD);
        }

        Some(Row::new(cells).style(row_style))
    });

    let table = Table::new(rows, [
        Constraint::Length(5),
        Constraint::Fill(1),
        Constraint::Length(12),
        Constraint::Length(10),
        Constraint::Fill(3),
    ])
    .header(header)
    .block(Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(MUTED_BORDER))
        .title(" Vulnerabilities Log ")
        .title_style(Style::default().fg(TEXT_LIGHT).add_modifier(Modifier::BOLD))
        .bg(SLATE_BG))
    .column_spacing(1);

    f.render_widget(table, horizontal_layout[0]);

    // 2. Draw Selected Issue Details Panel & Activity Panel
    if !app.issues.is_empty() {
        let issue = &app.issues[app.selected_issue_index];
        let right_pane_chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Percentage(60), Constraint::Percentage(40)])
            .split(horizontal_layout[1]);

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
                .title(" Vulnerability Details ")
                .title_style(Style::default().fg(TEXT_LIGHT))
                .bg(SLATE_BG))
            .wrap(Wrap { trim: true });
        
        f.render_widget(desc_p, right_pane_chunks[0]);

        // Recent Activity Box
        let comments_text = app.audit_logs
            .iter()
            .rev()
            .take(20)
            .map(|log| Line::from(Span::styled(log.clone(), Style::default().fg(TEXT_LIGHT))))
            .collect::<Vec<Line>>();

        let comments_p = Paragraph::new(comments_text)
            .block(Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(MUTED_BORDER))
                .title(" Recent Activity ")
                .title_style(Style::default().fg(TEXT_LIGHT))
                .bg(SLATE_BG))
            .wrap(Wrap { trim: true });
        
        f.render_widget(comments_p, right_pane_chunks[1]);
    }
}

fn draw_hunts_tab(f: &mut Frame, app: &App, rect: Rect) {
    let mut main_rect = rect;
    
    // Draw inline search bar if active or populated
    if app.active_overlay == crate::app::ActiveOverlay::SearchInput || !app.search_query.is_empty() {
        let search_layout = Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Length(3), Constraint::Min(0)])
            .split(rect);
            
        let prefix = if app.active_overlay == crate::app::ActiveOverlay::SearchInput { " > " } else { " " };
        let style = if app.active_overlay == crate::app::ActiveOverlay::SearchInput { Style::default().fg(Color::Yellow) } else { Style::default().fg(Color::DarkGray) };
        
        let p = Paragraph::new(format!("{}{}", prefix, app.search_query))
            .block(Block::default().borders(Borders::ALL).border_style(style).title(" Inline Search Filter "));
        
        f.render_widget(p, search_layout[0]);
        main_rect = search_layout[1];
    }

    let horizontal_layout = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(40), Constraint::Percentage(60)])
        .split(main_rect);

    let header_cells = vec!["Hunt Title", "Goal", "Reward", "Status"];
    let header = Row::new(header_cells)
        .style(Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))
        .bottom_margin(1);

    let rows = app.hunts.iter().enumerate().filter_map(|(idx, hunt)| {
        if !app.search_query.is_empty() {
            let q = app.search_query.to_lowercase();
            if !hunt.name.to_lowercase().contains(&q)
                && !hunt.description.to_lowercase().contains(&q)
                && !hunt.status.to_lowercase().contains(&q)
                && !hunt.reward.to_lowercase().contains(&q) {
                return None;
            }
        }

        let is_selected = idx == app.selected_hunt_index;
        
        let truncated_desc = if hunt.description.chars().count() > 25 {
            format!("{}...", hunt.description.chars().take(22).collect::<String>())
        } else {
            hunt.description.clone()
        };

        let title_display = if is_selected {
            format!("▶ {}", hunt.name)
        } else {
            format!("  {}", hunt.name)
        };
        let status_badge = format!("[{}]", hunt.status.to_uppercase());

        let cells = vec![
            Cell::from(title_display),
            Cell::from(truncated_desc),
            Cell::from(Span::styled(hunt.reward.clone(), Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD))),
            Cell::from(status_badge),
        ];

        let mut row_style = Style::default().fg(TEXT_LIGHT);
        if is_selected {
            row_style = row_style.bg(SLATE_SURFACE).fg(BLT_RED).add_modifier(Modifier::BOLD);
        }

        Some(Row::new(cells).style(row_style))
    });

    let table = Table::new(rows, [
        Constraint::Fill(2),
        Constraint::Fill(3),
        Constraint::Length(15),
        Constraint::Length(10),
    ])
    .header(header)
    .block(Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(MUTED_BORDER))
        .title(" Active Bounty Hunts ")
        .title_style(Style::default().fg(TEXT_LIGHT))
        .bg(SLATE_BG))
    .column_spacing(1);

    f.render_widget(table, horizontal_layout[0]);

    if !app.hunts.is_empty() {
        let hunt = &app.hunts[app.selected_hunt_index];

        let desc_text = vec![
            Line::from(vec![
                Span::styled("Hunt: ", Style::default().fg(Color::Gray)),
                Span::styled(&hunt.name, Style::default().fg(TEXT_LIGHT).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::styled("Reward: ", Style::default().fg(Color::Gray)),
                Span::styled(&hunt.reward, Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD)),
                Span::styled("  |  Status: ", Style::default().fg(Color::Gray)),
                Span::styled(format!("[{}]", hunt.status.to_uppercase()), Style::default().fg(Color::Yellow)),
            ]),
            Line::from(""),
            Line::from(Span::styled("Goal / Description:", Style::default().fg(Color::Yellow).add_modifier(Modifier::UNDERLINED))),
            Line::from(Span::styled(&hunt.description, Style::default().fg(TEXT_LIGHT))),
            Line::from(""),
            Line::from(Span::styled("Participants: ", Style::default().fg(Color::Gray))),
            Line::from(Span::styled("• NachiketRoy, shivam, rosai (Mocked)", Style::default().fg(TEXT_LIGHT))),
            Line::from(Span::styled("End Date: ", Style::default().fg(Color::Gray))),
            Line::from(Span::styled("2026-12-31 (Mocked)", Style::default().fg(TEXT_LIGHT))),
            Line::from(Span::styled("Progress: ", Style::default().fg(Color::Gray))),
            Line::from(Span::styled("[█████████░░░░] 65%", Style::default().fg(Color::Green))),
        ];

        let desc_p = Paragraph::new(desc_text)
            .block(Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(MUTED_BORDER))
                .title(" Hunt Details ")
                .title_style(Style::default().fg(TEXT_LIGHT))
                .bg(SLATE_BG))
            .wrap(Wrap { trim: true });
        
        f.render_widget(desc_p, horizontal_layout[1]);
    }
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
    let card_1_chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Length(4), Constraint::Min(2)])
        .split(row_1[0]);

    let card_1_text = Paragraph::new(vec![
        Line::from(""),
        Line::from(Span::styled(format!("  {}", app.stats.total_issues), Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD))),
        Line::from("  Total Issues"),
    ])
    .block(Block::default().borders(Borders::TOP).border_style(widget_style).title(" Issues Counter ").bg(SLATE_SURFACE));
    f.render_widget(card_1_text, card_1_chunks[0]);

    let sparkline_data: [u64; 16] = [12, 18, 5, 2, 8, 14, 19, 7, 22, 15, 8, 10, 14, 25, 12, 9];
    let sparkline = Sparkline::default()
        .block(Block::default().borders(Borders::NONE).bg(SLATE_SURFACE))
        .data(&sparkline_data)
        .style(Style::default().fg(BLT_RED));
    f.render_widget(sparkline, card_1_chunks[1]);

    // Card 2
    let card_2 = Paragraph::new(vec![
        Line::from(""),
        Line::from(Span::styled(format!("  {}", app.stats.active_repos), Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))),
        Line::from("  Active Repos"),
    ])
    .block(Block::default().borders(Borders::TOP).border_style(widget_style).title(" Active Repos ").bg(SLATE_SURFACE));
    f.render_widget(card_2, row_1[1]);

    // Card 3
    let card_3 = Paragraph::new(vec![
        Line::from(""),
        Line::from(Span::styled(format!("  {}", app.stats.total_contributors), Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD))),
        Line::from("  Contributors"),
    ])
    .block(Block::default().borders(Borders::TOP).border_style(widget_style).title(" Contributor Community ").bg(SLATE_SURFACE));
    f.render_widget(card_3, row_2[0]);

    // Card 4
    let card_4 = Paragraph::new(vec![
        Line::from(""),
        Line::from(Span::styled(format!("  {} 🥓", app.stats.bacon_points), Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD))),
        Line::from("  Bacon Points"),
    ])
    .block(Block::default().borders(Borders::TOP).border_style(widget_style).title(" Bacon Economy ").bg(SLATE_SURFACE));
    f.render_widget(card_4, row_2[1]);

    // Right Panel: Live Leaderboard
    let header_cells = vec!["Rank", "Hacker", "Rep", "Bacon Points"];
    let header = Row::new(header_cells)
        .style(Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))
        .bottom_margin(1);

    let rows = app.leaderboard.iter().map(|entry| {
        let rank_color = match entry.rank {
            1 => Color::Rgb(255, 215, 0), // Gold
            2 => Color::Rgb(192, 192, 192), // Silver
            3 => Color::Rgb(205, 127, 50), // Bronze
            _ => TEXT_LIGHT,
        };

        let cells = vec![
            Cell::from(Span::styled(format!("#{}", entry.rank), Style::default().fg(rank_color).add_modifier(Modifier::BOLD))),
            Cell::from(entry.name.clone()),
            Cell::from(entry.reputation.clone()),
            Cell::from(Span::styled(format!("{} 🥓", entry.bacon_points), Style::default().fg(BLT_RED))),
        ];

        Row::new(cells).style(Style::default().fg(TEXT_LIGHT))
    });

    let leaderboard_table = Table::new(rows, [
        Constraint::Length(6),
        Constraint::Percentage(40),
        Constraint::Percentage(30),
        Constraint::Percentage(20),
    ])
    .header(header)
    .block(Block::default()
        .borders(Borders::ALL)
        .border_style(widget_style)
        .title(" Top Contributors ")
        .title_style(Style::default().fg(TEXT_LIGHT).add_modifier(Modifier::BOLD))
        .bg(SLATE_BG))
    .column_spacing(1);

    f.render_widget(leaderboard_table, horizontal_layout[1]);
}

fn draw_settings_tab(f: &mut Frame, app: &App, rect: Rect) {
    let chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(50), Constraint::Percentage(50)])
        .split(rect);

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
    f.render_widget(p, chunks[0]);

    let mut health_text = vec![Line::from("")];
    if let Some(health) = &app.security_health {
        if health.open_backdoor_ports.is_empty() && health.world_writable_paths.is_empty() {
            health_text.push(Line::from(Span::styled(" Host Security Health: PASS", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD))));
            health_text.push(Line::from("  No common backdoor ports or world-writable paths detected."));
        } else {
            health_text.push(Line::from(Span::styled(" Host Security Health: WARNING", Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD))));
            if !health.open_backdoor_ports.is_empty() {
                health_text.push(Line::from(format!("  [!] Open Backdoor Ports Detected: {:?}", health.open_backdoor_ports)));
            }
            if !health.world_writable_paths.is_empty() {
                health_text.push(Line::from("  [!] World-Writable Paths Detected:"));
                for path in &health.world_writable_paths {
                    health_text.push(Line::from(format!("      - {}", path)));
                }
            }
        }
    } else {
        health_text.push(Line::from(Span::styled(" Running Security Health Scan...", Style::default().fg(Color::Yellow))));
    }

    let h = Paragraph::new(health_text)
        .block(Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(MUTED_BORDER))
            .title(" Minimal Security Scanner Core ")
            .title_style(Style::default().fg(TEXT_LIGHT))
            .bg(SLATE_BG));
    f.render_widget(h, chunks[1]);
}

fn draw_footer(f: &mut Frame, app: &App, rect: Rect) {
    let footer_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(20), Constraint::Percentage(40), Constraint::Percentage(40)])
        .split(rect);

    let mode_str = match app.run_mode {
        crate::app::RunMode::Offline => "OFFLINE",
        crate::app::RunMode::Standalone => "API",
        crate::app::RunMode::Mcp => "MCP",
    };

    let status_str = if !app.search_query.is_empty() { format!(" Filter: {} ", app.search_query) } else { format!(" Mode: {} ", mode_str) };

    let left = Paragraph::new(status_str)
        .style(Style::default().fg(Color::DarkGray))
        .block(Block::default().bg(SLATE_BG));
    f.render_widget(left, footer_chunks[0]);

    let middle = Paragraph::new(Span::styled(format!("  {} ", app.status_message), Style::default().fg(TEXT_LIGHT)))
        .block(Block::default().bg(SLATE_SURFACE));
    f.render_widget(middle, footer_chunks[1]);

    let mut legend_spans = vec![
        Span::styled(" [Tab] ", Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD)),
        Span::styled("Tab  ", Style::default().fg(TEXT_LIGHT)),
        Span::styled(" [↑/↓] ", Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD)),
        Span::styled("Nav  ", Style::default().fg(TEXT_LIGHT)),
    ];

    match app.active_tab {
        Tab::Issues => {
            legend_spans.extend(vec![
                Span::styled(" [Space] ", Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD)),
                Span::styled("Select  ", Style::default().fg(TEXT_LIGHT)),
                Span::styled(" [t] ", Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD)),
                Span::styled("Triage  ", Style::default().fg(TEXT_LIGHT)),
                Span::styled(" [a] ", Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD)),
                Span::styled("AI  ", Style::default().fg(TEXT_LIGHT)),
            ]);
        }
        Tab::Hunts => {
            legend_spans.extend(vec![
                Span::styled(" [Enter] ", Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD)),
                Span::styled("Details  ", Style::default().fg(TEXT_LIGHT)),
            ]);
        }
        Tab::Logs => {
            legend_spans.extend(vec![
                Span::styled(" [e] ", Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD)),
                Span::styled("Export  ", Style::default().fg(TEXT_LIGHT)),
            ]);
        }
        _ => {}
    }

    legend_spans.extend(vec![
        Span::styled(" [h] ", Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD)),
        Span::styled("Help  ", Style::default().fg(TEXT_LIGHT)),
        Span::styled(" [q] ", Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD)),
        Span::styled("Quit", Style::default().fg(TEXT_LIGHT)),
    ]);

    let right = Paragraph::new(Line::from(legend_spans))
        .alignment(ratatui::layout::Alignment::Right)
        .block(Block::default().bg(SLATE_BG));
    f.render_widget(right, footer_chunks[2]);
}

fn draw_help_modal(f: &mut Frame, rect: Rect) {
    let help_area = centered_rect(65, 60, rect);
    
    // Clear background space behind help box
    f.render_widget(Clear, help_area);

    let rows = vec![
        Row::new(vec![
            Cell::from(Span::styled("Tab / Shift+Tab", Style::default().fg(Color::Yellow))),
            Cell::from(Span::styled("Navigate between views", Style::default().fg(TEXT_LIGHT))),
        ]),
        Row::new(vec![
            Cell::from(Span::styled("Up / Down Arrow", Style::default().fg(Color::Yellow))),
            Cell::from(Span::styled("Scroll items in active list/table", Style::default().fg(TEXT_LIGHT))),
        ]),
        Row::new(vec![
            Cell::from(Span::styled("h / ?", Style::default().fg(Color::Yellow))),
            Cell::from(Span::styled("Toggle this help dialog overlay", Style::default().fg(TEXT_LIGHT))),
        ]),
        Row::new(vec![
            Cell::from(Span::styled("/", Style::default().fg(Color::Yellow))),
            Cell::from(Span::styled("Open Search / Filter overlay", Style::default().fg(TEXT_LIGHT))),
        ]),
        Row::new(vec![
            Cell::from(Span::styled("Space", Style::default().fg(Color::Yellow))),
            Cell::from(Span::styled("Select/Deselect issue for Bulk Triage", Style::default().fg(TEXT_LIGHT))),
        ]),
        Row::new(vec![
            Cell::from(Span::styled("t", Style::default().fg(Color::Yellow))),
            Cell::from(Span::styled("Triage selected (or Bulk if multiple)", Style::default().fg(TEXT_LIGHT))),
        ]),
        Row::new(vec![
            Cell::from(Span::styled("a", Style::default().fg(Color::Yellow))),
            Cell::from(Span::styled("Trigger AI-Assisted Triage (requires MCP)", Style::default().fg(TEXT_LIGHT))),
        ]),
        Row::new(vec![
            Cell::from(Span::styled("s / Enter", Style::default().fg(Color::Yellow))),
            Cell::from(Span::styled("Submit Vuln / View active Hunt details", Style::default().fg(TEXT_LIGHT))),
        ]),
        Row::new(vec![
            Cell::from(Span::styled("e", Style::default().fg(Color::Yellow))),
            Cell::from(Span::styled("Export session logs (when in Logs tab)", Style::default().fg(TEXT_LIGHT))),
        ]),
        Row::new(vec![
            Cell::from(Span::styled("Esc", Style::default().fg(Color::Yellow))),
            Cell::from(Span::styled("Dismiss any open dialog or modal", Style::default().fg(TEXT_LIGHT))),
        ]),
        Row::new(vec![
            Cell::from(Span::styled("q / Ctrl+C", Style::default().fg(Color::Yellow))),
            Cell::from(Span::styled("Exit/Quit the CLI client securely", Style::default().fg(TEXT_LIGHT))),
        ]),
    ];

    let table = Table::new(rows, [Constraint::Length(20), Constraint::Min(40)])
        .block(Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD))
            .title(" Keyboard Shortcuts Quick Reference ")
            .bg(SLATE_SURFACE))
        .column_spacing(2);
    
    f.render_widget(table, help_area);
}

fn draw_triage_modal(f: &mut Frame, app: &App, rect: Rect) {
    let modal_area = centered_rect(65, 35, rect);
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
        .alignment(ratatui::layout::Alignment::Center)
        .wrap(Wrap { trim: false });
    
    f.render_widget(p, modal_area);
}

fn draw_submit_form_modal(f: &mut Frame, app: &App, rect: Rect) {
    let modal_area = centered_rect(80, 70, rect);
    f.render_widget(Clear, modal_area);

    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3), // URL
            Constraint::Length(3), // Severity
            Constraint::Min(5),    // Description
            Constraint::Length(3), // Instructions
        ])
        .margin(1)
        .split(modal_area);

    let block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD))
        .title(" Submit New Vulnerability ")
        .bg(SLATE_SURFACE);
    f.render_widget(block, modal_area);

    let active = &app.submit_form.active_field;

    let style_active = Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD);
    let style_inactive = Style::default().fg(MUTED_BORDER);

    // URL Field
    let url_style = if *active == crate::app::FormField::Url { style_active } else { style_inactive };
    let url_text = if *active == crate::app::FormField::Url { format!("{}█", app.submit_form.url) } else { app.submit_form.url.clone() };
    let url_p = Paragraph::new(url_text)
        .block(Block::default().borders(Borders::ALL).border_style(url_style).title(" Vulnerable URL * (e.g. https://api.owaspblt.org/login) "));
    f.render_widget(url_p, chunks[0]);

    // Severity Field
    let sev_style = if *active == crate::app::FormField::Severity { style_active } else { style_inactive };
    let sev_text = if *active == crate::app::FormField::Severity { format!("{}█", app.submit_form.severity) } else { app.submit_form.severity.clone() };
    let sev_p = Paragraph::new(sev_text)
        .block(Block::default().borders(Borders::ALL).border_style(sev_style).title(" Severity (Low/Medium/High/Critical) "));
    f.render_widget(sev_p, chunks[1]);

    // Description Field
    let desc_style = if *active == crate::app::FormField::Description { style_active } else { style_inactive };
    let desc_text = if *active == crate::app::FormField::Description { format!("{}█", app.submit_form.description) } else { app.submit_form.description.clone() };
    let desc_p = Paragraph::new(desc_text)
        .block(Block::default().borders(Borders::ALL).border_style(desc_style).title(" Description & Steps to Reproduce * "))
        .wrap(Wrap { trim: false });
    f.render_widget(desc_p, chunks[2]);

    // Instructions
    let instr_p = Paragraph::new(Line::from(vec![
        Span::styled("[Tab] ", Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD)),
        Span::styled("Next Field  |  ", Style::default().fg(TEXT_LIGHT)),
        Span::styled("[Enter] ", Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD)),
        Span::styled("Newline/Next  |  ", Style::default().fg(TEXT_LIGHT)),
        Span::styled("[Ctrl+S] ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
        Span::styled("Submit Report  |  ", Style::default().fg(TEXT_LIGHT)),
        Span::styled("[Esc] ", Style::default().fg(Color::Gray).add_modifier(Modifier::BOLD)),
        Span::styled("Cancel", Style::default().fg(TEXT_LIGHT)),
    ]))
    .alignment(ratatui::layout::Alignment::Center);
    f.render_widget(instr_p, chunks[3]);
}

fn parse_markdown(text: &str) -> Vec<Line<'_>> {
    let mut lines = Vec::new();
    for line in text.lines() {
        if line.starts_with("# ") {
            lines.push(Line::from(Span::styled(&line[2..], Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))));
        } else if line.starts_with("## ") {
            lines.push(Line::from(Span::styled(&line[3..], Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD))));
        } else if line.starts_with("- ") {
            lines.push(Line::from(vec![
                Span::styled(" • ", Style::default().fg(BLT_RED)),
                Span::styled(&line[2..], Style::default().fg(TEXT_LIGHT)),
            ]));
        } else if line.trim().is_empty() {
            lines.push(Line::from(""));
        } else {
            lines.push(Line::from(Span::styled(line, Style::default().fg(TEXT_LIGHT))));
        }
    }
    lines
}

fn draw_hunt_details_modal(f: &mut Frame, app: &App, rect: Rect) {
    let modal_area = centered_rect(60, 60, rect);
    f.render_widget(Clear, modal_area);

    if app.hunts.is_empty() {
        return;
    }

    let hunt = &app.hunts[app.selected_hunt_index];

    let mut lines = vec![
        Line::from(""),
        Line::from(vec![
            Span::styled(" Name: ", Style::default().fg(Color::Gray)),
            Span::styled(hunt.name.clone(), Style::default().fg(TEXT_LIGHT).add_modifier(Modifier::BOLD)),
        ]),
        Line::from(vec![
            Span::styled(" Status: ", Style::default().fg(Color::Gray)),
            Span::styled(hunt.status.clone(), Style::default().fg(Color::Green)),
        ]),
        Line::from(vec![
            Span::styled(" Reward: ", Style::default().fg(Color::Gray)),
            Span::styled(hunt.reward.clone(), Style::default().fg(BLT_RED).add_modifier(Modifier::BOLD)),
        ]),
        Line::from(""),
        Line::from(Span::styled(" Description:", Style::default().fg(Color::Yellow))),
        Line::from(""),
    ];

    let mut parsed_desc = parse_markdown(&hunt.description);
    lines.append(&mut parsed_desc);
    
    lines.push(Line::from(""));
    lines.push(Line::from(" ──────────────────────────────────────────"));
    lines.push(Line::from(vec![
        Span::styled(" [s] ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
        Span::styled("Report Bug for Hunt  |  ", Style::default().fg(TEXT_LIGHT)),
        Span::styled("[Esc] ", Style::default().fg(Color::Gray).add_modifier(Modifier::BOLD)),
        Span::styled("Close", Style::default().fg(TEXT_LIGHT)),
    ]));

    let p = Paragraph::new(lines)
        .block(Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(BLT_RED))
            .title(" Active Bounty Hunt Details ")
            .bg(SLATE_SURFACE))
        .wrap(Wrap { trim: false });

    f.render_widget(p, modal_area);
}

fn draw_ai_triage_modal(f: &mut Frame, app: &App, rect: Rect) {
    let modal_area = centered_rect(60, 50, rect);
    f.render_widget(Clear, modal_area);

    let content = app.ai_triage_result.clone().unwrap_or_else(|| "Waiting for AI response...".to_string());

    let lines: Vec<Line> = content.split('\n').map(|s| Line::from(Span::styled(s.to_string(), Style::default().fg(TEXT_LIGHT)))).collect();

    let p = Paragraph::new(lines)
        .block(Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::Cyan))
            .title(" MCP AI-Assisted Triage Analysis ")
            .bg(SLATE_SURFACE))
        .wrap(Wrap { trim: false });

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

fn draw_logs_tab(f: &mut Frame, app: &App, rect: Rect) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(50), Constraint::Percentage(50)])
        .split(rect);

    let audit_items: Vec<ListItem> = app.audit_logs.iter()
        .map(|log| ListItem::new(Line::from(Span::styled(log, Style::default().fg(Color::Yellow)))))
        .collect();
    let audit_list = List::new(audit_items)
        .block(Block::default().borders(Borders::ALL).title(" Audit Log  (Press [e] to Export) "));
    f.render_widget(audit_list, chunks[0]);

    let event_items: Vec<ListItem> = app.event_feed.iter()
        .map(|ev| ListItem::new(Line::from(Span::styled(ev, Style::default().fg(Color::Cyan)))))
        .collect();
    let event_list = List::new(event_items)
        .block(Block::default().borders(Borders::ALL).title(" Real-Time Event Feed "));
    f.render_widget(event_list, chunks[1]);
}


fn draw_bulk_triage_modal(f: &mut Frame, app: &App, rect: Rect) {
    let area = centered_rect(50, 20, rect);
    f.render_widget(Clear, area);
    
    let text = vec![
        Line::from(""),
        Line::from(format!("  Bulk Triaging {} Selected Issues", app.selected_issues.len())),
        Line::from(""),
        Line::from(format!("  Target Status: [{}]", app.triage_target_status)),
        Line::from(""),
        Line::from("  [1] Open  [2] In Review  [3] Resolved"),
        Line::from(""),
        Line::from("  [Enter] Confirm  [Esc] Cancel"),
    ];
    let p = Paragraph::new(text)
        .block(Block::default().borders(Borders::ALL).title(" Bulk Triage ").border_style(Style::default().fg(Color::Red)));
    f.render_widget(p, area);
}

fn draw_command_palette_modal(f: &mut Frame, app: &App, rect: Rect) {
    let modal_area = centered_rect(50, 10, rect);
    f.render_widget(Clear, modal_area);
    
    let text = format!("> {}█", app.command_input);
    let p = Paragraph::new(Span::styled(text, Style::default().fg(Color::Yellow)))
        .block(Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(BLT_RED))
            .title(" Command Palette ")
            .bg(SLATE_SURFACE));
    
    f.render_widget(p, modal_area);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_markdown() {
        let text = "# Header\n## Subheader\n- List item\nNormal text";
        let lines = parse_markdown(text);
        assert_eq!(lines.len(), 4);
    }
}
