import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

/// Visual tokens shared with the BLT Vanish web client.
class BltColors {
  const BltColors._();

  /// Website red: `#dc2626`.
  static const red = Color(0xFFDC2626);

  /// Website coral: `#ef4444`.
  static const coral = Color(0xFFEF4444);

  /// Website ink: `#111827`.
  static const ink = Color(0xFF111827);

  /// Website gray page background: Tailwind `gray-50`.
  static const canvas = Color(0xFFF9FAFB);

  /// Website border gray: Tailwind `gray-200`.
  static const border = Color(0xFFE5E7EB);

  /// Muted body copy.
  static const muted = Color(0xFF6B7280);

  /// Red-tinted surface used for icon boxes and badges.
  static const redTint = Color(0xFFFEF2F2);
}

/// Flutter theme matched to the BLT Vanish web landing page.
class BltTheme {
  const BltTheme._();

  /// Light theme equivalent of the website's white/gray/red visual system.
  static ThemeData light() {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: BltColors.red,
      brightness: Brightness.light,
      primary: BltColors.red,
      secondary: BltColors.coral,
      surface: Colors.white,
      error: BltColors.red,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: BltColors.canvas,
      fontFamily: 'Geist',
      textTheme: const TextTheme(
        displayLarge: TextStyle(
          color: BltColors.ink,
          fontSize: 58,
          fontWeight: FontWeight.w800,
          letterSpacing: -2.4,
          height: 0.98,
        ),
        headlineMedium: TextStyle(
          color: BltColors.ink,
          fontSize: 30,
          fontWeight: FontWeight.w700,
          letterSpacing: -1.1,
          height: 1.05,
        ),
        headlineSmall: TextStyle(
          color: BltColors.ink,
          fontSize: 24,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.7,
        ),
        titleLarge: TextStyle(
          color: BltColors.ink,
          fontSize: 18,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.2,
        ),
        titleMedium: TextStyle(
          color: BltColors.ink,
          fontSize: 16,
          fontWeight: FontWeight.w700,
        ),
        bodyLarge: TextStyle(
          color: BltColors.muted,
          fontSize: 16,
          height: 1.6,
        ),
        bodyMedium: TextStyle(
          color: BltColors.muted,
          fontSize: 14,
          height: 1.55,
        ),
        bodySmall: TextStyle(
          color: BltColors.muted,
          fontSize: 12,
          height: 1.45,
        ),
      ),
      appBarTheme: const AppBarTheme(
        centerTitle: false,
        elevation: 0,
        scrolledUnderElevation: 0,
        backgroundColor: Color(0xEEFFFFFF),
        foregroundColor: BltColors.ink,
        titleTextStyle: TextStyle(
          color: BltColors.ink,
          fontFamily: 'Geist',
          fontSize: 16,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.2,
        ),
        iconTheme: IconThemeData(color: BltColors.ink),
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        color: Colors.white,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: const BorderSide(color: BltColors.border),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 14,
        ),
        prefixIconColor: BltColors.muted,
        hintStyle: const TextStyle(color: BltColors.muted),
        labelStyle: const TextStyle(color: BltColors.muted),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: BltColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: BltColors.red, width: 1.4),
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: BltColors.border),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: BltColors.red,
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: BltColors.ink,
          side: const BorderSide(color: BltColors.border),
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: BltColors.red,
          textStyle: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: BltColors.redTint,
        selectedColor: BltColors.red,
        checkmarkColor: Colors.white,
        labelStyle: const TextStyle(
          color: BltColors.red,
          fontSize: 12,
          fontWeight: FontWeight.w700,
        ),
        secondaryLabelStyle: const TextStyle(
          color: Colors.white,
          fontSize: 12,
          fontWeight: FontWeight.w700,
        ),
        side: const BorderSide(color: Color(0xFFFECACA)),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),
      ),
      navigationBarTheme: NavigationBarThemeData(
        elevation: 0,
        height: 72,
        backgroundColor: Colors.white,
        indicatorColor: BltColors.redTint,
        labelTextStyle: WidgetStateProperty.resolveWith(
          (states) => TextStyle(
            color: states.contains(WidgetState.selected)
                ? BltColors.red
                : BltColors.muted,
            fontSize: 12,
            fontWeight: FontWeight.w700,
          ),
        ),
        iconTheme: WidgetStateProperty.resolveWith(
          (states) => IconThemeData(
            color: states.contains(WidgetState.selected)
                ? BltColors.red
                : BltColors.muted,
          ),
        ),
      ),
      floatingActionButtonTheme: const FloatingActionButtonThemeData(
        backgroundColor: BltColors.red,
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: BltColors.ink,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
      pageTransitionsTheme: const PageTransitionsTheme(
        builders: {
          TargetPlatform.android: FadeUpwardsPageTransitionsBuilder(),
          TargetPlatform.iOS: CupertinoPageTransitionsBuilder(),
          TargetPlatform.windows: FadeUpwardsPageTransitionsBuilder(),
          TargetPlatform.macOS: CupertinoPageTransitionsBuilder(),
          TargetPlatform.linux: FadeUpwardsPageTransitionsBuilder(),
        },
      ),
    );
  }
}

/// Subtle dotted field used by the website hero.
class BltDotField extends StatelessWidget {
  /// Creates the dotted background field.
  const BltDotField({super.key, this.opacity = 0.55});

  /// Dot opacity.
  final double opacity;

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Opacity(
        opacity: opacity,
        child: CustomPaint(
          painter: _BltDotPainter(),
          size: Size.infinite,
        ),
      ),
    );
  }
}

class _BltDotPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = BltColors.ink.withValues(alpha: 0.16);
    const spacing = 18.0;
    const radius = 1.0;
    final center = Offset(size.width / 2, size.height * 0.35);
    final maxDistance = size.shortestSide * 0.78;

    for (var x = 0.0; x < size.width; x += spacing) {
      for (var y = 0.0; y < size.height; y += spacing) {
        final distance = (Offset(x, y) - center).distance;
        final fade = (1 - (distance / maxDistance)).clamp(0.0, 1.0);
        if (fade > 0) {
          canvas.drawCircle(
            Offset(x, y),
            radius,
            paint..color = BltColors.ink.withValues(alpha: 0.16 * fade),
          );
        }
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

/// Website-style section kicker pill.
class BltKicker extends StatelessWidget {
  /// Creates a red outline uppercase kicker.
  const BltKicker(this.label, {super.key});

  /// Kicker label.
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: BltColors.redTint,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: const Color(0xFFFECACA)),
      ),
      child: Text(
        label.toUpperCase(),
        style: const TextStyle(
          color: BltColors.red,
          fontSize: 11,
          fontWeight: FontWeight.w800,
          letterSpacing: 1.7,
        ),
      ),
    );
  }
}

/// Website-style icon container.
class BltIconBox extends StatelessWidget {
  /// Creates a red-tinted icon box.
  const BltIconBox(this.icon, {super.key, this.size = 42});

  /// Icon data.
  final IconData icon;

  /// Box size.
  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: BltColors.redTint,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: BltColors.border),
      ),
      child: Icon(icon, color: BltColors.red, size: size * 0.48),
    );
  }
}

/// Shared animated page shell matching the website's dotted gray canvas.
class BltPageShell extends StatelessWidget {
  /// Creates an animated page shell.
  const BltPageShell({super.key, required this.child, this.padding});

  /// Page content.
  final Widget child;

  /// Optional content padding.
  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        const Positioned.fill(child: BltDotField(opacity: 0.24)),
        TweenAnimationBuilder<double>(
          duration: const Duration(milliseconds: 420),
          curve: Curves.easeOutCubic,
          tween: Tween(begin: 16, end: 0),
          builder: (context, offset, child) {
            return Opacity(
              opacity: (1 - offset / 16).clamp(0.0, 1.0),
              child: Transform.translate(
                offset: Offset(0, offset),
                child: child,
              ),
            );
          },
          child: Padding(
            padding: padding ?? const EdgeInsets.all(16),
            child: child,
          ),
        ),
      ],
    );
  }
}

