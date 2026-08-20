/// Persistent offline outbox for signed ingest attempts.
library;

import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

enum OutboxStatus { pending, sent, failed }

class OutboxItem {
  OutboxItem({
    required this.id,
    required this.payload,
    required this.createdAtMs,
    this.status = OutboxStatus.pending,
    this.lastError,
    this.attempts = 0,
    this.findingId,
  });

  final String id;
  final Map<String, Object?> payload;
  final int createdAtMs;
  OutboxStatus status;
  String? lastError;
  int attempts;
  String? findingId;

  Map<String, Object?> toJson() => {
        'id': id,
        'payload': payload,
        'created_at_ms': createdAtMs,
        'status': status.name,
        'last_error': lastError,
        'attempts': attempts,
        'finding_id': findingId,
      };

  static OutboxItem fromJson(Map<String, Object?> json) {
    return OutboxItem(
      id: json['id'] as String,
      payload: Map<String, Object?>.from(json['payload'] as Map),
      createdAtMs: json['created_at_ms'] as int,
      status: OutboxStatus.values.firstWhere(
        (s) => s.name == json['status'],
        orElse: () => OutboxStatus.pending,
      ),
      lastError: json['last_error'] as String?,
      attempts: (json['attempts'] as int?) ?? 0,
      findingId: json['finding_id'] as String?,
    );
  }
}

class OutboxStore {
  static const _key = 'ng_outbox_v1';

  Future<List<OutboxItem>> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null || raw.isEmpty) return [];
    final decoded = jsonDecode(raw);
    if (decoded is! List) return [];
    return decoded
        .whereType<Map>()
        .map((m) => OutboxItem.fromJson(m.map((k, v) => MapEntry(k.toString(), v as Object?))))
        .toList();
  }

  Future<void> save(List<OutboxItem> items) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      _key,
      jsonEncode(items.map((i) => i.toJson()).toList()),
    );
  }

  Future<void> enqueue(List<Map<String, Object?>> payloads) async {
    final items = await load();
    final now = DateTime.now().toUtc().millisecondsSinceEpoch;
    for (var i = 0; i < payloads.length; i++) {
      items.add(OutboxItem(
        id: 'ob-$now-$i',
        payload: payloads[i],
        createdAtMs: now,
      ));
    }
    await save(items);
  }
}
