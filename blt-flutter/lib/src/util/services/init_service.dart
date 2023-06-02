import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';

class InitService {
  static void init() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _setOrientation();
    });
  }

  static void _setOrientation() {
    final shortestSide =
        MediaQueryData.fromView(WidgetsBinding.instance.platformDispatcher.views.first)
            .size
            .shortestSide;
    if (shortestSide > 600) {
      SystemChrome.setPreferredOrientations([
        DeviceOrientation.portraitUp,
        DeviceOrientation.portraitDown,
        DeviceOrientation.landscapeLeft,
        DeviceOrientation.landscapeRight,
      ]);
    } else {
      SystemChrome.setPreferredOrientations([
        DeviceOrientation.portraitUp,
      ]);
    }
  }
}
