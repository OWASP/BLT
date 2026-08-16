import 'package:flutter/foundation.dart';

/// Contract for an exposure event (e.g., a data breach or dark web leak).
class ExposureEvent {
  final String source;
  final DateTime occurredAt;
  final String urgency; // 'low', 'medium', 'high', 'critical'
  final double confidence;
  final String accountHash; // HMAC-SHA256(emailLowercase, appSecret)

  const ExposureEvent({
    required this.source,
    required this.occurredAt,
    required this.urgency,
    required this.confidence,
    required this.accountHash,
  });

  /// Factory constructor to parse a normalized JSON payload.
  factory ExposureEvent.fromJson(Map<String, dynamic> json) {
    return ExposureEvent(
      source: json['source'] as String,
      occurredAt: DateTime.parse(json['occurredAt'] as String),
      urgency: json['urgency'] as String,
      confidence: (json['confidence'] as num).toDouble(),
      accountHash: json['accountHash'] as String,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'source': source,
      'occurredAt': occurredAt.toIso8601String(),
      'urgency': urgency,
      'confidence': confidence,
      'accountHash': accountHash,
    };
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ExposureEvent &&
          runtimeType == other.runtimeType &&
          source == other.source &&
          occurredAt == other.occurredAt &&
          urgency == other.urgency &&
          accountHash == other.accountHash;

  @override
  int get hashCode =>
      source.hashCode ^
      occurredAt.hashCode ^
      urgency.hashCode ^
      accountHash.hashCode;
}
