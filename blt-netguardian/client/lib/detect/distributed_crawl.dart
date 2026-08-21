/// Distributed crawl: pull → claim → scan → spider → submit → complete.
library;

import 'package:http/http.dart' as http;

import 'crawl.dart';
import 'domain_normalize.dart';
import '../queue/domain_api.dart';
import '../queue/domain_queue.dart';
import 'normalize.dart';

class DistributedProgress {
  const DistributedProgress({
    required this.message,
    this.jobs = const [],
    this.counts = const {},
  });

  final String message;
  final List<DomainJob> jobs;
  final Map<String, int> counts;
}

Future<void> runDistributedCrawl({
  required String seedUrl,
  required String baseUrl,
  required String senderId,
  required CrawlRun run,
  required LocalDomainQueue local,
  DomainApi? api,
  http.Client? httpClient,
  String? token,
  void Function(DistributedProgress progress)? onProgress,
  void Function(DetectionFinding finding)? onFinding,
  CrawlConfig scanConfig = const CrawlConfig(
    maxPages: 8,
    maxNewHosts: 40,
    maxPathsPerHost: 6,
    delay: Duration(milliseconds: 350),
    continuous: false,
  ),
}) async {
  final domainApi = api ?? DomainApi(httpClient: httpClient);
  final ownedHttp = httpClient == null && api == null;

  Future<void> sync() async {
    final listed = await domainApi.list(
      baseUrl: baseUrl,
      token: token,
      senderId: senderId,
    );
    final merged = await local.merge(listed.jobs);
    onProgress?.call(DistributedProgress(
      message:
          'Queue sync · pending ${listed.counts['pending'] ?? 0} · '
          'in_progress ${listed.counts['in_progress'] ?? 0} · '
          'scanned ${listed.counts['scanned'] ?? 0}',
      jobs: merged,
      counts: listed.counts,
    ));
  }

  try {
    final seed = normalizeDomain(seedUrl);
    if (seed != null) {
      await domainApi.submit(
        baseUrl: baseUrl,
        domains: [seed.seedUrl],
        senderId: senderId,
        token: token,
      );
    }
    await sync();

    while (!run.stopped) {
      await sync();
      if (run.stopped) break;

      final job = await domainApi.claim(
        baseUrl: baseUrl,
        senderId: senderId,
        token: token,
      );
      if (job == null) {
        onProgress?.call(const DistributedProgress(
          message: 'No pending domains — waiting for discoveries…',
        ));
        await Future<void>.delayed(const Duration(seconds: 3));
        continue;
      }

      await local.merge([job]);
      onProgress?.call(DistributedProgress(
        message: 'Claimed ${job.hostKey} — scanning…',
        jobs: await local.load(),
      ));

      try {
        final result = await crawlAndScan(
          job.seedUrl,
          config: scanConfig,
          client: httpClient,
          run: run,
          onFinding: onFinding,
        );
        if (run.stopped) {
          await domainApi.fail(
            baseUrl: baseUrl,
            jobId: job.id,
            senderId: senderId,
            error: 'stopped',
            token: token,
          );
          break;
        }
        final discovered = [
          for (final host in result.discoveredHosts)
            if (normalizeDomain(host) != null) normalizeDomain(host)!.seedUrl,
        ];
        if (discovered.isNotEmpty) {
          await domainApi.submit(
            baseUrl: baseUrl,
            domains: discovered,
            senderId: senderId,
            token: token,
            sourceUrl: job.seedUrl,
          );
        }
        await domainApi.complete(
          baseUrl: baseUrl,
          jobId: job.id,
          senderId: senderId,
          token: token,
          result: {
            'pages': result.pagesScanned,
            'findings': result.findings.length,
            'discovered_hosts': result.discoveredHosts,
            'visited': result.visitedUrls,
          },
        );
        onProgress?.call(DistributedProgress(
          message:
              'Scanned ${job.hostKey} · ${result.pagesScanned} pages · '
              '${result.discoveredHosts.length} new hosts',
          jobs: await local.load(),
        ));
      } catch (e) {
        await domainApi.fail(
          baseUrl: baseUrl,
          jobId: job.id,
          senderId: senderId,
          error: e.toString(),
          token: token,
        );
        onProgress?.call(DistributedProgress(
          message: 'Failed ${job.hostKey}: $e',
        ));
      }
    }
  } finally {
    if (ownedHttp) {
      // DomainApi owns its client.
    }
  }
}
