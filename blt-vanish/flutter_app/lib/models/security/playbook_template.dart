import 'package:flutter/foundation.dart';

/// Represents a step within a remediation playbook.
class PlaybookStep {
  final String id;
  final String title;
  final String description;
  final String actionType; // e.g., 'password_reset', 'revoke_session', 'enable_mfa'
  final bool isRequired;

  const PlaybookStep({
    required this.id,
    required this.title,
    required this.description,
    required this.actionType,
    required this.isRequired,
  });

  factory PlaybookStep.fromJson(Map<String, dynamic> json) {
    return PlaybookStep(
      id: json['id'] as String,
      title: json['title'] as String,
      description: json['description'] as String,
      actionType: json['actionType'] as String,
      isRequired: json['isRequired'] as bool,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'description': description,
      'actionType': actionType,
      'isRequired': isRequired,
    };
  }
}

/// Contract for a remediation playbook template.
class PlaybookTemplate {
  final String id;
  final String title;
  final String severityTrigger; // e.g., 'critical', 'high'
  final List<PlaybookStep> steps;

  const PlaybookTemplate({
    required this.id,
    required this.title,
    required this.severityTrigger,
    required this.steps,
  });

  factory PlaybookTemplate.fromJson(Map<String, dynamic> json) {
    var stepsList = json['steps'] as List;
    List<PlaybookStep> steps = stepsList.map((i) => PlaybookStep.fromJson(i)).toList();

    return PlaybookTemplate(
      id: json['id'] as String,
      title: json['title'] as String,
      severityTrigger: json['severityTrigger'] as String,
      steps: steps,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'severityTrigger': severityTrigger,
      'steps': steps.map((s) => s.toJson()).toList(),
    };
  }
}
