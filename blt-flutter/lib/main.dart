//import 'package:blt/src/util/services/init_service.dart';
import 'package:flutter/material.dart';
import 'src/app.dart';
//import 'package:flutter/services.dart';
import 'package:sentry_flutter/sentry_flutter.dart';

// Application's entry point
void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  //InitService.init(); // Call the init method from the InitService class
  const SENTRY_DSN = "https://example-234234324.com/4504877879197696";
  await SentryFlutter.init(
    (options) {
      options.dsn = SENTRY_DSN;
      options.tracesSampleRate = 1.0;
    },
    appRunner: () => runApp(BLT()),
  );
}
