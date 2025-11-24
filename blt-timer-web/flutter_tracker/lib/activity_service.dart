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
  
  // Removed _lastMinuteKeyCount and _lastMinuteMouseDistance (unused legacy rate fields)

  bool _isInitialized = false;

  Future<bool> initialize() async {
    if (_isInitialized) return true;

    _isInitialized = _native.initialize();
    
    if (_isInitialized) {
      // Poll for events every 10ms
      _pollTimer = Timer.periodic(const Duration(milliseconds: 10), (_) {
        _native.processEvents();
      });

      // Update stream every second
      _updateTimer = Timer.periodic(const Duration(seconds: 1), (_) {
        _updateActivity();
      });
    }

    return _isInitialized;
  }

  void _updateActivity() {
    final data = _native.getActivityData();
    final keyCount = data['keyCount'] as int;
    final mouseDistance = data['mouseDistance'] as double;
    final leftClicks = (data['leftClicks'] ?? 0) as int;
    final rightClicks = (data['rightClicks'] ?? 0) as int;
    final scrollAmount = (data['scrollAmount'] ?? 0.0) as double;
    final enterCount = (data['enterCount'] ?? 0) as int;

    // Calculate incremental values
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
    // Accumulate absolute scroll steps so total only increases regardless of direction
    _totalScrollToday += scrollDelta.abs();
    _totalEnterToday += enterDelta;

    // Calculate per-minute rate (multiply by 60 since we update every second)
    final keysPerMinute = keysDelta * 60;
    final mouseDistancePerMinute = mouseDelta * 60;
    final leftClicksPerMinute = leftClicksDelta * 60;
    final rightClicksPerMinute = rightClicksDelta * 60;
    // Use signed value so charts reflect direction; total remains absolute.
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

    // Send cumulative data
    _activityStreamController.add(ActivityData(
      keyCount: keyCount,
      mouseDistance: mouseDistance,
      leftClicks: leftClicks,
      rightClicks: rightClicks,
      scrollAmount: scrollAmount,
      enterCount: enterCount,
      timestamp: DateTime.now(),
    ));

    // Send rate data
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

  void dispose() {
    _pollTimer?.cancel();
    _updateTimer?.cancel();
    _activityStreamController.close();
    _rateStreamController.close();
    _native.cleanup();
    _isInitialized = false;
  }
}
