import 'package:flutter_test/flutter_test.dart';
import 'package:selferase/models/security/credential_snapshot.dart';
import 'package:selferase/models/security/remediation_task.dart';
import 'package:selferase/models/security/risk_assessment.dart';
import 'package:selferase/models/security/security_alert.dart';
import 'package:selferase/services/midterm_metrics_aggregator.dart';
import 'package:selferase/services/remediation_planner.dart';

void main() {
  group('RemediationPlanner', () {
    const planner = RemediationPlanner();

    test('creates phishing remediation tasks for medium-or-higher scans', () {
      final assessment = RiskAssessment(
        id: 'scan-1',
        targetAsset: 'https://paypa1-login.example',
        severity: AlertSeverity.high,
        finalScore: 0.82,
        localSignals: const <String, double>{'entropy': 0.8},
        enrichmentSignals: const <String, String>{'reputation': 'malicious'},
        assessedAt: DateTime(2026, 7, 6),
        alerts: [
          SecurityAlert(
            id: 'alert-1',
            type: AlertType.phishing,
            severity: AlertSeverity.high,
            confidence: 0.9,
            reasonCodes: const <String>['EDGE_REPUTATION_MATCH'],
            createdAt: DateTime(2026, 7, 6),
          ),
        ],
        recommendedActions: const [],
      );

      final tasks = planner.planForAssessment(assessment);

      expect(tasks, hasLength(1));
      expect(tasks.first.type, RemediationTaskType.phishing);
      expect(tasks.first.status, RemediationTaskStatus.queued);
      expect(tasks.first.reasonCodes, contains('EDGE_REPUTATION_MATCH'));
    });

    test('creates credential rotation and hardening tasks', () {
      final snapshot = CredentialSnapshot(
        id: 'cred-1',
        accountLabel: 'GitHub',
        username: 'user@example.com',
        passwordHash: 'hash',
        reuseHash: 'reuse',
        strengthScore: 0.2,
        reuseLikelihoodScore: 1.0,
        exposureScore: 1.0,
        finalScore: 0.92,
        severity: AlertSeverity.critical,
        reasonCodes: const <String>[
          'WEAK_COMPLEXITY',
          'REUSED_CREDENTIAL',
          'KNOWN_DATA_BREACH',
        ],
        createdAt: DateTime(2026, 7, 6),
        updatedAt: DateTime(2026, 7, 6),
      );

      final tasks = planner.planForCredential(snapshot);

      expect(tasks, hasLength(2));
      expect(
        tasks.map((task) => task.type),
        containsAll(<RemediationTaskType>[
          RemediationTaskType.credential,
          RemediationTaskType.accountHardening,
        ]),
      );
    });

    test('enforces lifecycle transition rules', () {
      final task = RemediationTask(
        id: 'task-1',
        type: RemediationTaskType.credential,
        status: RemediationTaskStatus.queued,
        title: 'Rotate password',
        description: 'Rotate reused credential',
        target: 'GitHub',
        severity: AlertSeverity.high,
        priorityScore: 0.82,
        reasonCodes: const <String>['REUSED_CREDENTIAL'],
        createdAt: DateTime(2026, 7, 6),
        updatedAt: DateTime(2026, 7, 6),
      );

      final started = planner.transition(
        task,
        RemediationTaskStatus.inProgress,
      );
      final completed = planner.transition(
        started,
        RemediationTaskStatus.completed,
      );

      expect(started.status, RemediationTaskStatus.inProgress);
      expect(completed.status, RemediationTaskStatus.completed);
      expect(completed.completedAt, isNotNull);
      expect(
        () => planner.transition(completed, RemediationTaskStatus.inProgress),
        throwsStateError,
      );
    });
  });

  group('MidtermMetricsAggregator', () {
    test('aggregates remediation and finding counts', () {
      final aggregator = MidtermMetricsAggregator();
      final metrics = aggregator.aggregate(
        assessments: const <RiskAssessment>[],
        credentialSnapshots: const <CredentialSnapshot>[],
        remediationTasks: [
          RemediationTask(
            id: 'task-1',
            type: RemediationTaskType.credential,
            status: RemediationTaskStatus.completed,
            title: 'Rotate password',
            description: 'Rotate reused credential',
            target: 'GitHub',
            severity: AlertSeverity.high,
            priorityScore: 0.82,
            reasonCodes: const <String>['REUSED_CREDENTIAL'],
            createdAt: DateTime(2026, 7, 6),
            updatedAt: DateTime(2026, 7, 6),
            completedAt: DateTime(2026, 7, 6),
          ),
          RemediationTask(
            id: 'task-2',
            type: RemediationTaskType.phishing,
            status: RemediationTaskStatus.queued,
            title: 'Block URL',
            description: 'Block suspicious URL',
            target: 'https://example.test',
            severity: AlertSeverity.critical,
            priorityScore: 1.0,
            reasonCodes: const <String>['EDGE_REPUTATION_MATCH'],
            createdAt: DateTime(2026, 7, 6),
            updatedAt: DateTime(2026, 7, 6),
          ),
        ],
      );

      expect(metrics.remediationTaskCount, 2);
      expect(metrics.completedRemediationTaskCount, 1);
      expect(metrics.openRemediationTaskCount, 1);
      expect(metrics.highPriorityTaskCount, 2);
    });
  });
}
