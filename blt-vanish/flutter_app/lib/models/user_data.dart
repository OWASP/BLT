import 'package:json_annotation/json_annotation.dart';

part 'user_data.g.dart';

/// User's personal data stored encrypted locally
@JsonSerializable()
class UserData {
  final String id;
  final String firstName;
  final String? middleName;
  final String lastName;
  final List<String> emails;
  final List<String> phoneNumbers;
  final List<Address> addresses;
  final List<String> previousNames;
  final DateTime? dateOfBirth;
  final String? notes;
  final DateTime createdAt;
  final DateTime updatedAt;

  UserData({
    required this.id,
    required this.firstName,
    this.middleName,
    required this.lastName,
    required this.emails,
    required this.phoneNumbers,
    required this.addresses,
    this.previousNames = const [],
    this.dateOfBirth,
    this.notes,
    required this.createdAt,
    required this.updatedAt,
  });

  factory UserData.fromJson(Map<String, dynamic> json) =>
      _$UserDataFromJson(json);
  Map<String, dynamic> toJson() => _$UserDataToJson(this);

  String get fullName {
    if (middleName != null && middleName!.isNotEmpty) {
      return '$firstName $middleName $lastName';
    }
    return '$firstName $lastName';
  }
}

@JsonSerializable()
class Address {
  final String street;
  final String? street2;
  final String city;
  final String state;
  final String zipCode;
  final String country;
  final bool isCurrent;

  Address({
    required this.street,
    this.street2,
    required this.city,
    required this.state,
    required this.zipCode,
    this.country = 'USA',
    this.isCurrent = true,
  });

  factory Address.fromJson(Map<String, dynamic> json) =>
      _$AddressFromJson(json);
  Map<String, dynamic> toJson() => _$AddressToJson(this);

  String get fullAddress {
    final parts = [
      street,
      if (street2 != null && street2!.isNotEmpty) street2,
      '$city, $state $zipCode',
      if (country != 'USA') country,
    ];
    return parts.join('\n');
  }
}
