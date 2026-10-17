import 'package:uuid/uuid.dart';

import '../models/security/credential_snapshot.dart';
import '../models/security/remediation_task.dart';
import '../models/security/risk_assessment.dart';
import '../models/security/security_alert.dart';

/// Deterministic planner for turning findings into remediation tasks.
class RemediationPlanner {
  /// Creates a remediation planner.
  const RemediationPlanner({Uuid uuid = const Uuid()}) : _uuid = uuid;

  final Uuid _uuid;

  /// Builds remediation tasks from a phishing risk assessment.
  List<RemediationTask> planForAssessment(RiskAssessment assessment) {
    if (assessment.severity == AlertSeverity.low) {
      return const <RemediationTask>[];
    }

    final now = DateTime.now();
    final dueAt = _dueDateForSeverity(assessment.severity, now);
    final reasonCodes = assessment.alerts.isEmpty
        ? <String>[]
        : assessment.alerts.first.reasonCodes;

    return [
      RemediationTask(
        id: _uuid.v4(),
        type: RemediationTaskType.phishing,
        status: RemediationTaskStatus.queued,
        title: 'Block suspicious navigation target',
        description:
            'Avoid entering credentials or session data into this target and report or block it if needed.',
        target: assessment.targetAsset,
        severity: assessment.severity,
        priorityScore: _priorityForSeverity(assessment.severity),
        reasonCodes: reasonCodes,
        sourceId: assessment.id,
        dueAt: dueAt,
        createdAt: now,
        updatedAt: now,
        quickActionLabel: 'Review scan',
        deepLink: 'security-center',
      ),
    ];
  }

  /// Builds remediation tasks from a credential hygiene snapshot.
  List<RemediationTask> planForCredential(CredentialSnapshot snapshot) {
    if (snapshot.severity == AlertSeverity.low) {
      return const <RemediationTask>[];
    }

    final now = DateTime.now();
    final tasks = <RemediationTask>[];

    if (snapshot.reasonCodes.contains('WEAK_COMPLEXITY') ||
        snapshot.reasonCodes.contains('REUSED_CREDENTIAL')) {
      tasks.add(
        RemediationTask(
          id: _uuid.v4(),
          type: RemediationTaskType.credential,
          status: RemediationTaskStatus.queued,
          title: 'Rotate weak or reused credential',
          description:
              'Change this password to a unique passphrase and update your password manager.',
          target: snapshot.accountLabel,
          severity: snapshot.severity,
          priorityScore: _priorityForSeverity(snapshot.severity),
          reasonCodes: snapshot.reasonCodes,
          sourceId: snapshot.id,
          dueAt: _dueDateForSeverity(snapshot.severity, now),
          createdAt: now,
          updatedAt: now,
          quickActionLabel: 'Open credential check',
          deepLink: 'credential-hygiene',
        ),
      );
    }

    if (snapshot.reasonCodes.contains('KNOWN_DATA_BREACH')) {
      tasks.add(
        RemediationTask(
          id: _uuid.v4(),
          type: RemediationTaskType.accountHardening,
          status: RemediationTaskStatus.queued,
          title: 'Enable account protection',
          description:
              'Enable MFA, review active sessions, and revoke unknown devices for this account.',
          target: snapshot.accountLabel,
          severity: snapshot.severity,
          priorityScore: (_priorityForSeverity(snapshot.severity) + 0.08)
              .clamp(0.0, 1.0),
          reasonCodes: snapshot.reasonCodes,
          sourceId: snapshot.id,
          dueAt: _dueDateForSeverity(snapshot.severity, now),
          createdAt: now,
          updatedAt: now,
          quickActionLabel: 'Review hardening',
          deepLink: 'credential-hygiene',
        ),
      );
    }

    return tasks;
  }

  /// Applies a validated state transition.
  RemediationTask transition(
    RemediationTask task,
    RemediationTaskStatus nextStatus, {
    String? note,
  }) {
    if (!_allowedTransitions[task.status]!.contains(nextStatus)) {
      throw StateError(
        'Invalid remediation transition: ${task.status.name} -> ${nextStatus.name}',
      );
    }

    final now = DateTime.now();
    return task.copyWith(
      status: nextStatus,
      updatedAt: now,
      completedAt:
          nextStatus == RemediationTaskStatus.completed ? now : task.completedAt,
      notes: note ?? task.notes,
    );
  }

  static const _allowedTransitions = <RemediationTaskStatus,
      Set<RemediationTaskStatus>>{
    RemediationTaskStatus.queued: {
      RemediationTaskStatus.inProgress,
      RemediationTaskStatus.cancelled,
      RemediationTaskStatus.blocked,
    },
    RemediationTaskStatus.inProgress: {
      RemediationTaskStatus.waitingForUser,
      RemediationTaskStatus.completed,
      RemediationTaskStatus.blocked,
      RemediationTaskStatus.cancelled,
    },
    RemediationTaskStatus.waitingForUser: {
      RemediationTaskStatus.inProgress,
      RemediationTaskStatus.completed,
      RemediationTaskStatus.blocked,
      RemediationTaskStatus.cancelled,
    },
    RemediationTaskStatus.blocked: {
      RemediationTaskStatus.inProgress,
      RemediationTaskStatus.cancelled,
    },
    RemediationTaskStatus.completed: <RemediationTaskStatus>{},
    RemediationTaskStatus.cancelled: <RemediationTaskStatus>{},
  };

  DateTime _dueDateForSeverity(AlertSeverity severity, DateTime now) {
    return switch (severity) {
      AlertSeverity.critical => now.add(const Duration(hours: 24)),
      AlertSeverity.high => now.add(const Duration(days: 3)),
      AlertSeverity.medium => now.add(const Duration(days: 7)),
      AlertSeverity.low => now.add(const Duration(days: 30)),
    };
  }

  double _priorityForSeverity(AlertSeverity severity) {
    return switch (severity) {
      AlertSeverity.critical => 1.0,
      AlertSeverity.high => 0.82,
      AlertSeverity.medium => 0.58,
      AlertSeverity.low => 0.24,
    };
  }
}
