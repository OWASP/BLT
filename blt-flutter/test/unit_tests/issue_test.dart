import '../test_imports.dart';
import 'package:http/http.dart' as http;

void main() {
  setUp(() {
    currentUser = guestUser;
  });
  group("Issue Api's Test", () {
    test('getAllIssues returns correct data', () async {
      final paginatedUrl = 'https://www.bugheist.com/api/v1/issues/';
      final dynamic mockResponse = {
        "count": 244,
        "next": "https://www.bugheist.com/api/v1/issues/?page=2&search=bug",
        "previous": null,
        "results": [
          {
            "id": 1,
            "user": null,
            "url": "http://bugheist.com",
            "description": "Issue 1",
            "markdown_description": "",
            "label": 0,
            "views": 64,
            "verified": false,
            "score": null,
            "status": "open",
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64",
            "screenshot": null,
            "closed_date": null,
            "github_url": "",
            "created": "2024-03-23T15:45:31.895903Z",
            "modified": "2024-03-29T03:42:55.120275Z",
            "is_hidden": false,
            "rewarded": 0,
            "reporter_ip_address": "24.90.6.174",
            "cve_id": null,
            "cve_score": null,
            "hunt": null,
            "domain": 3,
            "closed_by": null,
            "team_members": [],
            "upvotes": 0,
            "flags": 0,
            "upvotted": false,
            "flagged": false,
            "screenshots": [
              "https://storage.googleapis.com/bhfiles/screenshots/pasted-ima0265cdff-894d-48ff-ab07-4ad962.png"
            ]
          }
        ]
      };
      final client = MockClient((request) async {
        // Create sample response of the HTTP call //
        final response = mockResponse;
        return http.Response(jsonEncode(response), 200);
      });

      final result = await IssueApiClient.getAllIssues(client, paginatedUrl);

      expect(result?.issueList?.length, 1);
      expect(result?.issueList?[0].id, 1);
      expect(result?.issueList?[0].title, 'Issue 1');
      expect(result?.issueList?[0].domain, 3);
      expect(result?.issueList?[0].screenshotsLink?.length, 1);
    });

    test('getAllIssues handles errors gracefully', () async {
      final paginatedUrl = 'https://www.bugheist.com/issues';
      final client = MockClient((request) async {
        // Create sample response of the HTTP call //
        final response = null;
        return http.Response(jsonEncode(response), 500);
      });

      final result = await IssueApiClient.getAllIssues(client, paginatedUrl);

      expect(result, isNull);
    });
  });
}
