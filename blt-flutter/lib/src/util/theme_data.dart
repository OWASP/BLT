import 'package:flutter/material.dart';

class AppTheme {
  static ThemeData lightTheme = ThemeData(
      primarySwatch: Colors.red,
      primaryColor: Colors.white,
      visualDensity: VisualDensity.adaptivePlatformDensity,
      brightness: Brightness.light);

  static ThemeData darkTheme =
      ThemeData.dark().copyWith(brightness: Brightness.dark);
}
