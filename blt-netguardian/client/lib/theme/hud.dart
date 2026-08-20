/// Triage HUD tokens — match `public/triage.html` :root.
library;

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class Hud {
  static const bg = Color(0xFF0A0A0A);
  static const panel = Color(0xFF0D0000);
  static const panelHi = Color(0xFF1A0000);
  static const border = Color(0xFFCC0000);
  static const accent = Color(0xFFFF2020);
  static const gold = Color(0xFFFFAA00);
  static const high = Color(0xFFFF8C00);
  static const medium = Color(0xFFFFD700);
  static const low = Color(0xFF22C55E);
  static const muted = Color(0xFF888888);
  static const text = Color(0xFFFFFFFF);

  static Color severity(String raw) {
    switch (raw.toLowerCase()) {
      case 'critical':
        return accent;
      case 'high':
        return high;
      case 'medium':
        return medium;
      case 'low':
        return low;
      default:
        return muted;
    }
  }

  static ThemeData theme() {
    final mono = GoogleFonts.shareTechMonoTextTheme(
      ThemeData.dark().textTheme,
    ).apply(bodyColor: text, displayColor: text);
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: bg,
      colorScheme: const ColorScheme.dark(
        primary: accent,
        secondary: gold,
        surface: panel,
        onSurface: text,
        error: accent,
      ),
      textTheme: mono,
      appBarTheme: AppBarTheme(
        backgroundColor: bg,
        foregroundColor: accent,
        elevation: 0,
        titleTextStyle: GoogleFonts.orbitron(
          color: accent,
          fontWeight: FontWeight.w800,
          fontSize: 18,
          letterSpacing: 4,
        ),
      ),
      inputDecorationTheme: const InputDecorationTheme(
        filled: true,
        fillColor: bg,
        isDense: true,
        labelStyle: TextStyle(color: muted, fontSize: 12, letterSpacing: 1.2),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.zero,
          borderSide: BorderSide(color: border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.zero,
          borderSide: BorderSide(color: border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.zero,
          borderSide: BorderSide(color: accent, width: 1.4),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: const Color(0x33FF2020),
          foregroundColor: text,
          side: const BorderSide(color: accent),
          shape: const RoundedRectangleBorder(borderRadius: BorderRadius.zero),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: gold,
          side: const BorderSide(color: gold),
          shape: const RoundedRectangleBorder(borderRadius: BorderRadius.zero),
        ),
      ),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith(
          (s) => s.contains(WidgetState.selected) ? accent : muted,
        ),
        trackColor: WidgetStateProperty.resolveWith(
          (s) => s.contains(WidgetState.selected)
              ? const Color(0x66FF2020)
              : const Color(0xFF333333),
        ),
      ),
      checkboxTheme: CheckboxThemeData(
        fillColor: WidgetStateProperty.resolveWith(
          (s) => s.contains(WidgetState.selected) ? accent : Colors.transparent,
        ),
        side: const BorderSide(color: border),
      ),
    );
  }
}

class HudPanel extends StatelessWidget {
  const HudPanel({super.key, required this.title, required this.children});

  final String title;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Hud.panel,
      child: Container(
        decoration: BoxDecoration(
          border: Border.all(color: Hud.border),
        ),
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              title.toUpperCase(),
              style: GoogleFonts.orbitron(
                color: Hud.accent,
                fontSize: 11,
                letterSpacing: 2.4,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 12),
            ...children,
          ],
        ),
      ),
    );
  }
}

class SeverityChip extends StatelessWidget {
  const SeverityChip(this.severity, {super.key});
  final String severity;

  @override
  Widget build(BuildContext context) {
    final color = Hud.severity(severity);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        border: Border.all(color: color),
      ),
      child: Text(
        severity.toUpperCase(),
        style: TextStyle(color: color, fontSize: 10, letterSpacing: 1.2),
      ),
    );
  }
}
