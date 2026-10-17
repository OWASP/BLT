/// ztr-finding-1 envelope builder + HMAC signing (parity with `src/envelope.py`).
library;

import 'dart:typed_data';

import 'canonicalize.dart';

const String ztrVersion = 'ztr-finding-1';
const String ztrAlg = 'hmac-sha256';

class EnvelopeValidationException implements Exception {
  EnvelopeValidationException(this.message);
  final String message;
  @override
  String toString() => 'EnvelopeValidationException: $message';
}

/// Build a signed plaintext-mode finding envelope ready for POST /api/ingest.
Map<String, Object?> prepareSignedPlaintextEnvelope({
  required String orgId,
  required String senderId,
  required String kid,
  required Uint8List secret,
  required Map<String, Object?> payload,
  required String issuedAt,
  required String nonce,
}) {
  final envelope = <String, Object?>{
    'version': ztrVersion,
    'org_id': orgId,
    'sender_id': senderId,
    'kid': kid,
    'alg': ztrAlg,
    'issued_at': issuedAt,
    'nonce': nonce,
    'plaintext_mode': true,
    'payload_plaintext': payload,
  };
  return prepareSignedEnvelope(envelope, secret);
}

Map<String, Object?> prepareSignedEnvelope(
  Map<String, Object?> envelope,
  Uint8List secret,
) {
  _validateShape(envelope, forSigning: true);
  if (envelope['payload_digest'] == null ||
      (envelope['payload_digest'] as String).isEmpty) {
    final plaintext = envelope['payload_plaintext'];
    final ciphertext = envelope['payload_ciphertext'];
    envelope['payload_digest'] = payloadDigestHex(
      plaintext: plaintext is Map<String, Object?>
          ? Map<String, Object?>.from(plaintext)
          : (plaintext is Map
              ? plaintext.map((k, v) => MapEntry(k.toString(), v as Object?))
              : null),
      ciphertextB64: ciphertext is String ? ciphertext : null,
    );
  }
  envelope['signature'] = _signEnvelope(envelope, secret);
  return envelope;
}

/// Compact UTF-8 JSON bytes for the HTTP body (unsorted keys — wire format).
Uint8List encodeEnvelopeBody(Map<String, Object?> envelope) {
  // Use canonical encoding for stable digests in tests; wire body must be the
  // exact bytes we hash. Prefer sorted keys so Dart/Python clients agree when
  // both use sort_keys.
  return canonicalizeJson(envelope);
}

String _signEnvelope(Map<String, Object?> envelope, Uint8List secret) {
  final message = canonicalizeEnvelopeForSigning(envelope);
  return hmacSha256Hex(secret, message);
}

void _validateShape(Map<String, Object?> envelope, {required bool forSigning}) {
  if (envelope['version'] != ztrVersion) {
    throw EnvelopeValidationException('version must be $ztrVersion');
  }
  const requiredCore = [
    'version',
    'org_id',
    'sender_id',
    'kid',
    'alg',
    'issued_at',
    'nonce',
  ];
  final missing = requiredCore.where((f) => !envelope.containsKey(f)).toList();
  if (missing.isNotEmpty) {
    throw EnvelopeValidationException(
      'missing required fields: ${missing.join(', ')}',
    );
  }
  final plaintext = envelope['payload_plaintext'];
  final ciphertext = envelope['payload_ciphertext'];
  final plaintextMode = envelope['plaintext_mode'];
  if (plaintext != null && ciphertext != null) {
    throw EnvelopeValidationException(
      'payload_plaintext and payload_ciphertext are mutually exclusive',
    );
  }
  if (plaintext == null && ciphertext == null) {
    throw EnvelopeValidationException('exactly one payload field is required');
  }
  if (plaintext != null) {
    if (plaintextMode != true) {
      throw EnvelopeValidationException(
        'plaintext_mode must be true when payload_plaintext is set',
      );
    }
    if (plaintext is! Map) {
      throw EnvelopeValidationException('payload_plaintext must be a JSON object');
    }
  } else if (plaintextMode == true) {
    throw EnvelopeValidationException(
      'plaintext_mode true requires payload_plaintext',
    );
  }
  if (envelope['alg'] != ztrAlg) {
    throw EnvelopeValidationException('alg must be $ztrAlg');
  }
  if (!forSigning) {
    for (final field in ['payload_digest', 'signature']) {
      if (!envelope.containsKey(field)) {
        throw EnvelopeValidationException('missing required fields: $field');
      }
    }
  }
}

/// Hex-decode a sender secret (e.g. demo `736563726574`).
Uint8List secretFromHex(String hex) {
  final cleaned = hex.trim().replaceAll(RegExp(r'\s+'), '');
  if (cleaned.length.isOdd) {
    throw FormatException('secret hex must have even length');
  }
  final out = Uint8List(cleaned.length ~/ 2);
  for (var i = 0; i < out.length; i++) {
    out[i] = int.parse(cleaned.substring(i * 2, i * 2 + 2), radix: 16);
  }
  return out;
}

String issuedAtNowUtc() {
  final now = DateTime.now().toUtc();
  String two(int n) => n.toString().padLeft(2, '0');
  return '${now.year.toString().padLeft(4, '0')}-'
      '${two(now.month)}-${two(now.day)}T'
      '${two(now.hour)}:${two(now.minute)}:${two(now.second)}Z';
}
