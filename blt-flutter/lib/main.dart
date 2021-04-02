import 'package:flutter/material.dart';
import 'pages/splash.dart';
import 'package:bugheist/pages/login_signup.dart';

void main() {
  runApp(FlutterSearch());
}

class FlutterSearch extends StatefulWidget {
  @override
  _FlutterSearchState createState() => _FlutterSearchState();
}

class _FlutterSearchState extends State<FlutterSearch> {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      home: LoginSignUp(),
    );
  }
}
