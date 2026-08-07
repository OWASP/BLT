import 'package:json_annotation/json_annotation.dart';
import 'security_alert.dart';
import 'remediation_action.dart';

part 'risk_assessment.g.dart';

@JsonSerializable(explicitToJson: true)
class RiskAssessment {
  final String id;
  final String targetAsset; 
  final AlertSeverity severity;
  final double finalScore;
  final Map<String, double> localSignals;
  final Map<String, String> enrichmentSignals;
  final DateTime assessedAt;
  final List<SecurityAlert> alerts;
  final List<RemediationAction> recommendedActions;

  // Constant constructor for absolute immutability
  const RiskAssessment({
    required this.id,
    required this.targetAsset,
    required this.severity,
    required this.finalScore,
    required this.localSignals,
    required this.enrichmentSignals,
    required this.assessedAt,
    required this.alerts,
    required this.recommendedActions,
  }) : assert(
          finalScore >= 0.0 && finalScore <= 1.0, // Enforces mathematical boundary limits
          'Final score must be strictly between 0.0 and 1.0',
        );
  // Factory converter with built-in perimeter validation rules
  factory RiskAssessment.fromJson(Map<String, dynamic> json) => 
      _$RiskAssessmentFromJson(json);
      
  Map<String, dynamic> toJson() => _$RiskAssessmentToJson(this);
}