/// Stable fingerprints matching `src/detect/normalize.py`.
library;

import 'dart:convert';

import 'package:crypto/crypto.dart';

const severities = {'critical', 'high', 'medium', 'low', 'info'};

String normalizeSeverity(Object? value) {
  final text = (value ?? '').toString().trim().toLowerCase();
  return severities.contains(text) ? text : 'info';
}

String computeFingerprint({
  required String ruleId,
  required String target,
  String locator = '',
}) {
  final material =
      '${ruleId.trim()}\x00${target.trim()}\x00${locator.trim()}';
  final digest = sha256.convert(utf8.encode(material)).toString();
  return 'fp-${digest.substring(0, 32)}';
}

class DetectionFinding {
  DetectionFinding({
    required this.ruleId,
    required this.severity,
    required this.title,
    required this.target,
    this.locator = '',
    this.cveId,
    Map<String, Object?>? evidence,
    this.remediation = '',
  }) : evidence = evidence ?? {} {
    if (ruleId.isEmpty) throw ArgumentError('rule_id is required');
    if (title.isEmpty) throw ArgumentError('title is required');
  }

  final String ruleId;
  final String severity;
  final String title;
  final String target;
  final String locator;
  final String? cveId;
  final Map<String, Object?> evidence;
  final String remediation;

  String get fingerprint => computeFingerprint(
        ruleId: ruleId,
        target: target,
        locator: locator,
      );

  /// Rebuild from API / proxy payload (server scan).
  static DetectionFinding fromPayload(Map<String, Object?> payload) {
    final evidence = payload['evidence'];
    return DetectionFinding(
      ruleId: (payload['rule_id'] ?? '').toString(),
      severity: (payload['severity'] ?? 'info').toString(),
      title: (payload['title'] ?? '').toString(),
      target: (payload['target'] ?? '').toString(),
      locator: (payload['locator'] ?? '').toString(),
      cveId: payload['cve_id']?.toString(),
      evidence: evidence is Map
          ? evidence.map((k, v) => MapEntry(k.toString(), v as Object?))
          : null,
      remediation: (payload['remediation'] ?? '').toString(),
    );
  }

  Map<String, Object?> toPayload() {
    final payload = <String, Object?>{
      'rule_id': ruleId,
      'severity': normalizeSeverity(severity),
      'title': title,
      'fingerprint': fingerprint,
    };
    if (target.isNotEmpty) payload['target'] = target;
    if (cveId != null && cveId!.isNotEmpty) payload['cve_id'] = cveId;
    if (locator.isNotEmpty) payload['locator'] = locator;
    if (remediation.isNotEmpty) payload['remediation'] = remediation;
    if (evidence.isNotEmpty) payload['evidence'] = evidence;
    return payload;
  }
}
