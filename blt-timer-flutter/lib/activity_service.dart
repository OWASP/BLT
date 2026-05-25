import 'dart:async';
import 'native_tracker.dart';

class ActivityData {
  final int keyCount;
  final double mouseDistance;
  final int leftClicks;
  final int rightClicks;
  final double scrollAmount;
  final int enterCount;
  final DateTime timestamp;

  ActivityData({
    required this.keyCount,
    required this.mouseDistance,
    required this.leftClicks,
    required this.rightClicks,
    required this.scrollAmount,
    required this.enterCount,
    required this.timestamp,
  });
}

class ActivityRate {
  final int keysPerMinute;
  final double mouseDistancePerMinute;
  final int leftClicksPerMinute;
  final int rightClicksPerMinute;
  final double scrollUnitsPerMinute;
  final int keysPerSecond;
  final double mouseDistancePerSecond;
  final int leftClicksPerSecond;
  final int rightClicksPerSecond;
  final double scrollUnitsPerSecond;
  final DateTime timestamp;

  ActivityRate({
    required this.keysPerMinute,
    required this.mouseDistancePerMinute,
    required this.leftClicksPerMinute,
    required this.rightClicksPerMinute,
    required this.scrollUnitsPerMinute,
    required this.keysPerSecond,
    required this.mouseDistancePerSecond,
    required this.leftClicksPerSecond,
    required this.rightClicksPerSecond,
    required this.scrollUnitsPerSecond,
    required this.timestamp,
  });
}

class ActivityService {
  final ActivityTrackerNative _native = ActivityTrackerNative();
  Timer? _pollTimer;
  Timer? _updateTimer;

  final _activityStreamController = StreamController<ActivityData>.broadcast();
  Stream<ActivityData> get activityStream => _activityStreamController.stream;

  final _rateStreamController = StreamController<ActivityRate>.broadcast();
  Stream<ActivityRate> get rateStream => _rateStreamController.stream;

  int _totalKeysToday = 0;
  double _totalMouseDistanceToday = 0.0;
  int _totalLeftClicksToday = 0;
  int _totalRightClicksToday = 0;
  double _totalScrollToday = 0.0;
  int _totalEnterToday = 0;

  int _lastKeyCount = 0;
  double _lastMouseDistance = 0.0;
  int _lastLeftClicks = 0;
  int _lastRightClicks = 0;
  double _lastScrollAmount = 0.0;
  int _lastEnterCount = 0;

  bool _isInitialized = false;
  bool _isPaused = false;

  bool get isPaused => _isPaused;

  Future<bool> initialize() async {
    if (_isInitialized) return true;

    try {
      _isInitialized = _native.initialize();
    } catch (e) {
      _isInitialized = false;
    }

    if (_isInitialized) {
      _pollTimer = Timer.periodic(const Duration(milliseconds: 50), (_) {
        _native.processEvents();
      });

      _updateTimer = Timer.periodic(const Duration(seconds: 1), (_) {
        _updateActivity();
      });
    }

    return _isInitialized;
  }

  void _updateActivity() {
    if (_isPaused) return;

    final data = _native.getActivityData();
    final keyCount = (data['keyCount'] as num?)?.toInt() ?? 0;
    final mouseDistance = (data['mouseDistance'] as num?)?.toDouble() ?? 0.0;
    final leftClicks = (data['leftClicks'] as num?)?.toInt() ?? 0;
    final rightClicks = (data['rightClicks'] as num?)?.toInt() ?? 0;
    final scrollAmount = (data['scrollAmount'] as num?)?.toDouble() ?? 0.0;
    final enterCount = (data['enterCount'] as num?)?.toInt() ?? 0;

    final keysDelta = keyCount - _lastKeyCount;
    final mouseDelta = mouseDistance - _lastMouseDistance;
    final leftClicksDelta = leftClicks - _lastLeftClicks;
    final rightClicksDelta = rightClicks - _lastRightClicks;
    final scrollDelta = scrollAmount - _lastScrollAmount;
    final enterDelta = enterCount - _lastEnterCount;

    _totalKeysToday += keysDelta;
    _totalMouseDistanceToday += mouseDelta;
    _totalLeftClicksToday += leftClicksDelta;
    _totalRightClicksToday += rightClicksDelta;
    _totalScrollToday += scrollDelta.abs();
    _totalEnterToday += enterDelta;

    final keysPerMinute = keysDelta * 60;
    final mouseDistancePerMinute = mouseDelta * 60;
    final leftClicksPerMinute = leftClicksDelta * 60;
    final rightClicksPerMinute = rightClicksDelta * 60;
    final scrollUnitsPerMinute = scrollDelta * 60;
    final keysPerSecond = keysDelta;
    final mouseDistancePerSecond = mouseDelta;
    final leftClicksPerSecond = leftClicksDelta;
    final rightClicksPerSecond = rightClicksDelta;
    final scrollUnitsPerSecond = scrollDelta;

    _lastKeyCount = keyCount;
    _lastMouseDistance = mouseDistance;
    _lastLeftClicks = leftClicks;
    _lastRightClicks = rightClicks;
    _lastScrollAmount = scrollAmount;
    _lastEnterCount = enterCount;

    _activityStreamController.add(ActivityData(
      keyCount: keyCount,
      mouseDistance: mouseDistance,
      leftClicks: leftClicks,
      rightClicks: rightClicks,
      scrollAmount: scrollAmount,
      enterCount: enterCount,
      timestamp: DateTime.now(),
    ));

    _rateStreamController.add(ActivityRate(
      keysPerMinute: keysPerMinute,
      mouseDistancePerMinute: mouseDistancePerMinute,
      leftClicksPerMinute: leftClicksPerMinute,
      rightClicksPerMinute: rightClicksPerMinute,
      scrollUnitsPerMinute: scrollUnitsPerMinute,
      keysPerSecond: keysPerSecond,
      mouseDistancePerSecond: mouseDistancePerSecond,
      leftClicksPerSecond: leftClicksPerSecond,
      rightClicksPerSecond: rightClicksPerSecond,
      scrollUnitsPerSecond: scrollUnitsPerSecond,
      timestamp: DateTime.now(),
    ));
  }

  int get totalKeysToday => _totalKeysToday;
  double get totalMouseDistanceToday => _totalMouseDistanceToday;
  int get totalLeftClicksToday => _totalLeftClicksToday;
  int get totalRightClicksToday => _totalRightClicksToday;
  double get totalScrollToday => _totalScrollToday;
  int get totalEnterToday => _totalEnterToday;

  void setInitialTotals({
    int keys = 0,
    double mouseDistance = 0.0,
    int leftClicks = 0,
    int rightClicks = 0,
    double scrollSteps = 0.0,
    int enterCount = 0,
  }) {
    _totalKeysToday = keys;
    _totalMouseDistanceToday = mouseDistance;
    _totalLeftClicksToday = leftClicks;
    _totalRightClicksToday = rightClicks;
    _totalScrollToday = scrollSteps;
    _totalEnterToday = enterCount;
  }

  void resetDailyStats() {
    _totalKeysToday = 0;
    _totalMouseDistanceToday = 0.0;
    _totalLeftClicksToday = 0;
    _totalRightClicksToday = 0;
    _totalScrollToday = 0.0;
    _totalEnterToday = 0;
  }

  void pause() {
    _isPaused = true;
  }

  void resume() {
    _isPaused = false;
  }

  Future<void> dispose() async {
    _pollTimer?.cancel();
    _updateTimer?.cancel();
    await _activityStreamController.close();
    await _rateStreamController.close();
    _native.cleanup();
    _isInitialized = false;
  }
}
