import 'package:flutter_test/flutter_test.dart';
import 'package:netguardian_client/detect/http_headers.dart';
import 'package:netguardian_client/detect/normalize.dart';

const url = 'https://app.example';
const secure = {
  'Strict-Transport-Security': 'max-age=15552000; includeSubDomains',
  'Content-Security-Policy': "default-src 'self'; frame-ancestors 'none'",
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
};

void main() {
  test('fingerprint is stable like Python normalize', () {
    final a = computeFingerprint(
      ruleId: 'http.missing-hsts',
      target: 'https://example.com',
      locator: 'Strict-Transport-Security',
    );
    expect(a, 'fp-befbeac0452fe85bd507ec1b10c4fa3a');
  });

  test('fingerprint strips like Python', () {
    final a = computeFingerprint(
      ruleId: ' http.missing-hsts ',
      target: ' https://example.com ',
      locator: ' Strict-Transport-Security ',
    );
    expect(a, 'fp-befbeac0452fe85bd507ec1b10c4fa3a');
  });

  test('hardened response yields no findings', () {
    expect(scanHeaders(url, secure), isEmpty);
  });

  test('missing CSP is medium (Python parity)', () {
    final findings = scanHeaders(url, {
      'content-type': 'text/html',
    });
    final csp = findings.firstWhere((f) => f.ruleId == 'http.missing-csp');
    expect(csp.severity, 'medium');
  });

  test('clickjacking locator is X-Frame-Options', () {
    final findings = scanHeaders(url, {
      'Content-Security-Policy': "default-src 'self'",
    });
    final cj = findings.firstWhere(
      (f) => f.ruleId == 'http.missing-clickjacking-protection',
    );
    expect(cj.locator, 'X-Frame-Options');
  });

  test('frame-ancestors self is protective', () {
    final findings = scanHeaders(url, {
      ...secure,
      'Content-Security-Policy': "default-src 'self'; frame-ancestors 'self'",
    });
    expect(
      findings.any((f) => f.ruleId == 'http.missing-clickjacking-protection'),
      isFalse,
    );
  });

  test('insecure cookie uses exact attributes and per-cookie locator', () {
    final findings = scanHeaders(url, {
      ...secure,
      'Set-Cookie': 'sid=abc; Path=/',
    });
    final cookie = findings.singleWhere(
      (f) => f.ruleId == 'http.insecure-cookie-flags',
    );
    expect(cookie.severity, 'high');
    expect(cookie.locator, 'Set-Cookie:sid');
    expect(cookie.evidence['missing_flags'], ['secure', 'httponly']);
  });

  test('substring Secure in cookie value is not an attribute', () {
    final findings = scanHeaders(url, {
      ...secure,
      'Set-Cookie': 'sid=notsecure; HttpOnly',
    });
    final cookie = findings.singleWhere(
      (f) => f.ruleId == 'http.insecure-cookie-flags',
    );
    expect(cookie.evidence['missing_flags'], ['secure']);
  });

  test('scanHeaders skips error responses', () {
    expect(scanHeaders(url, {}, status: 500), isEmpty);
  });
}
