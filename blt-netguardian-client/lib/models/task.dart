class Task {
  final String id;
  final String type;
  final String target;
  final Map<String, dynamic> parameters;
  final TaskStatus status;
  final DateTime createdAt;
  final DateTime? completedAt;
  final String? result;
  final String? error;

  Task({
    required this.id,
    required this.type,
    required this.target,
    required this.parameters,
    required this.status,
    required this.createdAt,
    this.completedAt,
    this.result,
    this.error,
  });

  factory Task.fromJson(Map<String, dynamic> json) {
    return Task(
      id: json['id'] as String,
      type: json['type'] as String,
      target: json['target'] as String,
      parameters: json['parameters'] as Map<String, dynamic>,
      status: TaskStatus.values.firstWhere(
        (e) => e.name == json['status'],
        orElse: () => TaskStatus.pending,
      ),
      createdAt: DateTime.parse(json['createdAt'] as String),
      completedAt: json['completedAt'] != null
          ? DateTime.parse(json['completedAt'] as String)
          : null,
      result: json['result'] as String?,
      error: json['error'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'type': type,
      'target': target,
      'parameters': parameters,
      'status': status.name,
      'createdAt': createdAt.toIso8601String(),
      'completedAt': completedAt?.toIso8601String(),
      'result': result,
      'error': error,
    };
  }

  Task copyWith({
    String? id,
    String? type,
    String? target,
    Map<String, dynamic>? parameters,
    TaskStatus? status,
    DateTime? createdAt,
    DateTime? completedAt,
    String? result,
    String? error,
  }) {
    return Task(
      id: id ?? this.id,
      type: type ?? this.type,
      target: target ?? this.target,
      parameters: parameters ?? this.parameters,
      status: status ?? this.status,
      createdAt: createdAt ?? this.createdAt,
      completedAt: completedAt ?? this.completedAt,
      result: result ?? this.result,
      error: error ?? this.error,
    );
  }
}

enum TaskStatus {
  pending,
  queued,
  processing,
  completed,
  failed,
}

enum TaskType {
  web2Crawler,
  web3Monitor,
  staticAnalyzer,
  contractScanner,
  volunteerAgent,
}