/// Client-side continuous crawl: fetch page → header scan → extract domains → queue.
///
/// Runs entirely on the user machine (Flutter desktop). The Worker is never used
/// as an open proxy to spider third-party sites.
library;

import 'package:http/http.dart' as http;

import 'http_headers.dart';
import 'link_extract.dart';
import 'normalize.dart';

class CrawlConfig {
  const CrawlConfig({
    this.maxPages = 25,
    this.maxNewHosts = 40,
    this.maxSameHostPaths = 8,
    this.delay = const Duration(milliseconds: 400),
    this.followExternalHosts = true,
    this.sameHostPathCrawl = true,
  });

  /// Hard cap on HTTP GETs this run.
  final int maxPages;

  /// Cap on newly discovered hosts enqueued from HTML.
  final int maxNewHosts;

  /// Cap on additional same-host paths (beyond the seed URL).
  final int maxSameHostPaths;

  /// Pause between requests (polite continuous crawl).
  final Duration delay;

  /// When true, enqueue absolute links to other hosts found in page source.
  final bool followExternalHosts;

  /// When true, also crawl a few same-host paths discovered from links.
  final bool sameHostPathCrawl;
}

class CrawlProgress {
  const CrawlProgress({
    required this.scanned,
    required this.queued,
    required this.discoveredHosts,
    required this.currentUrl,
    required this.findingsSoFar,
    this.done = false,
  });

  final int scanned;
  final int queued;
  final int discoveredHosts;
  final String currentUrl;
  final int findingsSoFar;
  final bool done;
}

class CrawlResult {
  const CrawlResult({
    required this.findings,
    required this.visitedUrls,
    required this.discoveredHosts,
    required this.pagesScanned,
  });

  final List<DetectionFinding> findings;
  final List<String> visitedUrls;
  final List<String> discoveredHosts;
  final int pagesScanned;
}

DetectionFinding _discoveredHostFinding({
  required String seedUrl,
  required String discoveredHost,
  required String sourceUrl,
}) {
  return DetectionFinding(
    ruleId: 'crawl.discovered-domain',
    severity: 'info',
    title: 'Discovered related domain in page source',
    target: 'https://$discoveredHost/',
    locator: 'html-link',
    evidence: {
      'discovered_host': discoveredHost,
      'source_url': sourceUrl,
      'seed_url': seedUrl,
    },
    remediation:
        'Review whether this host is in-scope for your org; schedule a follow-up '
        'header scan if authorized.',
  );
}

/// Continuous client-side crawl starting at [seedUrl].
///
/// For each page: header-scan, parse HTML for links, enqueue new hosts (and a
/// few same-host paths), then continue until caps are hit.
Future<CrawlResult> crawlAndScan(
  String seedUrl, {
  CrawlConfig config = const CrawlConfig(),
  http.Client? client,
  void Function(CrawlProgress progress)? onProgress,
}) async {
  final seed = Uri.tryParse(seedUrl.trim());
  if (seed == null || !seed.hasScheme || seed.host.isEmpty) {
    throw ArgumentError('Invalid seed URL: $seedUrl');
  }
  if (seed.scheme != 'http' && seed.scheme != 'https') {
    throw ArgumentError('Seed must be http(s)');
  }

  final httpClient = client ?? http.Client();
  final owned = client == null;

  final queue = <Uri>[seed.replace(fragment: '')];
  final visited = <String>{};
  final knownHosts = <String>{hostKey(seed)};
  final discoveredHosts = <String>[];
  final findings = <DetectionFinding>[];
  final visitedUrls = <String>[];
  var newHostEnqueued = 0;
  var sameHostPathsEnqueued = 0;
  var pagesScanned = 0;

  try {
    while (queue.isNotEmpty && pagesScanned < config.maxPages) {
      final url = queue.removeAt(0);
      final urlKey = url.toString();
      if (!visited.add(urlKey)) continue;

      onProgress?.call(CrawlProgress(
        scanned: pagesScanned,
        queued: queue.length,
        discoveredHosts: discoveredHosts.length,
        currentUrl: urlKey,
        findingsSoFar: findings.length,
      ));

      http.Response response;
      try {
        response = await httpClient.get(url).timeout(const Duration(seconds: 20));
      } catch (_) {
        pagesScanned += 1;
        visitedUrls.add(urlKey);
        if (config.delay > Duration.zero) {
          await Future<void>.delayed(config.delay);
        }
        continue;
      }

      pagesScanned += 1;
      visitedUrls.add(urlKey);
      findings.addAll(
        scanHeaders(urlKey, response.headers, status: response.statusCode),
      );

      final contentType = response.headers.entries
          .firstWhere(
            (e) => e.key.toLowerCase() == 'content-type',
            orElse: () => const MapEntry('content-type', ''),
          )
          .value
          .toLowerCase();
      final looksHtml = contentType.contains('html') ||
          contentType.isEmpty ||
          response.body.trimLeft().toLowerCase().startsWith('<!doctype') ||
          response.body.trimLeft().toLowerCase().startsWith('<html');

      if (looksHtml && response.statusCode < 400) {
        final links = extractUrlsFromHtml(response.body, urlKey);
        for (final link in links) {
          final host = hostKey(link);
          final isNewHost = !knownHosts.contains(host);

          if (isNewHost) {
            knownHosts.add(host);
            discoveredHosts.add(host);
            findings.add(_discoveredHostFinding(
              seedUrl: seed.toString(),
              discoveredHost: host,
              sourceUrl: urlKey,
            ));
            if (config.followExternalHosts &&
                newHostEnqueued < config.maxNewHosts) {
              final root = Uri(
                scheme: link.scheme,
                host: link.host,
                port: link.hasPort ? link.port : null,
                path: '/',
              );
              final rootKey = root.toString();
              if (!visited.contains(rootKey) &&
                  !queue.any((q) => q.toString() == rootKey)) {
                queue.add(root);
                newHostEnqueued += 1;
              }
            }
            continue;
          }

          if (config.sameHostPathCrawl &&
              host == hostKey(seed) &&
              sameHostPathsEnqueued < config.maxSameHostPaths) {
            final pathKey = link.toString();
            if (!visited.contains(pathKey) &&
                !queue.any((q) => q.toString() == pathKey)) {
              queue.add(link);
              sameHostPathsEnqueued += 1;
            }
          }
        }
      }

      onProgress?.call(CrawlProgress(
        scanned: pagesScanned,
        queued: queue.length,
        discoveredHosts: discoveredHosts.length,
        currentUrl: urlKey,
        findingsSoFar: findings.length,
      ));

      if (config.delay > Duration.zero &&
          (queue.isNotEmpty && pagesScanned < config.maxPages)) {
        await Future<void>.delayed(config.delay);
      }
    }

    onProgress?.call(CrawlProgress(
      scanned: pagesScanned,
      queued: queue.length,
      discoveredHosts: discoveredHosts.length,
      currentUrl: '',
      findingsSoFar: findings.length,
      done: true,
    ));

    return CrawlResult(
      findings: findings,
      visitedUrls: visitedUrls,
      discoveredHosts: List.unmodifiable(discoveredHosts),
      pagesScanned: pagesScanned,
    );
  } finally {
    if (owned) httpClient.close();
  }
}
