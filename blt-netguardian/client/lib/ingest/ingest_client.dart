/// HTTP client for `POST /api/ingest`.
library;

import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import 'canonicalize.dart';
import 'envelope.dart';
import 'payload_crypto.dart';

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

  String get errorCode => (body['error'] ?? '').toString();

  String get message {
    final msg = body['message'];
    if (msg != null && msg.toString().isNotEmpty) return msg.toString();
    if (errorCode.isNotEmpty) return errorCode;
    return 'HTTP $statusCode';
  }
}

String randomNonce() {
  final rng = Random.secure();
  final bytes = List<int>.generate(16, (_) => rng.nextInt(256));
  return bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
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
    bool encrypt = false,
    Uint8List? payloadKey,
    Duration timeout = const Duration(seconds: 20),
  }) async {
    final issuedAt = issuedAtNowUtc();
    final Map<String, Object?> envelope;
    if (encrypt) {
      if (payloadKey == null) {
        throw PayloadCryptoException('payload key required for encrypted ingest');
      }
      final ciphertext = await encryptPayload(
        key: payloadKey,
        payload: payload,
        aad: utf8.encode(orgId),
      );
      envelope = prepareSignedEnvelope({
        'version': ztrVersion,
        'org_id': orgId,
        'sender_id': senderId,
        'kid': kid,
        'alg': ztrAlg,
        'issued_at': issuedAt,
        'nonce': nonce ?? randomNonce(),
        'payload_ciphertext': ciphertext,
      }, secret);
    } else {
      envelope = prepareSignedPlaintextEnvelope(
        orgId: orgId,
        senderId: senderId,
        kid: kid,
        secret: secret,
        payload: payload,
        issuedAt: issuedAt,
        nonce: nonce ?? randomNonce(),
      );
    }
    final raw = encodeEnvelopeBody(envelope);
    final digest = bodyDigestHex(raw);
    final uri = Uri.parse('${baseUrl.replaceAll(RegExp(r'/+$'), '')}/api/ingest');
    final response = await _http
        .post(
          uri,
          headers: {
            'Content-Type': 'application/json; charset=utf-8',
            'X-BLT-Body-Digest': 'sha256=$digest',
          },
          body: raw,
        )
        .timeout(timeout);
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

  Future<bool> ping(String baseUrl) async {
    try {
      final uri = Uri.parse('${baseUrl.replaceAll(RegExp(r'/+$'), '')}/api/health');
      final response = await _http.get(uri).timeout(const Duration(seconds: 5));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  void close() => _http.close();
}
