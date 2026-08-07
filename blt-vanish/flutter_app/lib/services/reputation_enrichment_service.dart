import 'dart:convert';
import 'package:http/http.dart' as http;

/// Fetches public host reputation data from the Worker edge API.
class ReputationEnrichmentService {
  /// Base URL for the deployed Worker instance.
  final String baseUrl;
  final http.Client _client;

  /// Creates a service with an optional injected HTTP client for testing.
  ReputationEnrichmentService({required this.baseUrl, http.Client? client})
      : _client = client ?? http.Client();

  /// Returns a normalized reputation payload or an offline-safe fallback.
  Future<Map<String, String>> fetchReputation(String domain, {int timeoutMs = 1500}) async {
    final url = Uri.parse('$baseUrl/api/reputation?domain=$domain');
    const int maxAttempts = 2;

    for (int attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        final response = await _client.get(url).timeout(
          Duration(milliseconds: timeoutMs),
        );

        if (response.statusCode == 200) {
          final data = jsonDecode(response.body) as Map<String, dynamic>;
          return {
            'reputation': data['reputation']?.toString() ?? 'unknown',
            'threat_score': data['threat_score']?.toString() ?? '0.0',
          };
        }
      } catch (_) {
        if (attempt == maxAttempts - 1) break;
      }
    }

    return {'reputation': 'unknown', 'threat_score': '0.0'};
  }
}
