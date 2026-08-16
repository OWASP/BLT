/// JCS-profile JSON canonicalization matching `src/canonicalize.py`.
library;

import 'dart:convert';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';

/// RFC 8785-compatible profile: sorted keys, compact separators, UTF-8.
Uint8List canonicalizeJson(Object? value) {
  return Uint8List.fromList(utf8.encode(_encode(value)));
}

String canonicalizeJsonString(Object? value) => _encode(value);

Uint8List canonicalizeEnvelopeForSigning(Map<String, Object?> envelope) {
  final unsigned = Map<String, Object?>.from(envelope)..remove('signature');
  return canonicalizeJson(unsigned);
}

String bodyDigestHex(Uint8List rawBody) => sha256.convert(rawBody).toString();

String payloadDigestHex({
  Map<String, Object?>? plaintext,
  String? ciphertextB64,
}) {
  if (plaintext != null && ciphertextB64 != null) {
    throw ArgumentError('exactly one payload mode');
  }
  late final Uint8List payloadBytes;
  if (plaintext != null) {
    payloadBytes = canonicalizeJson(plaintext);
  } else if (ciphertextB64 != null) {
    payloadBytes = Uint8List.fromList(base64Decode(ciphertextB64));
  } else {
    throw ArgumentError('missing payload');
  }
  return sha256.convert(payloadBytes).toString();
}

String hmacSha256Hex(Uint8List secret, Uint8List message) {
  final digest = Hmac(sha256, secret).convert(message);
  return digest.toString();
}

String _encode(Object? value) {
  if (value == null) return 'null';
  if (value is bool) return value ? 'true' : 'false';
  if (value is num) {
    if (value is double && (value.isNaN || value.isInfinite)) {
      throw ArgumentError('NaN/Infinity not allowed');
    }
    // Match Python json.dumps for ints/floats used in envelopes.
    if (value is int) return value.toString();
    final d = value.toDouble();
    if (d == d.truncateToDouble() && !d.isNegative) {
      // 1.0 → 1 in Python when it's an int-like? Actually Python keeps 1.0 as 1.0
      // for float. Only int type becomes without decimal.
    }
    var s = d.toString();
    if (s.endsWith('.0') && d == d.roundToDouble()) {
      // Dart toString on 1.0 is "1.0" — good, matches Python float.
    }
    return s;
  }
  if (value is String) return jsonEncode(value);
  if (value is List) {
    final parts = value.map(_encode).join(',');
    return '[$parts]';
  }
  if (value is Map) {
    final keys = value.keys.map((k) => k.toString()).toList()..sort();
    final parts = <String>[];
    for (final key in keys) {
      parts.add('${jsonEncode(key)}:${_encode(value[key])}');
    }
    return '{${parts.join(',')}}';
  }
  throw ArgumentError('unsupported JSON type: ${value.runtimeType}');
}
