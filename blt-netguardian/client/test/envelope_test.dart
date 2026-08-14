import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:netguardian_client/ingest/canonicalize.dart';
import 'package:netguardian_client/ingest/envelope.dart';

void main() {
  test('canonical JSON sorts keys like Python', () {
    final payload = <String, Object?>{
      'rule_id': 'http.missing-hsts',
      'severity': 'high',
      'title': 'Missing HSTS',
      'target': 'https://example.com',
      'fingerprint': 'fp-client-test-1',
    };
    expect(
      canonicalizeJsonString(payload),
      '{"fingerprint":"fp-client-test-1","rule_id":"http.missing-hsts",'
      '"severity":"high","target":"https://example.com","title":"Missing HSTS"}',
    );
  });

  test('signed envelope matches Python golden vector', () {
    final payload = <String, Object?>{
      'rule_id': 'http.missing-hsts',
      'severity': 'high',
      'title': 'Missing HSTS',
      'target': 'https://example.com',
      'fingerprint': 'fp-client-test-1',
    };
    final secret = secretFromHex('736563726574');
    final signed = prepareSignedPlaintextEnvelope(
      orgId: 'org-demo',
      senderId: 'scanner-1',
      kid: 'k1',
      secret: secret,
      payload: payload,
      issuedAt: '2026-08-14T00:00:00Z',
      nonce: 'client-test-1',
    );
    expect(
      signed['payload_digest'],
      '1f79d2b1cfca357b32817f159fd4ef3f9d4700b13dc228b792202f2cae6a2235',
    );
    expect(
      signed['signature'],
      'cf64993ae9e3e71b93969c97e2a6d5e823ad503055321ee4e94ca2e4d5421593',
    );
    final raw = encodeEnvelopeBody(signed);
    expect(
      bodyDigestHex(raw),
      // Canonical wire body digest for the signed map.
      bodyDigestHex(Uint8List.fromList(utf8.encode(canonicalizeJsonString(signed)))),
    );
  });
}
