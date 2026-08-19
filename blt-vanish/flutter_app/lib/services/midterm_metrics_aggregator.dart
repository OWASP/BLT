import '../models/security/credential_snapshot.dart';
import '../models/security/exposure_event.dart';
import '../models/security/login_anomaly.dart';
import '../models/security/remediation_task.dart';
import '../models/security/risk_assessment.dart';
import '../models/security/security_alert.dart';

/// Aggregated metrics across security scans, credentials, remediation tasks, exposures, and anomalies.
class MidtermMetrics {
  /// Total scan assessments count.
  final int scanCount;

  /// Total credential snapshots count.
  final int credentialSnapshotCount;

  /// Total remediation tasks count.
  final int remediationTaskCount;

  /// Total completed remediation tasks count.
  final int completedRemediationTaskCount;

  /// Total open (queued or in-progress) remediation tasks count.
  final int openRemediationTaskCount;

  /// High or critical priority remediation task count.
  final int highPriorityTaskCount;

  /// Average risk score across all findings (0.0 to 1.0).
  final double averageRiskScore;

  /// Exposure event count.
  final int exposureEventCount;

  /// Login anomaly count.
  final int loginAnomalyCount;

  const MidtermMetrics({
    required this.scanCount,
    required this.credentialSnapshotCount,
    required this.remediationTaskCount,
    required this.completedRemediationTaskCount,
    required this.openRemediationTaskCount,
    required this.highPriorityTaskCount,
    required this.averageRiskScore,
    required this.exposureEventCount,
    required this.loginAnomalyCount,
  });
}

/// Aggregates security finding models into a unified metrics summary.
class MidtermMetricsAggregator {
  /// Calculates aggregated metrics from finding lists.
  MidtermMetrics aggregate({
    required List<RiskAssessment> assessments,
    required List<CredentialSnapshot> credentialSnapshots,
    required List<RemediationTask> remediationTasks,
    List<ExposureEvent> exposureEvents = const [],
    List<LoginAnomaly> loginAnomalies = const [],
  }) {
    final scanCount = assessments.length;
    final credentialCount = credentialSnapshots.length;
    final taskCount = remediationTasks.length;

    final completedTasks = remediationTasks.where((t) => t.isTerminal).length;
    final openTasks = remediationTasks.where((t) => !t.isTerminal).length;
    final highPriorityTasks = remediationTasks
        .where((t) =>
            t.severity == AlertSeverity.high ||
            t.severity == AlertSeverity.critical)
        .length;

    final scores = <double>[
      ...assessments.map((a) => a.finalScore),
      ...credentialSnapshots.map((c) => c.finalScore),
      ...remediationTasks.map((r) => r.priorityScore),
      ...loginAnomalies.map((l) => l.score),
    ];

    final avgRisk = scores.isEmpty
        ? 0.0
        : scores.reduce((a, b) => a + b) / scores.length;

    return MidtermMetrics(
      scanCount: scanCount,
      credentialSnapshotCount: credentialCount,
      remediationTaskCount: taskCount,
      completedRemediationTaskCount: completedTasks,
      openRemediationTaskCount: openTasks,
      highPriorityTaskCount: highPriorityTasks,
      averageRiskScore: avgRisk,
      exposureEventCount: exposureEvents.length,
      loginAnomalyCount: loginAnomalies.length,
    );
  }
}
