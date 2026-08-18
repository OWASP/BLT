//! UI Helper Widgets, Geometry Calculations, and Cell Conversion Adapters.
//!
//! This module provides reusable layout utilities and type converters for Ratatui widgets.
//!
//! Key Utilities:
//! - `centered_rect(percent_x, percent_y, rect)`: Calculates a proportional centered
//!   `Rect` sub-area within a parent bounding box, enforcing minimum readable dimensions
//!   (60 width x 18 height) to prevent popup clipping on smaller terminal viewports.
//! - `Cell<'a>`: Multi-variant lifetime adapter enum allowing `String`, `Span<'a>`, and `Line<'a>`
//!   to be converted uniformly into `ratatui::widgets::Cell<'a>` without lifetime mismatch errors.

use ratatui::{
    layout::Rect,
    text::{Line, Span},
};

/// Helper to calculate a centered rectangle on screen with minimum constraints.
pub fn centered_rect(percent_x: u16, percent_y: u16, r: Rect) -> Rect {
    let mut w = (r.width as u32 * percent_x as u32 / 100) as u16;
    let mut h = (r.height as u32 * percent_y as u32 / 100) as u16;

    let min_w = 60.min(r.width);
    let min_h = 18.min(r.height);

    if w < min_w {
        w = min_w;
    }
    if h < min_h {
        h = min_h;
    }

    let x = r.x + (r.width.saturating_sub(w)) / 2;
    let y = r.y + (r.height.saturating_sub(h)) / 2;

    Rect::new(x, y, w, h)
}

/// Generic Cell abstraction allowing Strings, Spans, and composite Lines.
pub enum Cell<'a> {
    Text(String),
    Styled(Span<'a>),
    Line(Line<'a>),
}

impl<'a> From<String> for Cell<'a> {
    fn from(s: String) -> Self {
        Cell::Text(s)
    }
}

impl<'a> From<&str> for Cell<'a> {
    fn from(s: &str) -> Self {
        Cell::Text(s.to_string())
    }
}

impl<'a> From<Span<'a>> for Cell<'a> {
    fn from(span: Span<'a>) -> Self {
        Cell::Styled(span)
    }
}

impl<'a> From<Line<'a>> for Cell<'a> {
    fn from(line: Line<'a>) -> Self {
        Cell::Line(line)
    }
}

impl<'a> From<Cell<'a>> for ratatui::widgets::Cell<'a> {
    fn from(val: Cell<'a>) -> Self {
        match val {
            Cell::Text(s) => ratatui::widgets::Cell::from(s),
            Cell::Styled(span) => ratatui::widgets::Cell::from(span),
            Cell::Line(line) => ratatui::widgets::Cell::from(line),
        }
    }
}
