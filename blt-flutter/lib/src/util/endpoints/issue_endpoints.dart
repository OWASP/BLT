import 'general_endpoints.dart';

/// Class for API endpoints to access issues on BLT.
class IssueEndPoints {
  IssueEndPoints._();

  // static const String issues = GeneralEndPoints.apiBaseUrl + "issues/";

  static const String userIssues = GeneralEndPoints.apiBaseUrl + "userissues/";

  static const String likeIssues = GeneralEndPoints.apiBaseUrl + "issue/like/";

  static const String flagIssues = GeneralEndPoints.apiBaseUrl + "issue/flag/";
}
