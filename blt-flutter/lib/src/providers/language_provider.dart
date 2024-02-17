import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

final languageProvider =
    StateNotifierProvider<LanguageStateNotifier, String>((ref) {
  return LanguageStateNotifier();
});

class LanguageStateNotifier extends StateNotifier<String> {
  LanguageStateNotifier() : super('en') {
    _loadSavedLanguage();
  }

  Future<void> _loadSavedLanguage() async {
    final prefs = await SharedPreferences.getInstance();
    final savedLang = prefs.getString('saved_language') ??
        'en'; // Default to English if no saved preference
    state = savedLang;
  }

  Future<void> changeLanguage(String newLanguageCode) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('saved_language', newLanguageCode);
    state = newLanguageCode;
  }
}
