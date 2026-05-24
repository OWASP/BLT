import 'package:json_annotation/json_annotation.dart';

part 'monitor_entry.g.dart';

/// Represents a monitored keyword, takedown, or personal info item
@JsonSerializable()
class MonitorEntry {
  final String id;
  final String keyword;
  final MonitorType type;
  final bool isActive;
  final int matchCount;
  final DateTime? lastCheckedAt;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String? notes;

  MonitorEntry({
    required this.id,
    required this.keyword,
    required this.type,
    this.isActive = true,
    this.matchCount = 0,
    this.lastCheckedAt,
    required this.createdAt,
    required this.updatedAt,
    this.notes,
  });

  factory MonitorEntry.fromJson(Map<String, dynamic> json) =>
      _$MonitorEntryFromJson(json);
  Map<String, dynamic> toJson() => _$MonitorEntryToJson(this);

  MonitorEntry copyWith({
    String? keyword,
    MonitorType? type,
    bool? isActive,
    int? matchCount,
    DateTime? lastCheckedAt,
    DateTime? updatedAt,
    String? notes,
  }) {
    return MonitorEntry(
      id: id,
      keyword: keyword ?? this.keyword,
      type: type ?? this.type,
      isActive: isActive ?? this.isActive,
      matchCount: matchCount ?? this.matchCount,
      lastCheckedAt: lastCheckedAt ?? this.lastCheckedAt,
      createdAt: createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      notes: notes ?? this.notes,
    );
  }
}

enum MonitorType {
  @JsonValue('keyword')
  keyword,
  @JsonValue('takedown')
  takedown,
  @JsonValue('personal_info')
  personalInfo,
}
