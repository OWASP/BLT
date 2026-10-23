import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiException implements Exception {
  final String message;
  final int? statusCode;
  ApiException(this.message, {this.statusCode});
  @override
  String toString() => 'ApiException: $message (status: $statusCode)';
}

class ApiClient {
  final String baseUrl;
  final Duration timeout;
  final Map<String, String> defaultHeaders;
  final http.Client _client;

  ApiClient({
    required this.baseUrl,
    http.Client? client,
    this.timeout = const Duration(seconds: 10),
    this.defaultHeaders = const {'Content-Type': 'application/json'},
  }) : _client = client ?? http.Client();

  Future<Map<String, dynamic>> post(String path, {Map<String, dynamic>? body}) async {
    final uri = Uri.parse('$baseUrl$path');
    final response = await _client
        .post(uri, headers: defaultHeaders, body: body != null ? jsonEncode(body) : null)
        .timeout(timeout, onTimeout: () {
      throw ApiException('Request to $path timed out after ${timeout.inSeconds}s');
    });

    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return {};
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw ApiException('HTTP ${response.statusCode}: ${response.body}', statusCode: response.statusCode);
    }
  }

  void dispose() {
    _client.close();
  }
}
