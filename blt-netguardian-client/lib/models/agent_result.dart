class AgentResult {
  final String id;
  final String taskId;
  final String agentId;
  final String agentType;
  final Map<String, dynamic> findings;
  final List<Vulnerability> vulnerabilities;
  final DateTime submittedAt;
  final ResultStatus status;

  AgentResult({
    required this.id,
    required this.taskId,
    required this.agentId,
    required this.agentType,
    required this.findings,
    required this.vulnerabilities,
    required this.submittedAt,
    required this.status,
  });

  factory AgentResult.fromJson(Map<String, dynamic> json) {
    return AgentResult(
      id: json['id'] as String,
      taskId: json['taskId'] as String,
      agentId: json['agentId'] as String,
      agentType: json['agentType'] as String,
      findings: json['findings'] as Map<String, dynamic>,
      vulnerabilities: (json['vulnerabilities'] as List<dynamic>)
          .map((v) => Vulnerability.fromJson(v as Map<String, dynamic>))
          .toList(),
      submittedAt: DateTime.parse(json['submittedAt'] as String),
      status: ResultStatus.values.firstWhere(
        (e) => e.name == json['status'],
        orElse: () => ResultStatus.pending,
      ),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'taskId': taskId,
      'agentId': agentId,
      'agentType': agentType,
      'findings': findings,
      'vulnerabilities': vulnerabilities.map((v) => v.toJson()).toList(),
      'submittedAt': submittedAt.toIso8601String(),
      'status': status.name,
    };
  }
}

class Vulnerability {
  final String id;
  final String title;
  final String description;
  final VulnerabilitySeverity severity;
  final String? cve;
  final String? cwe;
  final Map<String, dynamic> details;

  Vulnerability({
    required this.id,
    required this.title,
    required this.description,
    required this.severity,
    this.cve,
    this.cwe,
    required this.details,
  });

  factory Vulnerability.fromJson(Map<String, dynamic> json) {
    return Vulnerability(
      id: json['id'] as String,
      title: json['title'] as String,
      description: json['description'] as String,
      severity: VulnerabilitySeverity.values.firstWhere(
        (e) => e.name == json['severity'],
        orElse: () => VulnerabilitySeverity.medium,
      ),
      cve: json['cve'] as String?,
      cwe: json['cwe'] as String?,
      details: json['details'] as Map<String, dynamic>,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'description': description,
      'severity': severity.name,
      'cve': cve,
      'cwe': cwe,
      'details': details,
    };
  }
}

enum ResultStatus {
  pending,
  processing,
  triaged,
  stored,
}

enum VulnerabilitySeverity {
  critical,
  high,
  medium,
  low,
  info,
}