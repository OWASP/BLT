class Target {
  final String id;
  final String url;
  final TargetType type;
  final Map<String, dynamic> metadata;
  final DateTime registeredAt;
  final bool isActive;

  Target({
    required this.id,
    required this.url,
    required this.type,
    required this.metadata,
    required this.registeredAt,
    this.isActive = true,
  });

  factory Target.fromJson(Map<String, dynamic> json) {
    return Target(
      id: json['id'] as String,
      url: json['url'] as String,
      type: TargetType.values.firstWhere(
        (e) => e.name == json['type'],
        orElse: () => TargetType.website,
      ),
      metadata: json['metadata'] as Map<String, dynamic>,
      registeredAt: DateTime.parse(json['registeredAt'] as String),
      isActive: json['isActive'] as bool? ?? true,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'url': url,
      'type': type.name,
      'metadata': metadata,
      'registeredAt': registeredAt.toIso8601String(),
      'isActive': isActive,
    };
  }

  Target copyWith({
    String? id,
    String? url,
    TargetType? type,
    Map<String, dynamic>? metadata,
    DateTime? registeredAt,
    bool? isActive,
  }) {
    return Target(
      id: id ?? this.id,
      url: url ?? this.url,
      type: type ?? this.type,
      metadata: metadata ?? this.metadata,
      registeredAt: registeredAt ?? this.registeredAt,
      isActive: isActive ?? this.isActive,
    );
  }
}

enum TargetType {
  website,
  smartContract,
  api,
  repository,
}