import 'dart:async';

class IdleDetector {
  static const Duration defaultIdleTimeout = Duration(minutes: 2);
  final Duration idleTimeout;
  Timer? _idleTimer;
  DateTime? _lastActivityTime;
  final void Function()? onIdle;
  final void Function()? onActive;
  bool _isIdle = false;
  bool _isDisposed = false;

  IdleDetector({this.idleTimeout = defaultIdleTimeout, this.onIdle, this.onActive});

  bool get isIdle => _isIdle;
  DateTime? get lastActivityTime => _lastActivityTime;

  void recordActivity() {
    if (_isDisposed) return;
    _lastActivityTime = DateTime.now();
    _idleTimer?.cancel();
    if (_isIdle) {
      _isIdle = false;
      onActive?.call();
    }
    _idleTimer = Timer(idleTimeout, () {
      if (_isDisposed) return;
      _isIdle = true;
      onIdle?.call();
    });
  }

  void start() {
    recordActivity();
  }

  void stop() {
    _idleTimer?.cancel();
    _idleTimer = null;
  }

  void dispose() {
    if (_isDisposed) return;
    _isDisposed = true;
    stop();
    _lastActivityTime = null;
    _isIdle = false;
  }
}
