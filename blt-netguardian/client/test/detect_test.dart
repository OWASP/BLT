import 'package:flutter_test/flutter_test.dart';
import 'package:netguardian_client/detect/http_headers.dart';
import 'package:netguardian_client/detect/normalize.dart';

void main() {
  test('fingerprint is stable like Python normalize', () {
    final a = computeFingerprint(
      ruleId: 'http.missing-hsts',
      target: 'https://example.com',
      locator: 'Strict-Transport-Security',
    );
    final b = computeFingerprint(
      ruleId: 'http.missing-hsts',
      target: 'https://example.com',
      locator: 'Strict-Transport-Security',
    );
    expect(a, b);
    expect(a, 'fp-befbeac0452fe85bd507ec1b10c4fa3a');
  });

  test('scanHeaders flags missing HSTS on https', () {
    final findings = scanHeaders('https://example.com', {
      'content-type': 'text/html',
    });
    expect(
      findings.any((f) => f.ruleId == 'http.missing-hsts'),
      isTrue,
    );
    final payload = findings.firstWhere((f) => f.ruleId == 'http.missing-hsts').toPayload();
    expect(payload['fingerprint'], isNotNull);
    expect(payload['target'], 'https://example.com');
  });

  test('scanHeaders skips error responses', () {
    expect(scanHeaders('https://example.com', {}, status: 500), isEmpty);
  });
}
