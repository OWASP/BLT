import 'package:intl/intl.dart';

import './user_model.dart';

/// Model class for an issue posted on BugHeist.
class Issue {
  final int? id;
  final User? user;
  final String url;
  final String description;
  final int? label;
  final bool isVerified;
  final int? score;
  final bool isOpen;
  final String? userAgent;
  final String ocr;
  final String? screenshotLink;
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
    required this.description,
    this.label,
    required this.isVerified,
    this.score,
    required this.isOpen,
    this.userAgent,
    required this.ocr,
    this.screenshotLink,
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
      description: responseData["description"],
      label: responseData["label"],
      isVerified: responseData["verified"],
      score: responseData["score"],
      isOpen: (responseData["status"] == "open") ? true : false,
      userAgent: responseData["user_agent"],
      ocr: responseData["ocr"],
      screenshotLink: responseData["screenshot"],
      closedDate: (responseData["closed_date"].runtimeType != Null)
          ? DateTime.parse(responseData["closed_date"])
          : null,
      githubUrl: responseData["github_url"],
      created: DateTime.parse(responseData["created"]),
      lastModified: DateTime.parse(responseData["modified"]),
      hunt: responseData["hunt"],
      domain: responseData["domain"],
      closedBy: responseData["closed_by"],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'user': {
        'username': user!.username!.trim(),
      },
      'url': url.trim(),
      'verified': isVerified,
      'score': 0,
      'status': isOpen ? "open" : "closed",
      'description': description,
      // "hunt": null,
      // "domain": null,
      // "closed_by": null,
    };
  }
}
