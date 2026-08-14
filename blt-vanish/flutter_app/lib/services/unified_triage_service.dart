import '../models/security/credential_snapshot.dart';
import '../models/security/remediation_task.dart';
import '../models/security/risk_assessment.dart';
import '../models/security/security_alert.dart';

/// Types of items shown in the unified triage queue.
enum UnifiedTriageItemType {
  /// Phishing/security scan item.
  phishing,

  /// Credential hygiene item.
  credential,

  /// Remediation lifecycle item.
  remediation,
}

/// Global triage filter.
enum UnifiedTriageFilter {
  /// Show all items.
  all,

  /// Show phishing items.
  phishing,

  /// Show credential items.
  credentials,

  /// Show open remediation work.
  remediation,
}

/// Ranked item in the unified risk timeline.
class UnifiedTriageItem {
  /// Creates a ranked triage item.
  const UnifiedTriageItem({
    required this.id,
    required this.type,
    required this.title,
    required this.subtitle,
    required this.severity,
    required this.priorityScore,
    required this.createdAt,
    required this.quickActionLabel,
    this.reasonCodes = const <String>[],
    this.isActionable = true,
  });

  /// Stable item id.
  final String id;

  /// Item category.
  final UnifiedTriageItemType type;

  /// Display title.
  final String title;

  /// Display subtitle.
  final String subtitle;

  /// Severity.
  final AlertSeverity severity;

  /// Normalized priority score.
  final double priorityScore;

  /// Item timestamp.
  final DateTime createdAt;

  /// CTA label.
  final String quickActionLabel;

  /// Explainability codes.
  final List<String> reasonCodes;

  /// Whether quick action is active.
  final bool isActionable;
}

/// Ranks phishing, credential, and remediation items into one timeline.
class UnifiedTriageService {
  /// Builds a filtered and ranked triage timeline.
  List<UnifiedTriageItem> buildTimeline({
    required List<RiskAssessment> assessments,
    required List<CredentialSnapshot> credentialSnapshots,
    required List<RemediationTask> remediationTasks,
    UnifiedTriageFilter filter = UnifiedTriageFilter.all,
  }) {
    final items = <UnifiedTriageItem>[
      ...assessments.map(_fromAssessment),
      ...credentialSnapshots.map(_fromCredential),
      ...remediationTasks.map(_fromRemediationTask),
    ].where((item) => _matchesFilter(item, filter)).toList()
      ..sort((left, right) {
        final priority = right.priorityScore.compareTo(left.priorityScore);
        if (priority != 0) {
          return priority;
        }
        return right.createdAt.compareTo(left.createdAt);
      });

    return items;
  }

  UnifiedTriageItem _fromAssessment(RiskAssessment assessment) {
    return UnifiedTriageItem(
      id: assessment.id,
      type: UnifiedTriageItemType.phishing,
      title: 'Suspicious link scan',
      subtitle: assessment.targetAsset,
      severity: assessment.severity,
      priorityScore: assessment.finalScore,
      createdAt: assessment.assessedAt,
      quickActionLabel: 'Review scan',
      reasonCodes: assessment.alerts.isEmpty
          ? const <String>[]
          : assessment.alerts.first.reasonCodes,
      isActionable: assessment.severity != AlertSeverity.low,
    );
  }

  UnifiedTriageItem _fromCredential(CredentialSnapshot snapshot) {
    return UnifiedTriageItem(
      id: snapshot.id,
      type: UnifiedTriageItemType.credential,
      title: 'Credential hygiene finding',
      subtitle: snapshot.accountLabel,
      severity: snapshot.severity,
      priorityScore: snapshot.finalScore,
      createdAt: snapshot.updatedAt,
      quickActionLabel: 'Open credential check',
      reasonCodes: snapshot.reasonCodes,
      isActionable: snapshot.severity != AlertSeverity.low,
    );
  }

  UnifiedTriageItem _fromRemediationTask(RemediationTask task) {
    return UnifiedTriageItem(
      id: task.id,
      type: UnifiedTriageItemType.remediation,
      title: task.title,
      subtitle: task.target,
      severity: task.severity,
      priorityScore: task.isTerminal ? task.priorityScore * 0.45 : task.priorityScore,
      createdAt: task.updatedAt,
      quickActionLabel: task.quickActionLabel ?? 'Update task',
      reasonCodes: task.reasonCodes,
      isActionable: !task.isTerminal,
    );
  }

  bool _matchesFilter(UnifiedTriageItem item, UnifiedTriageFilter filter) {
    return switch (filter) {
      UnifiedTriageFilter.all => true,
      UnifiedTriageFilter.phishing =>
        item.type == UnifiedTriageItemType.phishing,
      UnifiedTriageFilter.credentials =>
        item.type == UnifiedTriageItemType.credential,
      UnifiedTriageFilter.remediation =>
        item.type == UnifiedTriageItemType.remediation && item.isActionable,
    };
  }
}
