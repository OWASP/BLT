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

  test('extractUrlsFromHtml picks domains out of JS/CSS source', () {
    const html = '''
      <html><script>
        const api = "https://hidden.test/v1/status";
      </script>
      <style>body { background: url(https://cdn.hidden.test/bg.png); }</style>
    ''';
    final urls = extractUrlsFromHtml(html, 'https://seed.test/');
    final hosts = urls.map((u) => u.host).toSet();
    expect(hosts, contains('hidden.test'));
    expect(hosts, contains('cdn.hidden.test'));
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
        maxPathsPerHost: 0,
        delay: Duration.zero,
      ),
    );

    expect(result.pagesScanned, greaterThanOrEqualTo(2));
    expect(result.discoveredHosts, contains('other.test'));
    expect(
      result.findings.any((f) => f.ruleId == 'crawl.discovered-domain'),
      isTrue,
    );
    expect(
      result.findings.any((f) => f.ruleId == 'http.missing-hsts'),
      isTrue,
    );
  });

  test('crawl spiders paths on discovered hosts, not only the seed', () async {
    final seen = <String>[];
    final client = MockClient((request) async {
      seen.add(request.url.toString());
      if (request.url.host == 'seed.test') {
        return http.Response(
          '<html><a href="https://other.test/">x</a></html>',
          200,
          headers: {'content-type': 'text/html'},
          request: request,
        );
      }
      if (request.url.host == 'other.test' && request.url.path == '/') {
        return http.Response(
          '<html><a href="/app">app</a><script>fetch("https://third.test/x")</script></html>',
          200,
          headers: {'content-type': 'text/html'},
          request: request,
        );
      }
      return http.Response(
        '<html>ok</html>',
        200,
        headers: {'content-type': 'text/html'},
        request: request,
      );
    });

    final result = await crawlAndScan(
      'https://seed.test/',
      client: client,
      config: const CrawlConfig(
        maxPages: 10,
        maxNewHosts: 10,
        maxPathsPerHost: 4,
        delay: Duration.zero,
      ),
    );

    expect(seen.any((u) => u.contains('other.test') && u.contains('/app')), isTrue);
    expect(result.discoveredHosts, containsAll(['other.test', 'third.test']));
  });

  test('continuous crawl revisits after the frontier drains', () async {
    var hits = 0;
    final client = MockClient((request) async {
      hits += 1;
      return http.Response(
        '<html>ok</html>',
        200,
        headers: {'content-type': 'text/html'},
        request: request,
      );
    });

    final result = await crawlAndScan(
      'https://seed.test/',
      client: client,
      config: const CrawlConfig(
        maxPages: 4,
        maxNewHosts: 1,
        maxPathsPerHost: 0,
        delay: Duration.zero,
        continuous: true,
        revisitAfter: Duration.zero,
        idleWait: Duration.zero,
      ),
    );

    expect(result.pagesScanned, 4);
    expect(hits, 4);
    expect(
      result.visitedUrls.where((u) => u.contains('seed.test')).length,
      greaterThan(1),
    );
  });

  test('CrawlRun.stop ends a continuous crawl', () async {
    final run = CrawlRun();
    var hits = 0;
    final client = MockClient((request) async {
      hits += 1;
      if (hits >= 2) run.stop();
      return http.Response(
        '<html>ok</html>',
        200,
        headers: {'content-type': 'text/html'},
        request: request,
      );
    });

    final result = await crawlAndScan(
      'https://seed.test/',
      client: client,
      run: run,
      config: const CrawlConfig(
        maxPages: 0,
        delay: Duration.zero,
        continuous: true,
        revisitAfter: Duration.zero,
        idleWait: Duration.zero,
      ),
    );

    expect(result.stopped, isTrue);
    expect(result.pagesScanned, greaterThanOrEqualTo(2));
    expect(result.pagesScanned, lessThan(20));
  });
}
