import 'package:json_annotation/json_annotation.dart';
import 'security_alert.dart';

part 'remediation_action.g.dart';

@JsonSerializable()
class RemediationAction {
  final String id;
  final String title;
  final String description;
  final AlertSeverity urgency;
  final String? deepLink;

  const RemediationAction({
    required this.id,
    required this.title,
    required this.description,
    required this.urgency,
    this.deepLink,
  });

  factory RemediationAction.fromJson(Map<String, dynamic> json) =>
      _$RemediationActionFromJson(json);

  Map<String, dynamic> toJson() => _$RemediationActionToJson(this);
}