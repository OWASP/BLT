/// Distributed crawl: pull → claim → scan → spider → submit → complete.
library;

import 'dart:async';

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
    this.currentHost = '',
    this.hostsFound = 0,
    this.pagesScanned = 0,
    this.findings = 0,
  });

  final String message;
  final List<DomainJob> jobs;
  final Map<String, int> counts;
  final String currentHost;
  final int hostsFound;
  final int pagesScanned;
  final int findings;
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
    delay: Duration(milliseconds: 280),
    continuous: false,
  ),
}) async {
  final domainApi = api ?? DomainApi(httpClient: httpClient);
  var pagesTotal = 0;
  var findingsTotal = 0;
  var hostsTotal = 0;
  DateTime lastBeat = DateTime.fromMillisecondsSinceEpoch(0);
  String? fatal;

  void push(
    String message, {
    String currentHost = '',
    List<DomainJob> jobs = const [],
    Map<String, int> counts = const {},
  }) {
    onProgress?.call(DistributedProgress(
      message: message,
      jobs: jobs,
      counts: counts,
      currentHost: currentHost,
      hostsFound: hostsTotal,
      pagesScanned: pagesTotal,
      findings: findingsTotal,
    ));
  }

  Future<({List<DomainJob> jobs, Map<String, int> counts})> sync() async {
    final listed = await domainApi.list(
      baseUrl: baseUrl,
      token: token,
      senderId: senderId,
    );
    final merged = await local.merge(listed.jobs);
    return (jobs: merged, counts: listed.counts);
  }

  Future<void> emit(
    String message, {
    String currentHost = '',
  }) async {
    try {
      final snap = await sync();
      push(message, currentHost: currentHost, jobs: snap.jobs, counts: snap.counts);
    } catch (_) {
      push(message, currentHost: currentHost);
    }
  }

  try {
    // Fail fast with a clear message if this API build has no domain queue.
    try {
      await sync();
    } catch (e) {
      throw Exception(
        'Domain queue API missing on $baseUrl — use http://127.0.0.1:8787 '
        '(local serve.py on latest main). Detail: $e',
      );
    }

    final seed = normalizeDomain(seedUrl);
    if (seed == null) {
      throw Exception('Invalid seed URL: $seedUrl');
    }
    final created = await domainApi.submit(
      baseUrl: baseUrl,
      domains: [seed.seedUrl],
      senderId: senderId,
      token: token,
    );
    await emit(
      created.isEmpty
          ? 'SEED ${seed.hostKey} already on the grid'
          : 'SEED ${seed.hostKey} → shared queue',
      currentHost: seed.hostKey,
    );

    while (!run.stopped) {
      final job = await domainApi.claim(
        baseUrl: baseUrl,
        senderId: senderId,
        token: token,
      );
      if (job == null) {
        await emit('GRID LIVE — waiting for the next pending domain');
        await Future<void>.delayed(const Duration(seconds: 2));
        continue;
      }

      await emit('CLAIM ${job.hostKey}  lease $senderId', currentHost: job.hostKey);

      try {
        final result = await crawlAndScan(
          job.seedUrl,
          config: scanConfig,
          client: httpClient,
          run: run,
          onFinding: onFinding,
          onProgress: (p) {
            final now = DateTime.now();
            if (now.difference(lastBeat) > const Duration(seconds: 20)) {
              lastBeat = now;
              unawaited(domainApi
                  .heartbeat(
                    baseUrl: baseUrl,
                    jobId: job.id,
                    senderId: senderId,
                    token: token,
                  )
                  .catchError((_) {}));
            }
            push(
              'SCAN ${job.hostKey}  p${p.scanned}  q${p.queued}',
              currentHost: job.hostKey,
            );
          },
        );
        if (run.stopped) {
          await domainApi.fail(
            baseUrl: baseUrl,
            jobId: job.id,
            senderId: senderId,
            error: 'stopped',
            token: token,
          );
          await emit('STOP released ${job.hostKey} → retry_required');
          break;
        }
        pagesTotal += result.pagesScanned;
        findingsTotal += result.findings.length;
        hostsTotal += result.discoveredHosts.length;
        final discovered = <String>[];
        for (final host in result.discoveredHosts) {
          final n = normalizeDomain(host);
          if (n != null) discovered.add(n.seedUrl);
        }
        if (discovered.isNotEmpty) {
          await domainApi.submit(
            baseUrl: baseUrl,
            domains: discovered,
            senderId: senderId,
            token: token,
            sourceUrl: job.seedUrl,
          );
          await emit(
            'SPIDER ${job.hostKey}  +${discovered.length} hosts → grid',
            currentHost: job.hostKey,
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
        await emit(
          'DONE ${job.hostKey}  ${result.pagesScanned}p  '
          '${result.findings.length}f  +${result.discoveredHosts.length} hosts',
          currentHost: job.hostKey,
        );
      } catch (e) {
        await domainApi.fail(
          baseUrl: baseUrl,
          jobId: job.id,
          senderId: senderId,
          error: e.toString(),
          token: token,
        );
        await emit('FAIL ${job.hostKey} → retry  $e', currentHost: job.hostKey);
      }
    }
  } catch (e) {
    fatal = e.toString();
    push('GRID error — $fatal');
    rethrow;
  } finally {
    if (fatal == null) {
      push(run.stopped ? 'GRID stopped' : 'GRID idle');
    }
  }
}
