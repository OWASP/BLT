import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:netguardian_client/ingest/payload_crypto.dart';

final key = Uint8List.fromList(utf8.encode('netguardian-demo-aesgcm-key-0032'));

void main() {
  test('AES-256-GCM roundtrip matches Python wire format', () async {
    final payload = {'rule_id': 'sqli', 'password': 'hunter2', 'n': 3};
    final token = await encryptPayload(
      key: key,
      payload: payload,
      aad: utf8.encode('org-a'),
    );
    final out = await decryptPayload(
      key: key,
      tokenB64: token,
      aad: utf8.encode('org-a'),
    );
    expect(out['rule_id'], 'sqli');
    expect(out['password'], 'hunter2');
    expect(out['n'], 3);
    final blob = base64Decode(token);
    expect(blob.length, greaterThan(12 + 16));
  });

  test('wrong AAD fails', () async {
    final token = await encryptPayload(
      key: key,
      payload: {'a': 1},
      aad: utf8.encode('org-a'),
    );
    expect(
      () => decryptPayload(
        key: key,
        tokenB64: token,
        aad: utf8.encode('org-b'),
      ),
      throwsA(isA<PayloadCryptoException>()),
    );
  });

  test('decrypts Python golden token (fixed nonce)', () async {
    const token = 'MDEyMzQ1Njc4OWFib5ZgrAMvzYVMfjIULs789XfT3z7emSGi9/MSJcZXTN00jEKm2BZvqg==';
    final out = await decryptPayload(
      key: key,
      tokenB64: token,
      aad: utf8.encode('org-a'),
    );
    expect(out['rule_id'], 'sqli');
    expect(out['n'], 3);
  });

  test('demo key b64 decodes to 32 bytes', () {
    final decoded = payloadKeyFromB64(
      'bmV0Z3VhcmRpYW4tZGVtby1hZXNnY20ta2V5LTAwMzI=',
    );
    expect(decoded, key);
  });
}
