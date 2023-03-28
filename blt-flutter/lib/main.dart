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

  const SENTRY_DSN = "https://example-234234324.com/4504877879197696";
  await SentryFlutter.init(
    (options) {
      options.dsn = SENTRY_DSN;
      options.tracesSampleRate = 1.0;
    },
    appRunner: () => runApp(BLT()),
  );
}
