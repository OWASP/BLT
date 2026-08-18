//! Official OWASP BLT Foundations Design Theme Tokens and Color Palette.
//!
//! This module defines the complete design token library for the OWASP BLT Terminal UI (TUI).
//! It adheres strictly to the official OWASP BLT Foundations Design Guidelines, implementing
//! a pure neutral dark canvas (`#0D0F12`), slate card panels (`#16181C`), subtle neutral
//! borders (`#2C2E36`), crisp high-contrast typography (`#FAFAFA`), and brand red (`#E10101`)
//! accents for focused intent and active navigation.
//!
//! Design Rules:
//! - Brand Red (`BLT_PRIMARY` `#E10101`) is reserved for intent, active navigation highlights,
//!   selection indicator bars (`▎`), and form focus states.
//! - Dark backgrounds avoid bluish cast by utilizing true neutral charcoal / carbon hues.
//! - High text contrast: headings on `BLT_TEXT_HEADING`, readable body copy on `BLT_TEXT_BODY`,
//!   and secondary metadata on `BLT_TEXT_MUTED`.

use ratatui::style::Color;

// Primary Brand & Interactive Tokens
#[allow(dead_code)]
pub const BLT_PRIMARY: Color = Color::Rgb(225, 1, 1); // #E10101 - Primary action, active nav, focused brand states
#[allow(dead_code)]
pub const BLT_PRIMARY_HOVER: Color = Color::Rgb(185, 28, 28); // #B91C1C - Destructive emphasis & hover
#[allow(dead_code)]
pub const BLT_ACTIVE_ACCENT: Color = Color::Rgb(254, 234, 233); // #feeae9 - Active chip / light accent

// Neutral Dark Surface & Layout Tokens (True Deep Dark Charcoal / Black - Zero Blue Tint)
pub const DARK_BASE: Color = Color::Rgb(13, 15, 18); // #0D0F12 - Pure deep neutral dark background
pub const DARK_SURFACE: Color = Color::Rgb(22, 24, 28); // #16181C - Neutral dark cards, sidebars, and panels
pub const DARK_SURFACE_ALT: Color = Color::Rgb(28, 30, 35); // #1C1E23 - Subtle alternate row & card surface
pub const DARK_CARD_SELECTED: Color = Color::Rgb(38, 40, 48); // #262830 - Active selected row background
pub const DARK_BORDER: Color = Color::Rgb(44, 46, 54); // #2C2E36 - Clean neutral border without blue tint

// Typography & Contrast Tokens
pub const BLT_TEXT_HEADING: Color = Color::Rgb(250, 250, 250); // #FAFAFA - Crisp high-contrast white headings
pub const BLT_TEXT_BODY: Color = Color::Rgb(225, 226, 230); // #E1E2E6 - Readable product copy
pub const BLT_TEXT_MUTED: Color = Color::Rgb(150, 152, 158); // #96989E - Supporting copy & secondary labels
pub const BLT_TEXT_DIM: Color = Color::Rgb(100, 102, 108); // #64666C - Subtle hints & keybindings

// Status & Severity Semantics
pub const SEVERITY_CRITICAL: Color = Color::Rgb(239, 68, 68); // #EF4444 - Critical
pub const SEVERITY_HIGH: Color = Color::Rgb(245, 158, 11); // #F59E0B - High
pub const SEVERITY_MEDIUM: Color = Color::Rgb(59, 130, 246); // #3B82F6 - Medium
pub const SEVERITY_LOW: Color = Color::Rgb(16, 185, 129); // #10B981 - Low

pub const STATUS_RESOLVED: Color = Color::Rgb(16, 185, 129); // #10B981 - Resolved / Success
pub const STATUS_IN_REVIEW: Color = Color::Rgb(245, 158, 11); // #F59E0B - In Review / Amber
pub const STATUS_PENDING: Color = Color::Rgb(245, 158, 11); // #F59E0B - Pending / Warning
