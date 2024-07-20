import 'package:blt/src/models/contributors_model.dart';

import '../util/util_import.dart';

class Project {
  final int id;
  final String name;
  final String slug;
  final String description;
  final String github_url;
  String? wiki_url;
  String? homepage_url;
  final String logo;
  DateTime? created;
  List<Contributors>? contributors;

  Project({
    required this.id,
    required this.name,
    required this.slug,
    required this.description,
    required this.github_url,
    this.wiki_url,
    this.homepage_url,
    required this.logo,
    this.created,
    this.contributors,
  });

  Project copyWith({
    int? id,
    String? name,
    String? slug,
    String? description,
    String? github_url,
    String? wiki_url,
    String? homepage_url,
    String? logo,
    DateTime? created,
    List<Contributors>? contributors,
  }) {
    return Project(
      id: id ?? this.id,
      name: name ?? this.name,
      slug: slug ?? this.slug,
      description: description ?? this.description,
      github_url: github_url ?? this.github_url,
      wiki_url: wiki_url ?? this.wiki_url,
      homepage_url: homepage_url ?? this.homepage_url,
      logo: logo ?? this.logo,
      created: created ?? this.created,
      contributors: contributors ?? this.contributors,
    );
  }

  factory Project.fromJson(dynamic json) {
    return Project(
      id: json["id"],
      name: json['name'],
      slug: json['slug'],
      description: json['description'],
      github_url: json['github_url'],
      wiki_url: json['wiki_url'] != null ? json['wiki_url'] as String : "",
      homepage_url:
          json['homepage_url'] != null ? json['homepage_url'] as String : "",
      logo: GeneralEndPoints.baseUrl + json['logo'],
      created: json['created'] != null ? DateTime.parse(json['created']) : null,
      contributors: json['contributors'] != null
          ? Contributors.fromSnapshot(json['contributors'])
          : null,
    );
  }

  static List<Project> fromSnapshot(List<dynamic> json) {
    return json.map((data) => Project.fromJson(data)).toList();
  }
}
