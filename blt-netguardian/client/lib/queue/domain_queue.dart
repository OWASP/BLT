/// Local cache of shared domain-queue jobs.
library;

import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

class DomainJob {
  DomainJob({
    required this.id,
    required this.orgId,
    required this.hostKey,
    required this.seedUrl,
    required this.status,
    this.discoveredAt,
    this.lastScanAt,
    this.claimedBy,
    this.retryCount = 0,
    this.lastError,
    this.sourceUrl,
    this.result,
  });

  final String id;
  final String orgId;
  final String hostKey;
  final String seedUrl;
  String status;
  final int? discoveredAt;
  int? lastScanAt;
  String? claimedBy;
  int retryCount;
  String? lastError;
  String? sourceUrl;
  Map<String, Object?>? result;

  Map<String, Object?> toJson() => {
        'id': id,
        'org_id': orgId,
        'host_key': hostKey,
        'seed_url': seedUrl,
        'status': status,
        'discovered_at': discoveredAt,
        'last_scan_at': lastScanAt,
        'claimed_by': claimedBy,
        'retry_count': retryCount,
        'last_error': lastError,
        'source_url': sourceUrl,
        'result': result,
      };

  static DomainJob fromJson(Map<String, Object?> json) {
    final result = json['result'];
    return DomainJob(
      id: (json['id'] ?? '').toString(),
      orgId: (json['org_id'] ?? '').toString(),
      hostKey: (json['host_key'] ?? '').toString(),
      seedUrl: (json['seed_url'] ?? '').toString(),
      status: (json['status'] ?? 'pending').toString(),
      discoveredAt: json['discovered_at'] is int ? json['discovered_at'] as int : null,
      lastScanAt: json['last_scan_at'] is int ? json['last_scan_at'] as int : null,
      claimedBy: json['claimed_by']?.toString(),
      retryCount: (json['retry_count'] as int?) ?? 0,
      lastError: json['last_error']?.toString(),
      sourceUrl: json['source_url']?.toString(),
      result: result is Map
          ? result.map((k, v) => MapEntry(k.toString(), v as Object?))
          : null,
    );
  }
}

class LocalDomainQueue {
  static const _key = 'ng_domain_queue_v1';

  Future<List<DomainJob>> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null || raw.isEmpty) return [];
    final decoded = jsonDecode(raw);
    if (decoded is! List) return [];
    return decoded
        .whereType<Map>()
        .map((m) => DomainJob.fromJson(
              m.map((k, v) => MapEntry(k.toString(), v as Object?)),
            ))
        .toList();
  }

  Future<void> save(List<DomainJob> jobs) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, jsonEncode(jobs.map((j) => j.toJson()).toList()));
  }

  Future<List<DomainJob>> merge(List<DomainJob> incoming) async {
    final current = await load();
    final byKey = {for (final j in current) j.hostKey: j};
    for (final job in incoming) {
      byKey[job.hostKey] = job;
    }
    final merged = byKey.values.toList()
      ..sort((a, b) => (b.discoveredAt ?? 0).compareTo(a.discoveredAt ?? 0));
    await save(merged);
    return merged;
  }
}
