import 'package:flutter_test/flutter_test.dart';
import 'package:vanish/models/security/credential_snapshot.dart';
import 'package:vanish/models/security/exposure_event.dart';
import 'package:vanish/models/security/login_anomaly.dart';
import 'package:vanish/models/security/remediation_task.dart';
import 'package:vanish/models/security/risk_assessment.dart';
import 'package:vanish/models/security/security_alert.dart';
import 'package:vanish/services/unified_triage_service.dart';

void main() {
  test('UnifiedTriageService ranks mixed findings by priority', () {
    final service = UnifiedTriageService();
    final now = DateTime(2026, 7, 6);

    final items = service.buildTimeline(
      assessments: [
        RiskAssessment(
          id: 'scan-low',
          targetAsset: 'https://example.com',
          severity: AlertSeverity.low,
          finalScore: 0.1,
          localSignals: const <String, double>{},
          enrichmentSignals: const <String, String>{},
          assessedAt: now,
          alerts: const <SecurityAlert>[],
          recommendedActions: const [],
        ),
      ],
      credentialSnapshots: [
        CredentialSnapshot(
          id: 'cred-critical',
          accountLabel: 'Bank',
          username: 'user@example.com',
          passwordHash: 'hash',
          reuseHash: 'reuse',
          strengthScore: 0.1,
          reuseLikelihoodScore: 1.0,
          exposureScore: 1.0,
          finalScore: 0.95,
          severity: AlertSeverity.critical,
          reasonCodes: const <String>['KNOWN_DATA_BREACH'],
          createdAt: now,
          updatedAt: now,
        ),
      ],
      remediationTasks: [
        RemediationTask(
          id: 'task-high',
          type: RemediationTaskType.phishing,
          status: RemediationTaskStatus.queued,
          title: 'Block URL',
          description: 'Block suspicious URL',
          target: 'https://bad.test',
          severity: AlertSeverity.high,
          priorityScore: 0.82,
          reasonCodes: const <String>['SUSPICIOUS_KEYWORDS'],
          createdAt: now,
          updatedAt: now,
        ),
      ],
      exposureEvents: [
        ExposureEvent(
          source: 'HaveIBeenPwned DarkWeb',
          occurredAt: now,
          urgency: 'critical',
          confidence: 0.99,
          accountHash: 'anon_hash_123',
        ),
      ],
      loginAnomalies: [
        LoginAnomaly(
          accountId: 'github_user',
          score: 0.88,
          riskBand: 'high',
          reasonCodes: const ['NEW_DEVICE', 'ODD_HOUR'],
          detectedAt: now,
        ),
      ],
    );

    expect(items.first.id, contains('HaveIBeenPwned'));
    expect(items.any((i) => i.type == UnifiedTriageItemType.exposure), isTrue);
    expect(items.any((i) => i.type == UnifiedTriageItemType.anomaly), isTrue);
    expect(items.last.id, 'scan-low');
  });

  test('UnifiedTriageService filters open remediation items', () {
    final service = UnifiedTriageService();
    final now = DateTime(2026, 7, 6);

    final items = service.buildTimeline(
      assessments: const <RiskAssessment>[],
      credentialSnapshots: const <CredentialSnapshot>[],
      remediationTasks: [
        RemediationTask(
          id: 'open-task',
          type: RemediationTaskType.credential,
          status: RemediationTaskStatus.queued,
          title: 'Rotate credential',
          description: 'Rotate reused credential',
          target: 'GitHub',
          severity: AlertSeverity.high,
          priorityScore: 0.82,
          reasonCodes: const <String>['REUSED_CREDENTIAL'],
          createdAt: now,
          updatedAt: now,
        ),
        RemediationTask(
          id: 'done-task',
          type: RemediationTaskType.credential,
          status: RemediationTaskStatus.completed,
          title: 'Completed rotation',
          description: 'Credential rotated',
          target: 'Email',
          severity: AlertSeverity.medium,
          priorityScore: 0.58,
          reasonCodes: const <String>['WEAK_COMPLEXITY'],
          createdAt: now,
          updatedAt: now,
          completedAt: now,
        ),
      ],
      filter: UnifiedTriageFilter.remediation,
    );

    expect(items, hasLength(1));
    expect(items.single.id, 'open-task');
  });

  test('UnifiedTriageService filters exposures and anomalies', () {
    final service = UnifiedTriageService();
    final now = DateTime(2026, 7, 6);

    final exposures = service.buildTimeline(
      assessments: const [],
      credentialSnapshots: const [],
      remediationTasks: const [],
      exposureEvents: [
        ExposureEvent(
          source: 'BreachData',
          occurredAt: now,
          urgency: 'high',
          confidence: 0.9,
          accountHash: 'hash',
        ),
      ],
      filter: UnifiedTriageFilter.exposures,
    );

    expect(exposures, hasLength(1));
    expect(exposures.single.type, UnifiedTriageItemType.exposure);

    final anomalies = service.buildTimeline(
      assessments: const [],
      credentialSnapshots: const [],
      remediationTasks: const [],
      loginAnomalies: [
        LoginAnomaly(
          accountId: 'user_1',
          score: 0.75,
          riskBand: 'medium',
          reasonCodes: const ['NEW_GEO'],
          detectedAt: now,
        ),
      ],
      filter: UnifiedTriageFilter.anomalies,
    );

    expect(anomalies, hasLength(1));
    expect(anomalies.single.type, UnifiedTriageItemType.anomaly);
  });
}
