import '../test_imports.dart';
import 'package:http/http.dart' as http;

void main() {
  setUp(() {
    currentUser = guestUser;
  });
  group("LeaderBoard Api's Test", () {
    test("Get Leaders Api Test", () async {
      final paginatedUrl = LeaderboardEndpoints.globalLeaderboard;
      final mockResponse = [
        {
          "rank": 1,
          "id": 1,
          "User": "test1",
          "score": {"total_score": 612},
          "image": {"user_avatar": "avatarstest1"},
          "title_type": {"title": 3},
          "follows": {"follows": null},
          "savedissue": {"issue_saved": null}
        },
        {
          "rank": 2,
          "id": 919,
          "User": "test2",
          "score": {"total_score": 442},
          "image": {"user_avatar": "avatarstest2"},
          "title_type": {"title": 3},
          "follows": {"follows": null},
          "savedissue": {"issue_saved": null}
        },
      ];
      final client = MockClient((request) async {
        return http.Response(jsonEncode(mockResponse), 200);
      });
      final responseLeaders =
          await LeaderboardApiClient.getLeaderData(client, paginatedUrl);
      expect(responseLeaders.length, 2);
      expect(responseLeaders[0].user, "test1");
      expect(responseLeaders[0].rank, 1);
      expect(responseLeaders[1].user, "test2");
      expect(responseLeaders[1].rank, 2);
    });

    test("Get Monthly Leaders Api Test", () async {
      final paginatedUrl = LeaderboardEndpoints.globalLeaderboard;
      final mockResponse = {
        "count": 2,
        "results": [
          {
            "rank": 1,
            "id": 1,
            "User": "test1",
            "score": {"total_score": 612},
            "image": {"user_avatar": "avatar/test1"},
            "title_type": {"title": 3},
            "follows": {"follows": null},
            "savedissue": {"issue_saved": null}
          },
          {
            "rank": 2,
            "id": 919,
            "User": "test2",
            "score": {"total_score": 442},
            "image": {"user_avatar": "avatar/test2"},
            "title_type": {"title": 3},
            "follows": {"follows": null},
            "savedissue": {"issue_saved": null}
          }
        ]
      };
      final client = MockClient((request) async {
        return http.Response(jsonEncode(mockResponse), 200);
      });
      final responseLeader = await LeaderboardApiClient.getMonthlyLeaderData(
          client, paginatedUrl, 2023, 12);
      expect(responseLeader.leaderList?.length, 2);
      expect(responseLeader.leaderList?[0].user, "test1");
      expect(responseLeader.leaderList?[0].rank, 1);
      expect(responseLeader.leaderList?[1].user, "test2");
      expect(responseLeader.leaderList?[1].rank, 2);
    });

    test("Get Scoreboard Api Test", () async {
      final paginatedUrl = LeaderboardEndpoints.companyScoreboard;
      final mockResponse = {
        "count": 2,
        "next": null,
        "previous": null,
        "results": [
          {
            "id": 1,
            "admin_id": 1198,
            "name": "test.com",
            "logo": "test-logo.jpg",
            "url": "www.test.com",
            "email": "",
            "twitter": "",
            "facebook": "",
            "created": "2023-11-24T13:10:02.149368Z",
            "modified": "2023-11-27T13:20:52.155917Z",
            "subscription_id": null,
            "is_active": true,
            "issue_count": 10
          },
          {
            "id": 2,
            "admin_id": 1198,
            "name": "test2.com",
            "logo": "test2-logo.jpg",
            "url": "www.test2.com",
            "email": "",
            "twitter": "",
            "facebook": "",
            "created": "2023-11-24T13:30:02.149448Z",
            "modified": "2023-11-25T13:30:02.154517Z",
            "subscription_id": null,
            "is_active": true,
            "issue_count": 5
          }
        ]
      };
      final client = MockClient((request) async {
        return http.Response(jsonEncode(mockResponse), 200);
      });
      final response =
          await LeaderboardApiClient.getScoreBoardData(client, paginatedUrl);
      expect(response.length, 2);
      expect(response[0].companyName, "test.com");
      expect(response[0].issueCount, 10);
      expect(response[1].companyName, "test2.com");
      expect(response[1].issueCount, 5);
    });
  });
}
