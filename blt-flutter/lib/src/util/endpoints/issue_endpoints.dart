/// Class for API endpoints to access issues on BugHeist.
class IssueEndPoints {
  IssueEndPoints._();

  static const String baseUrl = "https://www.bugheist.com/api/v1/";

  static const String issues = baseUrl + "issues/";

  static const String userIssues = baseUrl + "userissues/";

  static const String likeIssues = baseUrl + "issue/like/";

  static const String flagIssues = baseUrl + "issue/flag/";
}
