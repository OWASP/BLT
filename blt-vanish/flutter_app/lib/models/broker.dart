import 'package:json_annotation/json_annotation.dart';

part 'broker.g.dart';

@JsonSerializable()
class Broker {
  final String id;
  final String name;
  final String description;
  final String website;
  final String? optOutUrl;
  final String category;
  final List<String> dataTypes;
  final OptOutMethod optOutMethod;
  final String? contactEmail;
  final String? contactPhone;
  final String? mailingAddress;
  final int? estimatedResponseDays;
  final List<String> requiredFields;
  final String? notes;
  final bool isActive;

  Broker({
    required this.id,
    required this.name,
    required this.description,
    required this.website,
    this.optOutUrl,
    required this.category,
    required this.dataTypes,
    required this.optOutMethod,
    this.contactEmail,
    this.contactPhone,
    this.mailingAddress,
    this.estimatedResponseDays,
    required this.requiredFields,
    this.notes,
    this.isActive = true,
  });

  factory Broker.fromJson(Map<String, dynamic> json) => _$BrokerFromJson(json);
  Map<String, dynamic> toJson() => _$BrokerToJson(this);
}

@JsonSerializable()
class OptOutMethod {
  final String type; // 'online_form', 'email', 'mail', 'phone', 'multiple'
  final String instructions;
  final String? templateId;
  final List<String> steps;

  OptOutMethod({
    required this.type,
    required this.instructions,
    this.templateId,
    required this.steps,
  });

  factory OptOutMethod.fromJson(Map<String, dynamic> json) =>
      _$OptOutMethodFromJson(json);
  Map<String, dynamic> toJson() => _$OptOutMethodToJson(this);
}
