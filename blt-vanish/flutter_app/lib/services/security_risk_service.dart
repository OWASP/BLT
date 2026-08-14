import 'package:uuid/uuid.dart';

import '../models/security/remediation_action.dart';
import '../models/security/risk_assessment.dart';
import '../models/security/security_alert.dart';
import 'risk_classifier.dart';

/// Abstract contract for local lexical domain feature extraction
abstract class IUrlSignalExtractor {
  /// Extracts normalized URL lexical features from a parsed URI.
  Map<String, double> extract(Uri uri);
}

/// Abstract contract for local behavioral message feature extraction
abstract class IMessageSignalExtractor {
  /// Extracts normalized message-level social engineering features.
  Map<String, double> extract(String message);
}

/// Abstract contract for secure network threat intelligence enrichment
abstract class IReputationEnrichmentService {
  /// Fetches non-sensitive reputation signals for a domain.
  Future<Map<String, String>> fetchReputation(String domain, {int timeoutMs});
}

/// Core coordination engine executing the deterministic risk composition model
class SecurityRiskService {
  final IUrlSignalExtractor _urlExtractor;
  final IMessageSignalExtractor _messageExtractor;
  final IReputationEnrichmentService _enrichmentService;
  final RiskClassifier _classifier;
  final Uuid _uuid = const Uuid();

  /// Creates the security risk aggregation service.
  SecurityRiskService({
    required IUrlSignalExtractor urlExtractor,
    required IMessageSignalExtractor messageExtractor,
    required IReputationEnrichmentService enrichmentService,
    RiskClassifier classifier = const RiskClassifier(),
  })  : _urlExtractor = urlExtractor,
        _messageExtractor = messageExtractor,
        _enrichmentService = enrichmentService,
        _classifier = classifier;

  /// Aggregates local feature extractions and edge signals to build an explainable assessment
  Future<RiskAssessment> assessCandidate({
    required String targetAsset,
    String? contextualMessage,
  }) async {
    final uri = Uri.tryParse(targetAsset) ?? Uri();
    
    // 1. Local Volatile Extraction (Sensitive PII data never leaves the runtime environment)
    final localUrlSignals = _urlExtractor.extract(uri);
    final localMessageSignals = _messageExtractor.extract(contextualMessage ?? '');

    // 2. Non-Sensitive Edge Enrichment Fetching (Bounded to a safe 1500ms fallback cutoff)
    final Map<String, String> edgeEnrichment;
    if (uri.hasAuthority) {
      edgeEnrichment = await _enrichmentService.fetchReputation(uri.host, timeoutMs: 1500);
    } else {
      edgeEnrichment = {'reputation': 'unknown', 'threat_score': '0.0'};
    }

    // 3. Mathematical Score Composition: Risk = w1*U + w2*M + w3*R
    // Merge localized signals safely into telemetry data arrays
    final combinedLocalSignals = <String, double>{}
      ..addAll(localUrlSignals)
      ..addAll(localMessageSignals);
    final classification = _classifier.classifyPhishing(
      localSignals: combinedLocalSignals,
      enrichmentSignals: edgeEnrichment,
    );
    final enrichedSignals = <String, String>{
      ...edgeEnrichment,
      'confidence_band': classification.isOfflineFallback ? 'degraded' : 'standard',
    };

    return RiskAssessment(
      id: _uuid.v4(),
      targetAsset: targetAsset,
      severity: classification.severity,
      finalScore: classification.score,
      localSignals: combinedLocalSignals,
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
      recommendedActions: _generateFallbackActions(classification.severity),
    );
  }

  List<RemediationAction> _generateFallbackActions(AlertSeverity severity) {
    if (severity == AlertSeverity.low) return [];
    
    return [
      RemediationAction(
        id: _uuid.v4(),
        title: 'Block Navigation Target',
        description: 'Do not submit active credentials, cryptographic materials, or session payloads to this domain.',
        urgency: severity,
      )
    ];
  }
}
