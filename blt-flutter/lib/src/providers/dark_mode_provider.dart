import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

final darkModeProvider = ChangeNotifierProvider((ref) {
  return DarkModeNotifier();
});

/// Dark mode follows the system until the user flips the toggle; the choice
/// is then saved and wins over the system setting.
class DarkModeNotifier extends ChangeNotifier {
  static const _isDarkModeKey = 'isDarkMode';

  /// null = no saved choice, follow the system.
  bool? _savedDarkMode;

  bool get isDarkMode => _savedDarkMode ?? _systemIsDark;

  ThemeMode get themeMode => _savedDarkMode == null
      ? ThemeMode.system
      : (_savedDarkMode! ? ThemeMode.dark : ThemeMode.light);

  static bool get _systemIsDark =>
      WidgetsBinding.instance.platformDispatcher.platformBrightness ==
      Brightness.dark;

  DarkModeNotifier() {
    _loadDarkMode();
  }

  Future<void> _loadDarkMode() async {
    final prefs = await SharedPreferences.getInstance();
    _savedDarkMode = prefs.getBool(_isDarkModeKey);
    notifyListeners();
  }

  Future<void> toggleDarkMode() async {
    _savedDarkMode = !isDarkMode;
    notifyListeners();

    final prefs = await SharedPreferences.getInstance();
    prefs.setBool(_isDarkModeKey, _savedDarkMode!);
  }
}
