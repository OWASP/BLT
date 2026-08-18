import 'package:flutter_test/flutter_test.dart';
import 'package:selferase/services/url_signal_extractor.dart';

void main() {
  group('UrlSignalExtractor', () {
    final extractor = UrlSignalExtractor();

    test('scores benign URLs without phishing flags', () {
      final signals = extractor.extract(Uri.parse('https://www.example.com/about'));

      expect(signals['risky_tld'], 0.0);
      expect(signals['suspicious_tokens'], 0.0);
      expect(signals['query_anomaly'], 0.0);
      expect(signals['entropy'], inInclusiveRange(0.0, 1.0));
    });

    test('flags typo-style domains with risky TLDs', () {
      final signals = extractor.extract(
        Uri.parse('https://paypa1-account-support.top/reset'),
      );

      expect(signals['risky_tld'], 1.0);
      expect(signals['suspicious_tokens'], 0.7);
      expect(signals['entropy'], greaterThan(0.0));
    });

    test('flags phishing-like URLs and long query strings', () {
      final signals = extractor.extract(
        Uri.parse(
          'https://secure-login-verify.xyz/update?token=123456&session=abcdef&redirect=wallet',
        ),
      );

      expect(signals['risky_tld'], 1.0);
      expect(signals['suspicious_tokens'], 0.7);
      expect(signals['query_anomaly'], greaterThan(0.0));
    });
  });
}
