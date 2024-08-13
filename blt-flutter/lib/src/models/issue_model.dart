import 'package:blt/src/models/tags_model.dart';
import 'package:intl/intl.dart';

import './user_model.dart';

/// Model class for an issue posted on BLT.
class Issue {
  final int? id;
  final User? user;
  final String url;
  final String title;
  final String? description;
  final int? label;
  final bool isVerified;
  final int? score;
  final bool isOpen;
  final String? userAgent;
  String? ocr;
  int? likes;
  int? flags;
  bool? liked;
  bool? flagged;
  List<Tag>? tags;
  final List<String>? screenshotsLink;
  final DateTime? closedDate;
  final String? githubUrl;
  final DateTime? created;
  final DateTime? lastModified;
  final int? hunt;
  final int? domain;
  final String? closedBy;

  final DateFormat dateFormatter = DateFormat('d MMMM, yyyy');

  String? get closed_date {
    return (closedDate != null)
        ? dateFormatter.format(closedDate!.toLocal())
        : null;
  }

  String get created_date => dateFormatter.format(created!.toLocal());

  String? get last_modified_date {
    return (lastModified != null)
        ? dateFormatter.format(lastModified!.toLocal())
        : null;
  }

  Issue({
    this.id,
    this.user,
    required this.url,
    required this.title,
    required this.description,
    this.label,
    required this.isVerified,
    this.score,
    this.tags,
    required this.isOpen,
    this.userAgent,
    this.ocr,
    this.likes,
    this.flags,
    this.liked,
    this.flagged,
    this.screenshotsLink,
    this.closedDate,
    this.githubUrl,
    this.created,
    this.lastModified,
    this.hunt,
    this.domain,
    this.closedBy,
  });

  factory Issue.fromJson(Map<String, dynamic> responseData) {
    return Issue(
      id: responseData["id"],
      user: (responseData["user"] != null)
          ? User(
              id: responseData["user"]["id"],
              username: responseData["user"]["username"],
            )
          : null,
      url: responseData["url"],
      title: responseData["description"],
      description: responseData["markdown_description"] ?? "",
      label: responseData["label"],
      isVerified: responseData["verified"],
      score: responseData["score"],
      isOpen: (responseData["status"] == "open") ? true : false,
      userAgent: responseData["user_agent"],
      ocr: responseData["ocr"],
      likes: responseData["upvotes"],
      flags: responseData["flags"],
      liked: responseData["upvotted"],
      flagged: responseData["flagged"],
      screenshotsLink: responseData["screenshots"].cast<String>(),
      closedDate: (responseData["closed_date"].runtimeType != Null)
          ? DateTime.parse(responseData["closed_date"])
          : null,
      githubUrl: responseData["github_url"],
      created: DateTime.parse(responseData["created"]),
      lastModified: DateTime.parse(responseData["modified"]),
      hunt: responseData["hunt"],
      domain: responseData["domain"],
      closedBy: responseData["closed_by"],
      tags: Tag.fromSnapshot(responseData["tags"]),
    );
  }

  Map<String, dynamic> toJson() {
    List<int> tagId = [];
    for (int i = 0; i < (tags?.length ?? 0); i++) {
      tagId.add(tags![i].id);
    }
    return {
      'user': {
        'username': user!.username!.trim(),
      },
      'url': url.trim(),
      'verified': isVerified,
      'score': 0,
      'status': isOpen ? "open" : "closed",
      'description': description,
      'label': label,
      'tags': tagId,
      // "hunt": null,
      // "domain": null,
      // "closed_by": null,
    };
  }
}
