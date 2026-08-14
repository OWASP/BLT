/// HTTP client for `POST /api/ingest`.
library;

import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import 'canonicalize.dart';
import 'envelope.dart';

class IngestResult {
  IngestResult({
    required this.statusCode,
    required this.body,
    this.findingId,
  });

  final int statusCode;
  final Map<String, Object?> body;
  final String? findingId;

  bool get ok => statusCode == 200 || statusCode == 201;
}

class IngestClient {
  IngestClient({http.Client? httpClient}) : _http = httpClient ?? http.Client();

  final http.Client _http;

  /// Sign [payload] and POST to `{baseUrl}/api/ingest`.
  Future<IngestResult> sendFinding({
    required String baseUrl,
    required String orgId,
    required String senderId,
    required String kid,
    required Uint8List secret,
    required Map<String, Object?> payload,
    String? nonce,
  }) async {
    final issuedAt = issuedAtNowUtc();
    final stamp = DateTime.now().toUtc().millisecondsSinceEpoch;
    final envelope = prepareSignedPlaintextEnvelope(
      orgId: orgId,
      senderId: senderId,
      kid: kid,
      secret: secret,
      payload: payload,
      issuedAt: issuedAt,
      nonce: nonce ?? 'ng-client-$stamp',
    );
    final raw = encodeEnvelopeBody(envelope);
    final digest = bodyDigestHex(raw);
    final uri = Uri.parse(baseUrl.replaceAll(RegExp(r'/+$'), '') + '/api/ingest');
    final response = await _http.post(
      uri,
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'X-BLT-Body-Digest': 'sha256=$digest',
      },
      body: raw,
    );
    Map<String, Object?> parsed = {};
    try {
      final decoded = jsonDecode(utf8.decode(response.bodyBytes));
      if (decoded is Map) {
        parsed = decoded.map((k, v) => MapEntry(k.toString(), v as Object?));
      }
    } catch (_) {
      parsed = {'raw': utf8.decode(response.bodyBytes)};
    }
    return IngestResult(
      statusCode: response.statusCode,
      body: parsed,
      findingId: parsed['finding_id']?.toString(),
    );
  }

  void close() => _http.close();
}
