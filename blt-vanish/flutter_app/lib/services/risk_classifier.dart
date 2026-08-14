import '../models/security/security_alert.dart';

/// Immutable classifier thresholds for calibrated phishing risk scoring.
class RiskClassifierConfig {
  /// Creates a calibrated configuration.
  const RiskClassifierConfig({
    this.normalizedEntropyThreshold = 0.76,
    this.confidenceFloor = 0.50,
    this.mediumThreshold = 0.40,
    this.highThreshold = 0.65,
    this.criticalThreshold = 0.85,
    this.urlWeight = 0.4,
    this.messageWeight = 0.3,
    this.reputationWeight = 0.3,
  });

  /// Shannon entropy threshold after the extractor's `entropy / 5.0` normalization.
  final double normalizedEntropyThreshold;

  /// Minimum confidence allowed for a non-empty classification result.
  final double confidenceFloor;

  /// Minimum score for a medium-severity result.
  final double mediumThreshold;

  /// Minimum score for a high-severity result.
  final double highThreshold;

  /// Minimum score for a critical-severity result.
  final double criticalThreshold;

  /// Weight applied to aggregated URL lexical features.
  final double urlWeight;

  /// Weight applied to message-derived urgency features.
  final double messageWeight;

  /// Weight applied to edge reputation enrichment.
  final double reputationWeight;
}

/// Classification output for a phishing-risk evaluation.
class RiskClassification {
  /// Creates an immutable phishing classification.
  const RiskClassification({
    required this.score,
    required this.severity,
    required this.confidence,
    required this.reasonCodes,
    required this.topWeightedFactors,
    required this.guardrails,
    required this.isOfflineFallback,
  });

  /// Final normalized score in `[0, 1]`.
  final double score;

  /// Deterministic severity mapped from score and guardrails.
  final AlertSeverity severity;

  /// Explainability confidence in `[0, 1]`.
  final double confidence;

  /// Explainability reason codes emitted for the result.
  final List<String> reasonCodes;

  /// Top weighted factors that contributed to the result.
  final List<String> topWeightedFactors;

  /// Human-readable guardrails applied during classification.
  final List<String> guardrails;

  /// Whether edge enrichment was unavailable and the result is local-only.
  final bool isOfflineFallback;
}

/// Calibrated phishing classifier with false-positive guardrails.
class RiskClassifier {
  /// Creates a calibrated classifier.
  const RiskClassifier({
    this.config = const RiskClassifierConfig(),
  });

  /// Current calibrated thresholds and weights.
  final RiskClassifierConfig config;

  /// Classifies phishing risk using local and edge signals.
  RiskClassification classifyPhishing({
    required Map<String, double> localSignals,
    required Map<String, String> enrichmentSignals,
  }) {
    final entropy = localSignals['entropy'] ?? 0.0;
    final suspiciousTokens = localSignals['suspicious_tokens'] ?? 0.0;
    final riskyTld = localSignals['risky_tld'] ?? 0.0;
    final queryAnomaly = localSignals['query_anomaly'] ?? 0.0;
    final urgencyToken = localSignals['urgency_token'] ?? 0.0;

    final urlScore = (entropy * 0.4) + (suspiciousTokens * 0.3) + (riskyTld * 0.3);
    final messageScore = urgencyToken;
    final reputationScore =
        double.tryParse(enrichmentSignals['threat_score'] ?? '0.0') ?? 0.0;
    final reputation = enrichmentSignals['reputation'] ?? 'unknown';
    final isOfflineFallback = reputation == 'unknown';

    final score = ((config.urlWeight * urlScore) +
            (config.messageWeight * messageScore) +
            (config.reputationWeight * reputationScore))
        .clamp(0.0, 1.0);

    final reasonCodes = <String>[];
    if (entropy >= config.normalizedEntropyThreshold) {
      reasonCodes.add('HIGH_ENTROPY_HOST');
    }
    if (suspiciousTokens > 0.0) {
      reasonCodes.add('SUSPICIOUS_KEYWORDS');
    }
    if (riskyTld > 0.0) {
      reasonCodes.add('RISKY_TLD_EXTENSION');
    }
    if (reputation == 'malicious') {
      reasonCodes.add('EDGE_REPUTATION_MATCH');
    }

    var severity = _mapScoreToSeverity(score);
    final guardrails = <String>[];

    final strongSignalCount = <bool>[
      entropy >= config.normalizedEntropyThreshold,
      suspiciousTokens >= 0.7,
      riskyTld >= 1.0,
      messageScore >= 0.6,
      reputationScore >= 0.7 || reputation == 'malicious',
    ].where((signal) => signal).length;

    if (severity == AlertSeverity.critical && strongSignalCount < 2) {
      severity = AlertSeverity.high;
      guardrails.add('critical_requires_dual_signal');
    }

    if (severity.index >= AlertSeverity.high.index &&
        reputation != 'malicious' &&
        riskyTld == 0.0 &&
        entropy < config.normalizedEntropyThreshold &&
        queryAnomaly >= 0.5 &&
        strongSignalCount < 2) {
      severity = AlertSeverity.medium;
      guardrails.add('benign_marketing_cap');
    }

    final factorEntries = <MapEntry<String, double>>[
      MapEntry('url_score', config.urlWeight * urlScore),
      MapEntry('message_score', config.messageWeight * messageScore),
      MapEntry('reputation_score', config.reputationWeight * reputationScore),
      MapEntry('query_anomaly', queryAnomaly * 0.1),
    ]
      ..sort((left, right) => right.value.compareTo(left.value));

    final confidence = _computeConfidence(
      score: score,
      strongSignalCount: strongSignalCount,
      isOfflineFallback: isOfflineFallback,
    );

    return RiskClassification(
      score: score,
      severity: severity,
      confidence: confidence,
      reasonCodes: reasonCodes,
      topWeightedFactors: factorEntries
          .where((entry) => entry.value > 0.0)
          .take(3)
          .map((entry) => entry.key)
          .toList(),
      guardrails: guardrails,
      isOfflineFallback: isOfflineFallback,
    );
  }

  AlertSeverity _mapScoreToSeverity(double score) {
    if (score >= config.criticalThreshold) {
      return AlertSeverity.critical;
    }
    if (score >= config.highThreshold) {
      return AlertSeverity.high;
    }
    if (score >= config.mediumThreshold) {
      return AlertSeverity.medium;
    }
    return AlertSeverity.low;
  }

  double _computeConfidence({
    required double score,
    required int strongSignalCount,
    required bool isOfflineFallback,
  }) {
    var confidence =
        (config.confidenceFloor + (score * 0.35) + (strongSignalCount * 0.08))
            .clamp(config.confidenceFloor, 0.98);

    if (isOfflineFallback) {
      confidence = (confidence - 0.12).clamp(config.confidenceFloor, 0.79);
    }

    return confidence;
  }
}
