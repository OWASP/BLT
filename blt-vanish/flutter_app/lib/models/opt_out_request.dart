import 'package:json_annotation/json_annotation.dart';

part 'opt_out_request.g.dart';

@JsonSerializable()
class OptOutRequest {
  final String id;
  final String brokerId;
  final String brokerName;
  final RequestStatus status;
  final DateTime createdAt;
  final DateTime? submittedAt;
  final DateTime? completedAt;
  final String? confirmationNumber;
  final String? notes;
  final List<RequestAction> actions;

  OptOutRequest({
    required this.id,
    required this.brokerId,
    required this.brokerName,
    required this.status,
    required this.createdAt,
    this.submittedAt,
    this.completedAt,
    this.confirmationNumber,
    this.notes,
    this.actions = const [],
  });

  factory OptOutRequest.fromJson(Map<String, dynamic> json) =>
      _$OptOutRequestFromJson(json);
  Map<String, dynamic> toJson() => _$OptOutRequestToJson(this);

  OptOutRequest copyWith({
    RequestStatus? status,
    DateTime? submittedAt,
    DateTime? completedAt,
    String? confirmationNumber,
    String? notes,
    List<RequestAction>? actions,
  }) {
    return OptOutRequest(
      id: id,
      brokerId: brokerId,
      brokerName: brokerName,
      status: status ?? this.status,
      createdAt: createdAt,
      submittedAt: submittedAt ?? this.submittedAt,
      completedAt: completedAt ?? this.completedAt,
      confirmationNumber: confirmationNumber ?? this.confirmationNumber,
      notes: notes ?? this.notes,
      actions: actions ?? this.actions,
    );
  }
}

@JsonSerializable()
class RequestAction {
  final String id;
  final ActionType type;
  final DateTime timestamp;
  final String description;
  final String? details;

  RequestAction({
    required this.id,
    required this.type,
    required this.timestamp,
    required this.description,
    this.details,
  });

  factory RequestAction.fromJson(Map<String, dynamic> json) =>
      _$RequestActionFromJson(json);
  Map<String, dynamic> toJson() => _$RequestActionToJson(this);
}

enum RequestStatus {
  @JsonValue('draft')
  draft,
  @JsonValue('pending')
  pending,
  @JsonValue('submitted')
  submitted,
  @JsonValue('acknowledged')
  acknowledged,
  @JsonValue('completed')
  completed,
  @JsonValue('failed')
  failed,
  @JsonValue('requires_action')
  requiresAction,
}

enum ActionType {
  @JsonValue('created')
  created,
  @JsonValue('submitted')
  submitted,
  @JsonValue('email_sent')
  emailSent,
  @JsonValue('form_filled')
  formFilled,
  @JsonValue('mail_sent')
  mailSent,
  @JsonValue('response_received')
  responseReceived,
  @JsonValue('completed')
  completed,
  @JsonValue('failed')
  failed,
  @JsonValue('note_added')
  noteAdded,
}
