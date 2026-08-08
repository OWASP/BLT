import 'security_alert.dart';

/// Supported remediation categories in the local remediation lifecycle.
enum RemediationTaskType {
  /// A phishing or suspicious URL remediation.
  phishing,

  /// A credential rotation or password hygiene remediation.
  credential,

  /// A data broker opt-out remediation.
  brokerOptOut,

  /// A general account/privacy hardening remediation.
  accountHardening,
}

/// State machine statuses for remediation work.
enum RemediationTaskStatus {
  /// Task has been planned but not started.
  queued,

  /// User has started the task.
  inProgress,

  /// Task is waiting for user or third-party confirmation.
  waitingForUser,

  /// Task is complete.
  completed,

  /// Task is blocked and needs manual review.
  blocked,

  /// Task was dismissed or is no longer relevant.
  cancelled,
}

/// Local-first remediation task generated from risk findings.
class RemediationTask {
  /// Creates a remediation task.
  const RemediationTask({
    required this.id,
    required this.type,
    required this.status,
    required this.title,
    required this.description,
    required this.target,
    required this.severity,
    required this.priorityScore,
    required this.reasonCodes,
    required this.createdAt,
    required this.updatedAt,
    this.sourceId,
    this.dueAt,
    this.completedAt,
    this.quickActionLabel,
    this.deepLink,
    this.notes,
  });

  /// Stable local task identifier.
  final String id;

  /// Task category.
  final RemediationTaskType type;

  /// Current lifecycle status.
  final RemediationTaskStatus status;

  /// Human-readable task title.
  final String title;

  /// Human-readable task detail.
  final String description;

  /// Asset or account being remediated.
  final String target;

  /// Severity inherited from the source finding.
  final AlertSeverity severity;

  /// Normalized ranking score in `[0, 1]`.
  final double priorityScore;

  /// Reason codes inherited from the source finding.
  final List<String> reasonCodes;

  /// Optional source finding id.
  final String? sourceId;

  /// Suggested deadline.
  final DateTime? dueAt;

  /// Creation timestamp.
  final DateTime createdAt;

  /// Last update timestamp.
  final DateTime updatedAt;

  /// Completion timestamp.
  final DateTime? completedAt;

  /// CTA label for the task.
  final String? quickActionLabel;

  /// Optional internal or external deep link.
  final String? deepLink;

  /// Optional user or system note.
  final String? notes;

  /// Whether this task is in a terminal state.
  bool get isTerminal =>
      status == RemediationTaskStatus.completed ||
      status == RemediationTaskStatus.cancelled;

  /// Deserializes a remediation task.
  factory RemediationTask.fromJson(Map<String, dynamic> json) {
    return RemediationTask(
      id: json['id'] as String,
      type: RemediationTaskType.values.firstWhere(
        (type) => type.name == json['type'],
        orElse: () => RemediationTaskType.accountHardening,
      ),
      status: RemediationTaskStatus.values.firstWhere(
        (status) => status.name == json['status'],
        orElse: () => RemediationTaskStatus.queued,
      ),
      title: json['title'] as String,
      description: json['description'] as String,
      target: json['target'] as String,
      severity: AlertSeverity.values.firstWhere(
        (severity) => severity.name == json['severity'],
        orElse: () => AlertSeverity.low,
      ),
      priorityScore: (json['priorityScore'] as num).toDouble(),
      reasonCodes: (json['reasonCodes'] as List<dynamic>? ?? <dynamic>[])
          .map((code) => code as String)
          .toList(),
      sourceId: json['sourceId'] as String?,
      dueAt: json['dueAt'] == null
          ? null
          : DateTime.parse(json['dueAt'] as String),
      createdAt: DateTime.parse(json['createdAt'] as String),
      updatedAt: DateTime.parse(json['updatedAt'] as String),
      completedAt: json['completedAt'] == null
          ? null
          : DateTime.parse(json['completedAt'] as String),
      quickActionLabel: json['quickActionLabel'] as String?,
      deepLink: json['deepLink'] as String?,
      notes: json['notes'] as String?,
    );
  }

  /// Serializes the task for encrypted persistence.
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'type': type.name,
      'status': status.name,
      'title': title,
      'description': description,
      'target': target,
      'severity': severity.name,
      'priorityScore': priorityScore,
      'reasonCodes': reasonCodes,
      'sourceId': sourceId,
      'dueAt': dueAt?.toIso8601String(),
      'createdAt': createdAt.toIso8601String(),
      'updatedAt': updatedAt.toIso8601String(),
      'completedAt': completedAt?.toIso8601String(),
      'quickActionLabel': quickActionLabel,
      'deepLink': deepLink,
      'notes': notes,
    };
  }

  /// Returns a copy with selected fields replaced.
  RemediationTask copyWith({
    RemediationTaskType? type,
    RemediationTaskStatus? status,
    String? title,
    String? description,
    String? target,
    AlertSeverity? severity,
    double? priorityScore,
    List<String>? reasonCodes,
    String? sourceId,
    DateTime? dueAt,
    DateTime? createdAt,
    DateTime? updatedAt,
    DateTime? completedAt,
    String? quickActionLabel,
    String? deepLink,
    String? notes,
  }) {
    return RemediationTask(
      id: id,
      type: type ?? this.type,
      status: status ?? this.status,
      title: title ?? this.title,
      description: description ?? this.description,
      target: target ?? this.target,
      severity: severity ?? this.severity,
      priorityScore: priorityScore ?? this.priorityScore,
      reasonCodes: reasonCodes ?? this.reasonCodes,
      sourceId: sourceId ?? this.sourceId,
      dueAt: dueAt ?? this.dueAt,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      completedAt: completedAt ?? this.completedAt,
      quickActionLabel: quickActionLabel ?? this.quickActionLabel,
      deepLink: deepLink ?? this.deepLink,
      notes: notes ?? this.notes,
    );
  }
}
