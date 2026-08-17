import 'package:flutter_test/flutter_test.dart';
import '../lib/services/login_anomaly_service.dart';
import '../lib/services/risk_correlation_service.dart';
import '../lib/services/recommendation_playbook_service.dart';

void main() {
  group('Login Anomaly & Correlation Tests', () {
    late LoginAnomalyService anomalyService;
    late RiskCorrelationService correlationService;
    late RecommendationPlaybookService playbookService;

    setUp(() {
      anomalyService = LoginAnomalyService();
      correlationService = RiskCorrelationService(anomalyService);
      playbookService = RecommendationPlaybookService();
    });

    test('Isolated anomaly (new device only) should be low risk', () {
      final anomaly = correlationService.correlateLogin(
        accountId: 'test_user',
        newGeo: false,
        newDevice: true,
        oddHour: false,
        hasRecentPhishingAlert: false,
        hasWeakCredential: false,
      );

      expect(anomaly.score, closeTo(0.30, 0.01));
      expect(anomaly.riskBand, 'low');
    });

    test('Correlated anomaly (new device + prior phishing) escalates risk', () {
      final anomaly = correlationService.correlateLogin(
        accountId: 'test_user',
        newGeo: false,
        newDevice: true,
        oddHour: false,
        hasRecentPhishingAlert: true,
        hasWeakCredential: false,
      );

      // Score: 0.30 (device) + 0.20 (correlation) = 0.50 -> medium
      expect(anomaly.score, closeTo(0.50, 0.01));
      expect(anomaly.riskBand, 'medium');
    });

    test('Critical anomaly (new geo, new device, odd hour, correlation)', () {
      final anomaly = correlationService.correlateLogin(
        accountId: 'test_user',
        newGeo: true, // 0.35
        newDevice: true, // 0.30
        oddHour: true, // 0.15
        hasRecentPhishingAlert: true, // 0.20
        hasWeakCredential: false,
      );

      // Total = 1.0 -> critical
      expect(anomaly.score, closeTo(1.0, 0.01));
      expect(anomaly.riskBand, 'critical');
    });

    test('Correlated anomaly (new device + weak credential) escalates risk', () {
      final anomaly = correlationService.correlateLogin(
        accountId: 'test_user',
        newGeo: false,
        newDevice: true,
        oddHour: false,
        hasRecentPhishingAlert: false,
        hasWeakCredential: true,
      );

      // Score: 0.30 (device) + 0.20 (weak credential) = 0.50 -> medium
      expect(anomaly.score, closeTo(0.50, 0.01));
      expect(anomaly.riskBand, 'medium');
      expect(anomaly.reasonCodes, contains('WEAK_CREDENTIAL'));
    });

    test('Combined context (weak credential + prior phishing) adds up correctly', () {
      final anomaly = correlationService.correlateLogin(
        accountId: 'test_user',
        newGeo: false,
        newDevice: true,
        oddHour: false,
        hasRecentPhishingAlert: true,
        hasWeakCredential: true,
      );

      // Score: 0.30 (device) + 0.20 (phishing) + 0.20 (weak credential) = 0.70 -> high
      expect(anomaly.score, closeTo(0.70, 0.01));
      expect(anomaly.riskBand, 'high');
      expect(anomaly.reasonCodes, containsAll(['PRIOR_PHISHING_ALERT', 'WEAK_CREDENTIAL']));
    });

    test('Playbook matches critical severity with session revoke', () {
      final anomaly = correlationService.correlateLogin(
        accountId: 'test_user',
        newGeo: true,
        newDevice: true,
        oddHour: true,
        hasRecentPhishingAlert: true, // 0.20 extra ensures > 0.80
        hasWeakCredential: false,
      );

      final playbook = playbookService.generatePlaybook(anomaly);
      
      expect(playbook.severityTrigger, 'critical');
      // Should have session revoke and MFA
      expect(playbook.steps.any((s) => s.actionType == 'revoke_session'), isTrue);
      expect(playbook.steps.any((s) => s.actionType == 'enable_mfa'), isTrue);
    });
  });
}
