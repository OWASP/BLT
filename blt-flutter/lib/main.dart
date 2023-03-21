import 'package:flutter/material.dart';
import 'src/app.dart';
import 'package:flutter/services.dart';
import 'package:sentry_flutter/sentry_flutter.dart';

// Application's entry point
void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]).then((value) => runApp(BLT()));

  const SENTRY_DSN = String.fromEnvironment('SENTRY_DSN');
  await SentryFlutter.init(
    (options) {
      options.dsn = SENTRY_DSN;
      options.tracesSampleRate = 1.0;
    },
    appRunner: () => runApp(BLT()),
  );
}
