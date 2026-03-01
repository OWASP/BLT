import 'dart:convert';
import 'package:http/http.dart' as http;
import 'activity_service.dart';

class TrackerIntegration {
  final String apiUrl;
  final String userId;
  final String projectId;
  String? sessionId;

  TrackerIntegration({
    required this.apiUrl,
    required this.userId,
    required this.projectId,
  });

  Future<bool> startSession() async {
    try {
      final response = await http.post(
        Uri.parse('$apiUrl/api/sessions/start'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'userId': userId,
          'projectId': projectId,
          'source': 'flutter-linux',
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        sessionId = data['sessionId'];
        return true;
      }
      return false;
    } catch (e) {
      // Swallow network error; integration is optional.
      return false;
    }
  }

  Future<void> sendActivityData(ActivityData data) async {
    if (sessionId == null) return;

    try {
      await http.post(
        Uri.parse('$apiUrl/api/activity'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'sessionId': sessionId,
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
        }),
      );
    } catch (e) {
      // Ignore transient network errors.
    }
  }

  Future<void> endSession() async {
    if (sessionId == null) return;

    try {
      await http.post(
        Uri.parse('$apiUrl/api/sessions/end'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'sessionId': sessionId,
          'userId': userId,
        }),
      );
      sessionId = null;
    } catch (e) {
      // Ignore errors during session end.
    }
  }
}
