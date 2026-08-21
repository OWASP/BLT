import 'package:flutter_test/flutter_test.dart';
import 'package:netguardian_client/detect/domain_normalize.dart';

void main() {
  test('normalizeDomain collapses www, scheme, path, case', () {
    final a = normalizeDomain('HTTPS://WWW.Example.COM/path?q=1');
    final b = normalizeDomain('http://example.com/');
    final c = normalizeDomain('example.com');
    expect(a!.hostKey, 'example.com');
    expect(a.seedUrl, 'https://example.com/');
    expect(b!.hostKey, a.hostKey);
    expect(c!.hostKey, a.hostKey);
  });

  test('normalizeDomain rejects loopback', () {
    expect(normalizeDomain('http://localhost/'), isNull);
    expect(normalizeDomain('mailto:x@example.com'), isNull);
  });
}
