import 'package:flutter_test/flutter_test.dart';
import 'package:netguardian_client/ingest/redact.dart';

void main() {
  test('redactPayload masks secret keys recursively', () {
    final out = redactPayload({
      'rule_id': 'http.missing-hsts',
      'token': 'super-secret',
      'evidence': {
        'password': 'hunter2',
        'note': 'ok',
        'nested': {'api_key': 'abc'},
      },
    });
    expect(out['token'], '[REDACTED]');
    expect((out['evidence'] as Map)['password'], '[REDACTED]');
    expect((out['evidence'] as Map)['note'], 'ok');
    expect(((out['evidence'] as Map)['nested'] as Map)['api_key'], '[REDACTED]');
    expect(out['rule_id'], 'http.missing-hsts');
  });
}
