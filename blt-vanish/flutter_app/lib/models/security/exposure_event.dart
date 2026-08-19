import 'package:flutter/foundation.dart';

/// Contract for an exposure event (e.g., a data breach or dark web leak).
class ExposureEvent {
  final String? id;
  final String source;
  final DateTime occurredAt;
  final String urgency; // 'low', 'medium', 'high', 'critical'
  final double confidence;
  final String accountHash; // HMAC-SHA256(emailLowercase, appSecret)

  const ExposureEvent({
    this.id,
    required this.source,
    required this.occurredAt,
    required this.urgency,
    this.confidence = 1.0,
    this.accountHash = '',
  });

  /// Factory constructor to parse a normalized JSON payload.
  factory ExposureEvent.fromJson(Map<String, dynamic> json) {
    return ExposureEvent(
      id: json['id'] as String?,
      source: json['source'] as String,
      occurredAt: DateTime.parse(json['occurredAt'] as String),
      urgency: json['urgency'] as String,
      confidence: json['confidence'] != null
          ? (json['confidence'] as num).toDouble()
          : 1.0,
      accountHash: (json['accountHash'] as String?) ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      if (id != null) 'id': id,
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
          id == other.id &&
          source == other.source &&
          occurredAt == other.occurredAt &&
          urgency == other.urgency &&
          accountHash == other.accountHash;

  @override
  int get hashCode =>
      (id?.hashCode ?? 0) ^
      source.hashCode ^
      occurredAt.hashCode ^
      urgency.hashCode ^
      accountHash.hashCode;
}
