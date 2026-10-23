import 'package:flutter/material.dart';

class AppLifecycleManager extends WidgetsBindingObserver {
  final VoidCallback? onPause;
  final VoidCallback? onResume;

  AppLifecycleManager({
    this.onPause,
    this.onResume,
  });

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    switch (state) {
      case AppLifecycleState.paused:
      case AppLifecycleState.detached:
      case AppLifecycleState.hidden:
        onPause?.call();
        break;
      case AppLifecycleState.resumed:
        onResume?.call();
        break;
      case AppLifecycleState.inactive:
        // Keep tracking during inactive state
        break;
    }
  }

  void register() {
    WidgetsBinding.instance.addObserver(this);
  }

  void unregister() {
    WidgetsBinding.instance.removeObserver(this);
  }

  void dispose() {
    unregister();
  }
}
