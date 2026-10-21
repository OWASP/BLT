import 'package:blt/src/util/brand.dart';
import 'package:flutter/material.dart';

/// Light and dark themes built from the BLT brand tokens (see brand.dart):
/// BLT red on white / gray-50 in light mode, gray-950 / gray-900 in dark mode,
/// system font, cards with a gray-200 / gray-800 border.
class AppTheme {
  static final ThemeData lightTheme = _build(
    ThemeData(useMaterial3: true, brightness: Brightness.light),
    ColorScheme.fromSeed(
      seedColor: BLTColors.primary,
      brightness: Brightness.light,
    ).copyWith(
      primary: BLTColors.primary,
      onPrimary: Colors.white,
      primaryContainer: BLTColors.primarySoft,
      onPrimaryContainer: BLTColors.primaryDark,
      secondary: BLTColors.primaryDark,
      onSecondary: Colors.white,
      error: BLTColors.primaryDark,
      surface: Colors.white,
      onSurface: BLTColors.gray900,
      onSurfaceVariant: BLTColors.gray500,
      surfaceContainerLowest: Colors.white,
      surfaceContainerLow: BLTColors.gray50,
      surfaceContainer: BLTColors.gray50,
      surfaceContainerHigh: BLTColors.gray100,
      surfaceContainerHighest: BLTColors.gray100,
      surfaceTint: Colors.transparent,
      outline: BLTColors.gray300,
      outlineVariant: BLTColors.gray200,
    ),
    scaffold: Colors.white,
    bar: Colors.white,
    card: Colors.white,
    border: BLTColors.lightBorder,
  );

  static final ThemeData darkTheme = _build(
    ThemeData.dark(useMaterial3: true),
    ColorScheme.fromSeed(
      seedColor: BLTColors.primary,
      brightness: Brightness.dark,
    ).copyWith(
      primary: BLTColors.primaryOnDark,
      onPrimary: Colors.white,
      primaryContainer: BLTColors.primaryDark,
      onPrimaryContainer: Colors.white,
      secondary: BLTColors.primaryLight,
      onSecondary: BLTColors.gray950,
      error: BLTColors.primaryLight,
      surface: BLTColors.gray900,
      onSurface: BLTColors.gray100,
      onSurfaceVariant: BLTColors.gray400,
      surfaceContainerLowest: BLTColors.gray950,
      surfaceContainerLow: BLTColors.gray900,
      surfaceContainer: BLTColors.gray900,
      surfaceContainerHigh: BLTColors.gray800,
      surfaceContainerHighest: BLTColors.gray800,
      surfaceTint: Colors.transparent,
      outline: BLTColors.gray700,
      outlineVariant: BLTColors.gray800,
    ),
    scaffold: BLTColors.darkBackground,
    bar: BLTColors.darkSurface,
    card: BLTColors.darkSurface,
    border: BLTColors.darkBorder,
  );

  static ThemeData _build(
    ThemeData base,
    ColorScheme scheme, {
    required Color scaffold,
    required Color bar,
    required Color card,
    required Color border,
  }) {
    return base.copyWith(
      colorScheme: scheme,
      primaryColor: scheme.primary,
      scaffoldBackgroundColor: scaffold,
      canvasColor: scaffold,
      dividerColor: border,
      visualDensity: VisualDensity.adaptivePlatformDensity,
      appBarTheme: AppBarTheme(
        backgroundColor: bar,
        foregroundColor: scheme.onSurface,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
      ),
      cardTheme: CardThemeData(
        color: card,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: border),
        ),
      ),
      dividerTheme: DividerThemeData(color: border),
      drawerTheme: DrawerThemeData(backgroundColor: scaffold),
      progressIndicatorTheme:
          ProgressIndicatorThemeData(color: scheme.primary),
      textSelectionTheme: TextSelectionThemeData(
        cursorColor: scheme.primary,
        selectionHandleColor: scheme.primary,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: BLTColors.primary,
          foregroundColor: Colors.white,
        ),
      ),
      floatingActionButtonTheme: FloatingActionButtonThemeData(
        backgroundColor: BLTColors.primary,
        foregroundColor: Colors.white,
      ),
    );
  }
}
