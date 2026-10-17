import 'package:uuid/uuid.dart';
import '../models/security/remediation_action.dart';
import '../models/security/risk_assessment.dart';
import '../models/security/security_alert.dart';
import 'risk_classifier.dart';

/// Builds a deterministic risk assessment from local and edge signals.
class RiskAssessmentBuilder {
  /// Creates a builder with an optional calibrated classifier override.
  RiskAssessmentBuilder({
    RiskClassifier classifier = const RiskClassifier(),
  }) : _classifier = classifier;

  final Uuid _uuid = const Uuid();
  final RiskClassifier _classifier;

  /// Produces a `RiskAssessment` for the provided URL and signal maps.
  RiskAssessment buildAssessment({
    required String url,
    required Map<String, double> localSignals,
    required Map<String, String> enrichmentSignals,
  }) {
    final classification = _classifier.classifyPhishing(
      localSignals: localSignals,
      enrichmentSignals: enrichmentSignals,
    );
    final enrichedSignals = <String, String>{
      ...enrichmentSignals,
      'confidence_band': classification.isOfflineFallback ? 'degraded' : 'standard',
    };

    return RiskAssessment(
      id: _uuid.v4(),
      targetAsset: url,
      severity: classification.severity,
      finalScore: classification.score,
      localSignals: localSignals,
      enrichmentSignals: enrichedSignals,
      assessedAt: DateTime.now(),
      alerts: [
        SecurityAlert(
          id: _uuid.v4(),
          type: AlertType.phishing,
          severity: classification.severity,
          confidence: classification.confidence,
          reasonCodes: classification.reasonCodes,
          createdAt: DateTime.now(),
        )
      ],
      recommendedActions: _generateRecommendedActions(
        severity: classification.severity,
        reasonCodes: classification.reasonCodes,
      ),
    );
  }

  List<RemediationAction> _generateRecommendedActions({
    required AlertSeverity severity,
    required List<String> reasonCodes,
  }) {
    if (severity == AlertSeverity.low) {
      return const [];
    }

    final actions = <RemediationAction>[
      RemediationAction(
        id: _uuid.v4(),
        title: 'Pause and verify the destination',
        description:
            'Open the target in a trusted browser only after confirming the domain spelling and ownership.',
        urgency: severity,
      ),
    ];

    if (reasonCodes.contains('EDGE_REPUTATION_MATCH') ||
        reasonCodes.contains('RISKY_TLD_EXTENSION')) {
      actions.add(
        RemediationAction(
          id: _uuid.v4(),
          title: 'Do not submit credentials',
          description:
              'Avoid entering passwords, OTP codes, or recovery details on this destination until it is independently verified.',
          urgency: severity,
        ),
      );
    }

    return actions;
  }
}
