class Tag {
  final int id;
  final String name;
  Tag({
    required this.id,
    required this.name,
  });

  Tag copyWith({
    int? id,
    String? name,
  }) {
    return Tag(
      id: id ?? this.id,
      name: name ?? this.name,
    );
  }

  factory Tag.fromJson(dynamic json) {
    return Tag(
      id: json["id"],
      name: json["name"],
    );
  }

  static Map<String, dynamic> toJson(Tag tag) {
    return {
      "id": tag.id,
      "name": tag.name,
    };
  }

  static List<Tag> fromSnapshot(List<dynamic> json) {
    return json.map((data) => Tag.fromJson(data)).toList();
  }

  static List<Map<String, dynamic>> fromListToJson(List<Tag> tags) {
    return tags.map((tag) => Tag.toJson(tag)).toList();
  }
}
