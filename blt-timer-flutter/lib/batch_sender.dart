import 'dart:async';
import 'api_client.dart';

class ActivityBatchItem {
  final Map<String, dynamic> payload;
  final DateTime timestamp;
  ActivityBatchItem({required this.payload, required this.timestamp});
}

class BatchSender {
  final ApiClient apiClient;
  final String endpoint;
  final Duration sendInterval;
  final int maxBatchSize;
  final void Function(String error)? onError;

  final List<ActivityBatchItem> _buffer = [];
  Timer? _sendTimer;
  bool _isSending = false;
  bool _isDisposed = false;
  Completer<void>? _flushCompleter;

  BatchSender({
    required this.apiClient,
    required this.endpoint,
    this.sendInterval = const Duration(minutes: 1),
    this.maxBatchSize = 50,
    this.onError,
  });

  void start() {
    if (_isDisposed) return;
    _sendTimer?.cancel();
    _sendTimer = Timer.periodic(sendInterval, (_) => _flush());
  }

  void add(Map<String, dynamic> payload) {
    if (_isDisposed) return;
    _buffer.add(ActivityBatchItem(payload: payload, timestamp: DateTime.now()));
    if (_buffer.length >= maxBatchSize) {
      _flush();
    }
  }

  Future<void> _flush() async {
    if (_isDisposed || _isSending || _buffer.isEmpty) return;
    _isSending = true;
    _flushCompleter = Completer<void>();
    final batch = List<ActivityBatchItem>.from(_buffer);
    _buffer.clear();

    try {
      final payloads = batch.map((e) => {
        ...e.payload,
        'clientTimestamp': e.timestamp.toIso8601String(),
      }).toList();
      await apiClient.post(endpoint, body: {'activities': payloads});
    } catch (e) {
      // Re-add failed items to buffer for retry (with limit)
      final canRequeue = _buffer.length + batch.length <= maxBatchSize * 2;
      if (canRequeue) {
        _buffer.insertAll(0, batch);
      } else {
        onError?.call('Batch dropped: buffer overflow. Lost ${batch.length} items. Error: $e');
      }
      onError?.call(e.toString());
    } finally {
      _isSending = false;
      _flushCompleter?.complete();
      _flushCompleter = null;
    }
  }

  Future<void> flushAndDispose() async {
    if (_isDisposed) return;
    _isDisposed = true;
    _sendTimer?.cancel();
    await _flush();
  }

  Future<void> dispose() async {
    if (_isDisposed) return;
    _isDisposed = true;
    _sendTimer?.cancel();
    if (_flushCompleter != null) {
      await _flushCompleter!.future;
    }
  }
}
