import 'package:bugheist/models/issue_model.dart';

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
    print(responseData["next"]);
    return IssueData(
      count: responseData["count"],
      nextQuery: responseData["next"],
      previousQuery: responseData["previous"],
      issueList: responseData["results"],
    );
  }
}
