import 'package:flutter/material.dart';
import 'src/app.dart';
import 'package:flutter/services.dart';
// Application's entry point
void main() {
    WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]).then((value) => runApp(BugHeist()));
  runApp(BugHeist());
}
