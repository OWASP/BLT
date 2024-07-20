class Contributors {
  final int id;
  final String name;
  final int githubId;
  final String githubUrl;
  final String image;
  final String type;
  final int contributions;

  Contributors({
    required this.id,
    required this.name,
    required this.githubId,
    required this.githubUrl,
    required this.image,
    required this.type,
    required this.contributions,
  });

  Contributors copyWith({
    int? id,
    String? name,
    int? githubId,
    String? githubUrl,
    String? image,
    String? type,
    int? contributions,
  }) {
    return Contributors(
      id: id ?? this.id,
      name: name ?? this.name,
      githubId: id ?? this.githubId,
      githubUrl: githubUrl ?? this.githubUrl,
      image: image ?? this.image,
      type: type ?? this.type,
      contributions: contributions ?? this.contributions,
    );
  }

  factory Contributors.fromJson(dynamic json) {
    return Contributors(
      id: json['id'],
      name: json['name'],
      githubId: json['github_id'],
      githubUrl: json['github_url'],
      image: json['avatar'],
      type: json['contributor_type'],
      contributions: json['contributions'],
    );
  }
  static List<Contributors> fromSnapshot(List<dynamic> json) {
    return json.map((data) => Contributors.fromJson(data)).toList();
  }
}
