import 'dart:async';
import 'api_client.dart';
import 'batch_sender.dart';
import 'idle_detector.dart';
import 'activity_service.dart';

class TrackerIntegration {
  final String apiUrl;
  final String userId;
  final String projectId;
  String? _sessionId;
  String? get sessionId => _sessionId;

  late final ApiClient _apiClient;
  late final BatchSender _batchSender;
  late final IdleDetector _idleDetector;

  final _errorController = StreamController<String>.broadcast();
  Stream<String> get errorStream => _errorController.stream;

  bool _isDisposed = false;

  TrackerIntegration({
    required this.apiUrl,
    required this.userId,
    required this.projectId,
  }) {
    _apiClient = ApiClient(baseUrl: apiUrl);
    _batchSender = BatchSender(
      apiClient: _apiClient,
      endpoint: '/api/activity/batch',
      onError: (error) {
        _errorController.add(error);
      },
    );
    _idleDetector = IdleDetector(
      onIdle: () {
        _batchSender.flushAndDispose();
      },
      onActive: () {
        if (!_isDisposed && _sessionId != null) {
          _batchSender.start();
        }
      },
    );
  }

  Future<bool> startSession() async {
    if (_isDisposed) return false;

    try {
      final data = await _apiClient.post('/api/sessions/start', body: {
        'userId': userId,
        'projectId': projectId,
        'source': 'flutter-linux',
      });

      _sessionId = data['sessionId'] as String?;
      if (_sessionId != null) {
        _batchSender.start();
        _idleDetector.start();
        return true;
      }
      return false;
    } on ApiException catch (e) {
      _errorController.add('Failed to start session: ${e.message}');
      return false;
    } catch (e) {
      _errorController.add('Unexpected error starting session: $e');
      return false;
    }
  }

  void sendActivityData(ActivityData data) {
    if (_isDisposed || _sessionId == null) return;

    _idleDetector.recordActivity();

    _batchSender.add({
      'sessionId': _sessionId,
      'userId': userId,
      'projectId': projectId,
      'activity': {
        'keyboard': {
          'keyCount': data.keyCount,
        },
        'mouse': {
          'distance': data.mouseDistance,
        },
      },
      'timestamp': data.timestamp.toIso8601String(),
    });
  }

  Future<void> endSession() async {
    if (_sessionId == null) return;

    _idleDetector.stop();
    await _batchSender.flushAndDispose();

    try {
      await _apiClient.post('/api/sessions/end', body: {
        'sessionId': _sessionId,
        'userId': userId,
      });
      _sessionId = null;
    } on ApiException catch (e) {
      _errorController.add('Failed to end session: ${e.message}');
    } catch (e) {
      _errorController.add('Unexpected error ending session: $e');
    }
  }

  Future<void> dispose() async {
    if (_isDisposed) return;
    _isDisposed = true;

    _idleDetector.dispose();
    await _batchSender.dispose();
    await _errorController.close();
    _apiClient.dispose();
  }
}
