import 'package:bugheist/src/models/issue_model.dart';

/// Model class for the paginated data sent on requesting issues.
class IssueData {
  final int count;
  String? nextQuery;
  String? previousQuery;
  List<Issue>? issueList;

  IssueData({
    required this.count,
    this.nextQuery,
    this.previousQuery,
    this.issueList,
  });

  factory IssueData.fromJson(Map<String, dynamic> responseData) {
    return IssueData(
      count: responseData["count"],
      nextQuery: responseData["next"],
      previousQuery: responseData["previous"],
      issueList: responseData["results"],
    );
  }
}
