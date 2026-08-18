import 'package:flutter_test/flutter_test.dart';
import 'package:selferase/services/security_risk_service.dart';

class MockUrlExtractor implements IUrlSignalExtractor {
  @override
  Map<String, double> extract(Uri uri) => {'entropy': 0.8, 'suspicious_tokens': 1.0, 'risky_tld': 1.0};
}

class MockMessageExtractor implements IMessageSignalExtractor {
  @override
  Map<String, double> extract(String message) => {'urgency_token': 0.0};
}

class MockEnrichmentService implements IReputationEnrichmentService {
  @override
  Future<Map<String, String>> fetchReputation(
    String domain, {
    int timeoutMs = 1500,
  }) async {
    return {'reputation': 'clean', 'threat_score': '0.0'};
  }
}

void main() {
  test('SecurityRiskService should process injected extractors cleanly and output valid assessments', () async {
    final service = SecurityRiskService(
      urlExtractor: MockUrlExtractor(),
      messageExtractor: MockMessageExtractor(),
      enrichmentService: MockEnrichmentService(),
    );

    final assessment = await service.assessCandidate(targetAsset: 'https://verify-identity-gate.xyz');

    expect(assessment.finalScore, greaterThan(0.0));
    expect(assessment.finalScore, lessThanOrEqualTo(1.0));
    expect(assessment.alerts, isNotEmpty);
    expect(assessment.alerts.first.reasonCodes, contains('HIGH_ENTROPY_HOST'));
  });
}
