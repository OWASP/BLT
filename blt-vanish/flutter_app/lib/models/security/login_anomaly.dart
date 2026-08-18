import 'package:flutter/foundation.dart';

/// Contract representing a login anomaly (suspicious login detection).
class LoginAnomaly {
  final String accountId;
  final double score; // 0.0 to 1.0 representing confidence of anomaly
  final String riskBand; // 'low', 'medium', 'high', 'critical'
  final List<String> reasonCodes; // e.g., 'NEW_GEO', 'NEW_DEVICE', 'ODD_HOUR'
  final DateTime detectedAt;

  const LoginAnomaly({
    required this.accountId,
    required this.score,
    required this.riskBand,
    required this.reasonCodes,
    required this.detectedAt,
  });

  factory LoginAnomaly.fromJson(Map<String, dynamic> json) {
    return LoginAnomaly(
      accountId: json['accountId'] as String,
      score: (json['score'] as num).toDouble(),
      riskBand: json['riskBand'] as String,
      reasonCodes: List<String>.from(json['reasonCodes'] as List),
      detectedAt: DateTime.parse(json['detectedAt'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'accountId': accountId,
      'score': score,
      'riskBand': riskBand,
      'reasonCodes': reasonCodes,
      'detectedAt': detectedAt.toIso8601String(),
    };
  }
}
