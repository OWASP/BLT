import 'security_alert.dart';

/// Encrypted, hash-only credential snapshot used for local hygiene scoring.
class CredentialSnapshot {
  /// Creates a credential snapshot without storing the raw password.
  const CredentialSnapshot({
    required this.id,
    required this.accountLabel,
    required this.username,
    required this.passwordHash,
    required this.reuseHash,
    required this.strengthScore,
    required this.reuseLikelihoodScore,
    required this.exposureScore,
    required this.finalScore,
    required this.severity,
    required this.reasonCodes,
    required this.createdAt,
    required this.updatedAt,
    this.rotationGuidance,
  });

  /// Stable local identifier.
  final String id;

  /// Human-readable account or provider label.
  final String accountLabel;

  /// User-entered account identifier.
  final String username;

  /// SHA-256 hash of the exact password string.
  final String passwordHash;

  /// Stable hash used to compare reuse across snapshots.
  final String reuseHash;

  /// Normalized credential strength score in `[0, 1]`.
  final double strengthScore;

  /// Reuse likelihood score in `[0, 1]`.
  final double reuseLikelihoodScore;

  /// Exposure posture score in `[0, 1]`.
  final double exposureScore;

  /// Combined credential risk score in `[0, 1]`.
  final double finalScore;

  /// Deterministic severity mapped from the final score.
  final AlertSeverity severity;

  /// Explainability reason codes.
  final List<String> reasonCodes;

  /// Suggested next-step guidance.
  final String? rotationGuidance;

  /// Snapshot creation timestamp.
  final DateTime createdAt;

  /// Snapshot update timestamp.
  final DateTime updatedAt;

  /// Deserializes a credential snapshot.
  factory CredentialSnapshot.fromJson(Map<String, dynamic> json) {
    return CredentialSnapshot(
      id: json['id'] as String,
      accountLabel: json['accountLabel'] as String,
      username: json['username'] as String,
      passwordHash: json['passwordHash'] as String,
      reuseHash: json['reuseHash'] as String,
      strengthScore: (json['strengthScore'] as num).toDouble(),
      reuseLikelihoodScore: (json['reuseLikelihoodScore'] as num).toDouble(),
      exposureScore: (json['exposureScore'] as num).toDouble(),
      finalScore: (json['finalScore'] as num).toDouble(),
      severity: _severityFromWireValue(json['severity'] as String),
      reasonCodes: (json['reasonCodes'] as List<dynamic>)
          .map((code) => code as String)
          .toList(),
      rotationGuidance: json['rotationGuidance'] as String?,
      createdAt: DateTime.parse(json['createdAt'] as String),
      updatedAt: DateTime.parse(json['updatedAt'] as String),
    );
  }

  /// Serializes the snapshot for encrypted persistence.
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'accountLabel': accountLabel,
      'username': username,
      'passwordHash': passwordHash,
      'reuseHash': reuseHash,
      'strengthScore': strengthScore,
      'reuseLikelihoodScore': reuseLikelihoodScore,
      'exposureScore': exposureScore,
      'finalScore': finalScore,
      'severity': severity.name,
      'reasonCodes': reasonCodes,
      'rotationGuidance': rotationGuidance,
      'createdAt': createdAt.toIso8601String(),
      'updatedAt': updatedAt.toIso8601String(),
    };
  }

  /// Returns a copy with selected fields replaced.
  CredentialSnapshot copyWith({
    String? id,
    String? accountLabel,
    String? username,
    String? passwordHash,
    String? reuseHash,
    double? strengthScore,
    double? reuseLikelihoodScore,
    double? exposureScore,
    double? finalScore,
    AlertSeverity? severity,
    List<String>? reasonCodes,
    String? rotationGuidance,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return CredentialSnapshot(
      id: id ?? this.id,
      accountLabel: accountLabel ?? this.accountLabel,
      username: username ?? this.username,
      passwordHash: passwordHash ?? this.passwordHash,
      reuseHash: reuseHash ?? this.reuseHash,
      strengthScore: strengthScore ?? this.strengthScore,
      reuseLikelihoodScore:
          reuseLikelihoodScore ?? this.reuseLikelihoodScore,
      exposureScore: exposureScore ?? this.exposureScore,
      finalScore: finalScore ?? this.finalScore,
      severity: severity ?? this.severity,
      reasonCodes: reasonCodes ?? this.reasonCodes,
      rotationGuidance: rotationGuidance ?? this.rotationGuidance,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  static AlertSeverity _severityFromWireValue(String value) {
    return AlertSeverity.values.firstWhere(
      (severity) => severity.name == value,
      orElse: () => AlertSeverity.low,
    );
  }
}
