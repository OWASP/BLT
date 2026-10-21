import 'dart:ui' show FontFeature;

import 'package:flutter/material.dart';

/// OWASP BLT brand tokens, matching the owaspblt.org homepage:
/// BLT red (Tailwind red-600) on neutral Tailwind gray surfaces.
/// Change colours here, not in widgets.
class BLTColors {
  BLTColors._();

  // BLT red
  static const Color primary = Color(0xFFDC2626); // red-600
  static const Color primaryDark = Color(0xFFB91C1C); // red-700 (pressed, dark-mode buttons)
  static const Color primaryOnDark = Color(0xFFEF4444); // red-500 (accent on dark surfaces)
  static const Color primaryLight = Color(0xFFF87171); // red-400 (text on dark surfaces)
  static const Color primarySoft = Color(0xFFFEE2E2); // red-100 (tinted chips)

  // Tailwind gray scale
  static const Color gray50 = Color(0xFFF9FAFB);
  static const Color gray100 = Color(0xFFF3F4F6);
  static const Color gray200 = Color(0xFFE5E7EB);
  static const Color gray300 = Color(0xFFD1D5DB);
  static const Color gray400 = Color(0xFF9CA3AF);
  static const Color gray500 = Color(0xFF6B7280);
  static const Color gray600 = Color(0xFF4B5563);
  static const Color gray700 = Color(0xFF374151);
  static const Color gray800 = Color(0xFF1F2937);
  static const Color gray900 = Color(0xFF111827);
  static const Color gray950 = Color(0xFF030712);

  // Semantic aliases
  static const Color textMuted = gray500;
  static const Color lightBackground = Colors.white;
  static const Color lightSurface = gray50;
  static const Color lightBorder = gray200;
  static const Color darkBackground = gray950; // page
  static const Color darkSurface = gray900; // app bars, cards
  static const Color darkCard = gray800; // raised cards, inputs
  static const Color darkBorder = gray800;
}

/// The app uses the platform's system font (Roboto / San Francisco / Segoe UI),
/// like the homepage's system font stack. These helpers keep the call shape of
/// the GoogleFonts.* functions they replaced, without loading a web font.
class BLTFonts {
  BLTFonts._();

  static TextStyle system({
    TextStyle? textStyle,
    Color? color,
    Color? backgroundColor,
    double? fontSize,
    FontWeight? fontWeight,
    FontStyle? fontStyle,
    double? letterSpacing,
    double? wordSpacing,
    TextBaseline? textBaseline,
    double? height,
    Locale? locale,
    Paint? foreground,
    Paint? background,
    List<Shadow>? shadows,
    List<FontFeature>? fontFeatures,
    TextDecoration? decoration,
    Color? decorationColor,
    TextDecorationStyle? decorationStyle,
    double? decorationThickness,
  }) {
    return (textStyle ?? const TextStyle()).copyWith(
      color: color,
      backgroundColor: backgroundColor,
      fontSize: fontSize,
      fontWeight: fontWeight,
      fontStyle: fontStyle,
      letterSpacing: letterSpacing,
      wordSpacing: wordSpacing,
      textBaseline: textBaseline,
      height: height,
      locale: locale,
      foreground: foreground,
      background: background,
      shadows: shadows,
      fontFeatures: fontFeatures,
      decoration: decoration,
      decorationColor: decorationColor,
      decorationStyle: decorationStyle,
      decorationThickness: decorationThickness,
    );
  }
}
