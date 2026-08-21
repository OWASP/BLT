/// HTTP client for `/api/domains` (shared crawl queue).
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'domain_queue.dart';

class DomainApi {
  DomainApi({http.Client? httpClient}) : _http = httpClient ?? http.Client();

  final http.Client _http;

  Uri _uri(String base, String path) {
    final root = base.replaceAll(RegExp(r'/+$'), '');
    return Uri.parse('$root$path');
  }

  Map<String, String> _headers({String? token, String? senderId}) {
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }
    if (senderId != null && senderId.isNotEmpty) {
      headers['X-NG-Sender'] = senderId;
    }
    return headers;
  }

  Map<String, Object?> _decode(http.Response response) {
    if (response.body.isEmpty) return {};
    final decoded = jsonDecode(utf8.decode(response.bodyBytes));
    if (decoded is Map) {
      return decoded.map((k, v) => MapEntry(k.toString(), v as Object?));
    }
    return {};
  }

  List<DomainJob> _jobsFrom(Object? raw) {
    if (raw is! List) return [];
    return raw
        .whereType<Map>()
        .map((m) => DomainJob.fromJson(
              m.map((k, v) => MapEntry(k.toString(), v as Object?)),
            ))
        .toList();
  }

  Future<({List<DomainJob> jobs, Map<String, int> counts})> list({
    required String baseUrl,
    String? token,
    String? senderId,
  }) async {
    final response = await _http
        .get(_uri(baseUrl, '/api/domains'), headers: _headers(token: token, senderId: senderId))
        .timeout(const Duration(seconds: 20));
    final body = _decode(response);
    final countsRaw = body['counts'];
    final counts = <String, int>{};
    if (countsRaw is Map) {
      for (final e in countsRaw.entries) {
        counts[e.key.toString()] = int.tryParse('${e.value}') ?? 0;
      }
    }
    return (jobs: _jobsFrom(body['jobs']), counts: counts);
  }

  Future<List<DomainJob>> submit({
    required String baseUrl,
    required List<String> domains,
    required String senderId,
    String? token,
    String? sourceUrl,
  }) async {
    final response = await _http
        .post(
          _uri(baseUrl, '/api/domains'),
          headers: _headers(token: token, senderId: senderId),
          body: jsonEncode({
            'sender_id': senderId,
            'domains': domains,
            if (sourceUrl != null) 'source_url': sourceUrl,
          }),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode >= 400) {
      throw Exception('domain submit HTTP ${response.statusCode}: ${response.body}');
    }
    return _jobsFrom(_decode(response)['created']);
  }

  Future<DomainJob?> claim({
    required String baseUrl,
    required String senderId,
    String? token,
  }) async {
    final response = await _http
        .post(
          _uri(baseUrl, '/api/domains/claim'),
          headers: _headers(token: token, senderId: senderId),
          body: jsonEncode({'sender_id': senderId}),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode >= 400) {
      throw Exception('domain claim HTTP ${response.statusCode}: ${response.body}');
    }
    final job = _decode(response)['job'];
    if (job is! Map) return null;
    return DomainJob.fromJson(job.map((k, v) => MapEntry(k.toString(), v as Object?)));
  }

  Future<void> complete({
    required String baseUrl,
    required String jobId,
    required String senderId,
    required Map<String, Object?> result,
    String? token,
  }) async {
    final response = await _http
        .post(
          _uri(baseUrl, '/api/domains/$jobId/complete'),
          headers: _headers(token: token, senderId: senderId),
          body: jsonEncode({'sender_id': senderId, 'result': result}),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode >= 400) {
      throw Exception('domain complete HTTP ${response.statusCode}: ${response.body}');
    }
  }

  Future<void> fail({
    required String baseUrl,
    required String jobId,
    required String senderId,
    required String error,
    String? token,
  }) async {
    final response = await _http
        .post(
          _uri(baseUrl, '/api/domains/$jobId/fail'),
          headers: _headers(token: token, senderId: senderId),
          body: jsonEncode({'sender_id': senderId, 'error': error}),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode >= 400) {
      throw Exception('domain fail HTTP ${response.statusCode}: ${response.body}');
    }
  }
}
