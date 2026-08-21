import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:netguardian_client/detect/crawl.dart';
import 'package:netguardian_client/detect/link_extract.dart';

void main() {
  test('extractUrlsFromHtml resolves relative and absolute links', () {
    const html = '''
      <html><body>
        <a href="/about">About</a>
        <a href="https://cdn.partner.test/lib.js">cdn</a>
        <img src="//assets.example.com/x.png">
        <a href="mailto:sec@example.com">mail</a>
        <script src="https://analytics.other.test/a.js"></script>
      </body></html>
    ''';
    final urls = extractUrlsFromHtml(html, 'https://app.example.com/home');
    final asStrings = urls.map((u) => u.toString()).toSet();
    expect(asStrings, contains('https://app.example.com/about'));
    expect(asStrings, contains('https://cdn.partner.test/lib.js'));
    expect(asStrings, contains('https://assets.example.com/x.png'));
    expect(asStrings, contains('https://analytics.other.test/a.js'));
    expect(asStrings.any((s) => s.contains('mailto')), isFalse);
  });

  test('crawlAndScan discovers external host and header-scans seed', () async {
    final client = MockClient((request) async {
      if (request.url.host == 'seed.test') {
        return http.Response(
          '<html><a href="https://other.test/">x</a></html>',
          200,
          headers: {'content-type': 'text/html'},
          request: request,
        );
      }
      if (request.url.host == 'other.test') {
        return http.Response(
          '<html>ok</html>',
          200,
          headers: {
            'content-type': 'text/html',
            'Strict-Transport-Security': 'max-age=15552000',
            'Content-Security-Policy': "default-src 'self'; frame-ancestors 'none'",
            'X-Content-Type-Options': 'nosniff',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
          },
          request: request,
        );
      }
      return http.Response('missing', 404, request: request);
    });

    final result = await crawlAndScan(
      'https://seed.test/',
      client: client,
      config: const CrawlConfig(
        maxPages: 5,
        maxNewHosts: 5,
        maxSameHostPaths: 0,
        delay: Duration.zero,
      ),
    );

    expect(result.pagesScanned, greaterThanOrEqualTo(2));
    expect(result.discoveredHosts, contains('other.test'));
    expect(
      result.findings.any((f) => f.ruleId == 'crawl.discovered-domain'),
      isTrue,
    );
    // seed.test had no security headers → findings present
    expect(
      result.findings.any((f) => f.ruleId == 'http.missing-hsts'),
      isTrue,
    );
  });
}
