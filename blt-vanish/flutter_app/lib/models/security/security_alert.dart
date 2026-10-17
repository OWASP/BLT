import 'package:json_annotation/json_annotation.dart';

part 'security_alert.g.dart';

// Categorizes the alert into core threat processing workflows
enum AlertType {
  @JsonValue('phishing')
  phishing,
  @JsonValue('credential')
  credential,
  @JsonValue('exposure')
  exposure,
  @JsonValue('anomaly')
  anomaly,
}

// Defining the strict severity bands for the Risk Engine
enum AlertSeverity {
  @JsonValue('low') low,
  @JsonValue('medium') medium,
  @JsonValue('high') high,
  @JsonValue('critical') critical,
}

// Immutable data model representing a validated threat configuration alert
@JsonSerializable()
class SecurityAlert {
  final String id;
  final AlertType type;
  final AlertSeverity severity; 
  final double confidence; // Must be between 0.0 and 1.0
  final List<String> reasonCodes;
  final DateTime createdAt;

  // Constant Constructor
  const SecurityAlert({
    required this.id,
    required this.type,
    required this.severity,
    required this.confidence,
    required this.reasonCodes,
    required this.createdAt,
  }) : assert(
          confidence >= 0.0 && confidence <= 1.0,
          'Confidence level ($confidence) must be between 0.0 and 1.0.',
        );

  factory SecurityAlert.fromJson(Map<String, dynamic> json) => 
      _$SecurityAlertFromJson(json);
      
  Map<String, dynamic> toJson() => _$SecurityAlertToJson(this);
}
