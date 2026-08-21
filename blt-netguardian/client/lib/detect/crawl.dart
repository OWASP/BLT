/// Client-side crawl: fetch page → header scan → extract domains from source → queue.
///
/// Runs on the user machine. The Worker is never used as an open proxy.
/// One-shot mode stops at [CrawlConfig.maxPages]. Continuous mode keeps
/// spidering until [CrawlRun.stop] (revisits host roots when the frontier
/// drains).
library;

import 'package:http/http.dart' as http;

import 'http_headers.dart';
import 'link_extract.dart';
import 'normalize.dart';

class CrawlConfig {
  const CrawlConfig({
    this.maxPages = 0,
    this.maxNewHosts = 200,
    this.maxPathsPerHost = 12,
    this.maxQueue = 400,
    this.delay = const Duration(milliseconds: 400),
    this.followExternalHosts = true,
    this.sameHostPathCrawl = true,
    this.continuous = false,
    this.revisitAfter = const Duration(minutes: 2),
    this.idleWait = const Duration(seconds: 3),
  });

  /// Hard cap on GETs this run. `0` means unlimited (continuous / until stop).
  final int maxPages;

  /// Cap on newly discovered hosts enqueued from page source.
  final int maxNewHosts;

  /// Cap on extra paths crawled per host (beyond the host root).
  final int maxPathsPerHost;

  /// Bound the in-memory frontier.
  final int maxQueue;

  /// Pause between requests.
  final Duration delay;

  /// Enqueue other hosts found in HTML/JS/CSS.
  final bool followExternalHosts;

  /// Also crawl same-host paths discovered from links (every host, not just seed).
  final bool sameHostPathCrawl;

  /// Keep running after the queue drains: revisit known host roots.
  final bool continuous;

  /// How long before a visited URL may be fetched again in continuous mode.
  final Duration revisitAfter;

  /// Pause when the frontier is empty before recycling hosts.
  final Duration idleWait;
}

/// Cooperative cancel for a running crawl.
class CrawlRun {
  bool _stop = false;
  void stop() => _stop = true;
  bool get stopped => _stop;
}

class CrawlProgress {
  const CrawlProgress({
    required this.scanned,
    required this.queued,
    required this.discoveredHosts,
    required this.currentUrl,
    required this.findingsSoFar,
    this.done = false,
    this.idle = false,
  });

  final int scanned;
  final int queued;
  final int discoveredHosts;
  final String currentUrl;
  final int findingsSoFar;
  final bool done;
  final bool idle;
}

class CrawlResult {
  const CrawlResult({
    required this.findings,
    required this.visitedUrls,
    required this.discoveredHosts,
    required this.pagesScanned,
    this.stopped = false,
  });

  final List<DetectionFinding> findings;
  final List<String> visitedUrls;
  final List<String> discoveredHosts;
  final int pagesScanned;
  final bool stopped;
}

DetectionFinding discoveredHostFinding({
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

bool _looksHtml(http.Response response) {
  final contentType = response.headers.entries
      .firstWhere(
        (e) => e.key.toLowerCase() == 'content-type',
        orElse: () => const MapEntry('content-type', ''),
      )
      .value
      .toLowerCase();
  if (contentType.contains('html') || contentType.contains('javascript')) {
    return true;
  }
  final start = response.body.trimLeft().toLowerCase();
  return contentType.isEmpty ||
      start.startsWith('<!doctype') ||
      start.startsWith('<html');
}

bool _pageCapReached(CrawlConfig config, int pagesScanned) {
  return config.maxPages > 0 && pagesScanned >= config.maxPages;
}

/// Crawl starting at [seedUrl].
///
/// One-shot (`continuous: false`): stop when the queue is empty or [maxPages].
/// Continuous: spider until [run.stop], recycling host roots when idle.
Future<CrawlResult> crawlAndScan(
  String seedUrl, {
  CrawlConfig config = const CrawlConfig(),
  http.Client? client,
  CrawlRun? run,
  void Function(CrawlProgress progress)? onProgress,
  void Function(DetectionFinding finding)? onFinding,
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
  final session = run ?? CrawlRun();
  final seedClean = stripFragment(seed);

  final queue = <Uri>[seedClean];
  final queuedKeys = <String>{seedClean.toString()};
  final visitedAt = <String, DateTime>{};
  final knownHosts = <String>{hostKey(seedClean)};
  final discoveredHosts = <String>[];
  final findings = <DetectionFinding>[];
  final findingKeys = <String>{};
  final visitedUrls = <String>[];
  final pathsPerHost = <String, int>{};
  var newHostEnqueued = 0;
  var pagesScanned = 0;

  bool atPageCap() => _pageCapReached(config, pagesScanned);

  void emitFinding(DetectionFinding finding) {
    if (!findingKeys.add(finding.fingerprint)) return;
    findings.add(finding);
    onFinding?.call(finding);
  }

  bool enqueue(Uri uri) {
    final clean = stripFragment(uri);
    final key = clean.toString();
    if (queuedKeys.contains(key)) return false;
    if (queue.length >= config.maxQueue) return false;
    final last = visitedAt[key];
    if (last != null) {
      if (!config.continuous) return false;
      if (DateTime.now().difference(last) < config.revisitAfter) return false;
    }
    queue.add(clean);
    queuedKeys.add(key);
    return true;
  }

  void recycleFrontier() {
    for (final host in knownHosts) {
      enqueue(Uri(scheme: 'https', host: host, path: '/'));
    }
  }

  try {
    while (!session.stopped && !atPageCap()) {
      if (queue.isEmpty) {
        if (!config.continuous) break;
        onProgress?.call(CrawlProgress(
          scanned: pagesScanned,
          queued: 0,
          discoveredHosts: discoveredHosts.length,
          currentUrl: '',
          findingsSoFar: findings.length,
          idle: true,
        ));
        if (config.idleWait > Duration.zero) {
          await Future<void>.delayed(config.idleWait);
        }
        if (session.stopped) break;
        recycleFrontier();
        if (queue.isEmpty) {
          await Future<void>.delayed(config.idleWait);
          continue;
        }
      }

      final url = queue.removeAt(0);
      queuedKeys.remove(url.toString());
      final urlKey = url.toString();
      final last = visitedAt[urlKey];
      if (last != null &&
          (!config.continuous ||
              DateTime.now().difference(last) < config.revisitAfter)) {
        continue;
      }

      onProgress?.call(CrawlProgress(
        scanned: pagesScanned,
        queued: queue.length,
        discoveredHosts: discoveredHosts.length,
        currentUrl: urlKey,
        findingsSoFar: findings.length,
      ));

      http.Response? response;
      try {
        response =
            await httpClient.get(url).timeout(const Duration(seconds: 20));
      } catch (_) {
        response = null;
      }

      pagesScanned += 1;
      visitedUrls.add(urlKey);
      visitedAt[urlKey] = DateTime.now();

      if (response != null) {
        for (final f in scanHeaders(
          urlKey,
          response.headers,
          status: response.statusCode,
        )) {
          emitFinding(f);
        }

        if (_looksHtml(response) && response.statusCode < 400) {
          final links = extractUrlsFromHtml(response.body, urlKey);
          for (final link in links) {
            final host = hostKey(link);
            final isNewHost = !knownHosts.contains(host);

            if (isNewHost) {
              knownHosts.add(host);
              discoveredHosts.add(host);
              emitFinding(discoveredHostFinding(
                seedUrl: seedClean.toString(),
                discoveredHost: host,
                sourceUrl: urlKey,
              ));
              if (config.followExternalHosts &&
                  newHostEnqueued < config.maxNewHosts) {
                if (enqueue(hostRoot(link))) newHostEnqueued += 1;
              }
              continue;
            }

            if (config.sameHostPathCrawl) {
              final used = pathsPerHost[host] ?? 0;
              if (used < config.maxPathsPerHost &&
                  link.path != '/' &&
                  link.path.isNotEmpty) {
                if (enqueue(link)) {
                  pathsPerHost[host] = used + 1;
                }
              }
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
          !session.stopped &&
          !atPageCap() &&
          (queue.isNotEmpty || config.continuous)) {
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
      stopped: session.stopped,
    );
  } finally {
    if (owned) httpClient.close();
  }
}
