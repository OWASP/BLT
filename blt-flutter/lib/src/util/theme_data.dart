import 'package:flutter/material.dart';

class AppTheme {
  static ThemeData lightTheme = ThemeData(
      useMaterial3: true,
      primarySwatch: Colors.red,
      primaryColor: Colors.white,
      visualDensity: VisualDensity.adaptivePlatformDensity,
      brightness: Brightness.light);

  static ThemeData darkTheme = ThemeData.dark(
    useMaterial3: true,
  ).copyWith(brightness: Brightness.dark);
}
