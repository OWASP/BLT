//! Markdown Text Parsing and Inline Syntax Highlighting Engine.
//!
//! This module provides customized lightweight Markdown text parsing and syntax
//! highlighting for rendering rich technical vulnerability descriptions, bounty hunt
//! specifications, and AI triage recommendation reports inside Ratatui terminals.
//!
//! Key Functions:
//! - `parse_markdown(text)`: Parses multi-line block Markdown content:
//!   - `# Header` => Bold high-contrast white heading (`BLT_TEXT_HEADING`).
//!   - `## Subheader` => Bold brand red subheader (`BLT_PRIMARY`).
//!   - `- List Item` => Styled red bullet marker (`•`) followed by readable body text.
//! - `parse_inline_markdown(text)`: Parses inline bold markdown tokens (`**text**`) and
//!   dynamically applies semantic severity color highlighting for security keywords:
//!   - `Critical` => Bright Red (`SEVERITY_CRITICAL`).
//!   - `High` => Amber / Orange (`SEVERITY_HIGH`).
//!   - `Medium` => Yellow (`Color::Yellow`).
//!   - `Low` => Green (`Color::Green`).
//!   - Mitigation / Recommendation sections => Brand Red accent highlighting.

use ratatui::{
    style::{Color, Modifier, Style},
    text::{Line, Span},
};

use super::theme::{
    BLT_PRIMARY, BLT_TEXT_BODY, BLT_TEXT_HEADING, SEVERITY_CRITICAL, SEVERITY_HIGH,
};

/// Parses multi-line markdown text with headers and list bullet markers.
pub fn parse_markdown(text: &str) -> Vec<Line<'_>> {
    let mut lines = Vec::new();
    for line in text.lines() {
        if line.starts_with("# ") {
            lines.push(Line::from(Span::styled(
                &line[2..],
                Style::default()
                    .fg(BLT_TEXT_HEADING)
                    .add_modifier(Modifier::BOLD),
            )));
        } else if line.starts_with("## ") {
            lines.push(Line::from(Span::styled(
                &line[3..],
                Style::default()
                    .fg(BLT_PRIMARY)
                    .add_modifier(Modifier::BOLD),
            )));
        } else if line.starts_with("- ") {
            lines.push(Line::from(vec![
                Span::styled(
                    " • ",
                    Style::default()
                        .fg(BLT_PRIMARY)
                        .add_modifier(Modifier::BOLD),
                ),
                Span::styled(&line[2..], Style::default().fg(BLT_TEXT_BODY)),
            ]));
        } else if line.trim().is_empty() {
            lines.push(Line::from(""));
        } else {
            lines.push(Line::from(Span::styled(
                line,
                Style::default().fg(BLT_TEXT_BODY),
            )));
        }
    }
    lines
}

/// Parses inline bold markdown tokens (`**text**`) and highlights vulnerability severities.
pub fn parse_inline_markdown(text: &str) -> Vec<Line<'_>> {
    let mut lines = Vec::new();
    for raw_line in text.lines() {
        let mut spans = Vec::new();
        let trimmed_line = raw_line.trim_start();
        let indent_len = raw_line.len() - trimmed_line.len();
        let indent = " ".repeat(indent_len);

        let mut current_text = trimmed_line;

        if current_text.starts_with("* ") || current_text.starts_with("- ") {
            spans.push(Span::styled(
                format!("{}• ", indent),
                Style::default().fg(BLT_PRIMARY),
            ));
            current_text = &current_text[2..];
        } else if !indent.is_empty() {
            spans.push(Span::raw(indent));
        }

        let parts = current_text.split("**");
        let mut is_bold = false;

        for part in parts {
            if part.is_empty() {
                is_bold = !is_bold;
                continue;
            }

            let trimmed = part.trim();

            let severity_color = match trimmed {
                "Critical" => Some(SEVERITY_CRITICAL),
                "High" => Some(SEVERITY_HIGH),
                "Medium" => Some(Color::Yellow),
                "Low" => Some(Color::Green),
                _ => None,
            };

            if let Some(color) = severity_color {
                spans.push(Span::styled(
                    part.to_string(),
                    Style::default().fg(color).add_modifier(Modifier::BOLD),
                ));
                is_bold = !is_bold;
                continue;
            }

            let mut style = Style::default();
            if is_bold {
                style = style.add_modifier(Modifier::BOLD);
                if part.contains("Severity Suggestion")
                    || part.contains("Recommendation")
                    || part.contains("Mitigation")
                    || part.contains("Input Validation")
                {
                    style = style.fg(BLT_PRIMARY);
                } else {
                    style = style.fg(BLT_TEXT_HEADING);
                }
            } else {
                style = style.fg(BLT_TEXT_BODY);
            }

            spans.push(Span::styled(part.to_string(), style));
            is_bold = !is_bold;
        }

        lines.push(Line::from(spans));
    }
    lines
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

    #[test]
    fn test_severity_plain_critical() {
        let lines = parse_inline_markdown("Critical");
        assert_eq!(lines.len(), 1);
        let spans = &lines[0].spans;
        assert_eq!(spans.len(), 1);
        assert_eq!(spans[0].style.fg, Some(SEVERITY_CRITICAL));
        assert!(spans[0].style.add_modifier.contains(Modifier::BOLD));
    }

    #[test]
    fn test_severity_bold_high() {
        let lines = parse_inline_markdown("**High**");
        assert_eq!(lines.len(), 1);
        let severity_spans: Vec<_> = lines[0]
            .spans
            .iter()
            .filter(|s| s.content.trim() == "High")
            .collect();
        assert_eq!(severity_spans.len(), 1);
        assert_eq!(severity_spans[0].style.fg, Some(SEVERITY_HIGH));
        assert!(severity_spans[0]
            .style
            .add_modifier
            .contains(Modifier::BOLD));
    }

    #[test]
    fn test_severity_bold_medium() {
        let lines = parse_inline_markdown("**Medium**");
        let severity_spans: Vec<_> = lines[0]
            .spans
            .iter()
            .filter(|s| s.content.trim() == "Medium")
            .collect();
        assert_eq!(severity_spans.len(), 1);
        assert_eq!(severity_spans[0].style.fg, Some(Color::Yellow));
    }

    #[test]
    fn test_severity_plain_low() {
        let lines = parse_inline_markdown("Low");
        assert_eq!(lines[0].spans.len(), 1);
        assert_eq!(lines[0].spans[0].style.fg, Some(Color::Green));
    }

    #[test]
    fn test_severity_token_in_mixed_line() {
        let lines = parse_inline_markdown("Severity: **Critical** — patch now");
        let spans = &lines[0].spans;
        let sev = spans
            .iter()
            .find(|s| s.content.trim() == "Critical")
            .expect("severity span");
        assert_eq!(sev.style.fg, Some(SEVERITY_CRITICAL));
        let tail = spans.last().unwrap();
        assert!(!tail.style.add_modifier.contains(Modifier::BOLD));
    }
}
