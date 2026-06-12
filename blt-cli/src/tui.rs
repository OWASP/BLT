use std::io;
use std::time::{Duration, Instant};

use crossterm::event::{self, Event, KeyCode, KeyEvent, KeyModifiers};
use ratatui::{backend::Backend, Terminal};

use crate::app::{App, Tab};
use crate::ui;

pub fn run_app<B: Backend>(terminal: &mut Terminal<B>, mut app: App) -> io::Result<()> {
    let tick_rate = Duration::from_millis(100);
    let mut last_tick = Instant::now();

    loop {
        terminal.draw(|f| ui::draw(f, &mut app))?;

        let timeout = tick_rate
            .checked_sub(last_tick.elapsed())
            .unwrap_or_else(|| Duration::from_secs(0));

        if event::poll(timeout)? {
            if let Event::Key(key) = event::read()? {
                // Handle key inputs
                handle_keys(key, &mut app);
            }
        }

        if last_tick.elapsed() >= tick_rate {
            last_tick = Instant::now();
        }

        if app.should_quit {
            return Ok(());
        }
    }
}

fn handle_keys(key: KeyEvent, app: &mut App) {
    // Check for global quit key
    if key.code == KeyCode::Char('q') && !app.show_triage_modal {
        app.should_quit = true;
        return;
    }
    if key.code == KeyCode::Char('c') && key.modifiers.contains(KeyModifiers::CONTROL) {
        app.should_quit = true;
        return;
    }

    // Modal check redirects
    if app.show_help {
        if key.code == KeyCode::Esc || key.code == KeyCode::Char(' ') || key.code == KeyCode::Char('h') || key.code == KeyCode::Char('?') {
            app.show_help = false;
        }
        return;
    }

    if app.show_triage_modal {
        match key.code {
            KeyCode::Enter => {
                app.confirm_triage();
            }
            KeyCode::Esc => {
                app.show_triage_modal = false;
                app.status_message = "Triage write operation cancelled.".to_string();
            }
            _ => {}
        }
        return;
    }

    // Navigation and normal operations
    match key.code {
        KeyCode::Tab => app.next_tab(),
        KeyCode::BackTab => app.prev_tab(),
        
        // Tab numeric shortcuts
        KeyCode::Char('1') => {
            app.active_tab = Tab::Issues;
            app.status_message = "Switched to tab: Issues".to_string();
        }
        KeyCode::Char('2') => {
            app.active_tab = Tab::Hunts;
            app.status_message = "Switched to tab: Active Hunts".to_string();
        }
        KeyCode::Char('3') => {
            app.active_tab = Tab::Stats;
            app.status_message = "Switched to tab: BLT Stats".to_string();
        }
        KeyCode::Char('4') => {
            app.active_tab = Tab::Settings;
            app.status_message = "Switched to tab: Settings".to_string();
        }

        // List Scrolling
        KeyCode::Down | KeyCode::Char('j') => app.scroll_down(),
        KeyCode::Up | KeyCode::Char('k') => app.scroll_up(),

        // Dialog overlays
        KeyCode::Char('h') | KeyCode::Char('?') => app.toggle_help(),
        KeyCode::Char('t') => app.trigger_triage(),
        
        KeyCode::Esc => app.close_popups(),
        _ => {}
    }
}
