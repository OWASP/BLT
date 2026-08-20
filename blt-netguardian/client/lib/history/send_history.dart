/// Local history of successfully sent findings.
library;

import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

class HistoryItem {
  HistoryItem({
    required this.id,
    required this.sentAtMs,
    required this.ruleId,
    required this.target,
    required this.severity,
    this.findingId,
    this.fingerprint,
    this.redacted = false,
  });

  final String id;
  final int sentAtMs;
  final String ruleId;
  final String target;
  final String severity;
  final String? findingId;
  final String? fingerprint;
  final bool redacted;

  Map<String, Object?> toJson() => {
        'id': id,
        'sent_at_ms': sentAtMs,
        'rule_id': ruleId,
        'target': target,
        'severity': severity,
        'finding_id': findingId,
        'fingerprint': fingerprint,
        'redacted': redacted,
      };

  static HistoryItem fromJson(Map<String, Object?> json) {
    return HistoryItem(
      id: json['id'] as String,
      sentAtMs: json['sent_at_ms'] as int,
      ruleId: (json['rule_id'] ?? '').toString(),
      target: (json['target'] ?? '').toString(),
      severity: (json['severity'] ?? '').toString(),
      findingId: json['finding_id'] as String?,
      fingerprint: json['fingerprint'] as String?,
      redacted: json['redacted'] == true,
    );
  }
}

class SendHistoryStore {
  static const _key = 'ng_send_history_v1';
  static const _maxItems = 100;

  Future<List<HistoryItem>> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null || raw.isEmpty) return [];
    final decoded = jsonDecode(raw);
    if (decoded is! List) return [];
    return decoded
        .whereType<Map>()
        .map((m) => HistoryItem.fromJson(
              m.map((k, v) => MapEntry(k.toString(), v as Object?)),
            ))
        .toList();
  }

  Future<void> save(List<HistoryItem> items) async {
    final prefs = await SharedPreferences.getInstance();
    final trimmed = items.take(_maxItems).toList();
    await prefs.setString(
      _key,
      jsonEncode(trimmed.map((i) => i.toJson()).toList()),
    );
  }

  Future<void> record({
    required Map<String, Object?> payload,
    String? findingId,
    required bool redacted,
  }) async {
    final items = await load();
    final now = DateTime.now().toUtc().millisecondsSinceEpoch;
    items.insert(
      0,
      HistoryItem(
        id: 'hist-$now-${items.length}',
        sentAtMs: now,
        ruleId: (payload['rule_id'] ?? '').toString(),
        target: (payload['target'] ?? '').toString(),
        severity: (payload['severity'] ?? '').toString(),
        findingId: findingId,
        fingerprint: payload['fingerprint']?.toString(),
        redacted: redacted,
      ),
    );
    await save(items);
  }

  Future<void> clear() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_key);
  }
}
