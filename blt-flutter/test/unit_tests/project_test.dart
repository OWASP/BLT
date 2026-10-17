import 'package:blt/src/util/api/project_apis.dart';
import 'package:http/http.dart' as http;
import '../test_imports.dart';

void main() {
  group("Project Api's Test", () {
    test("get all projects", () async {
      final dynamic mockResponse = {
        "count": 1,
        "projects": [
          {
            "id": 13,
            "name": "TestProject",
            "slug": "testproject",
            "description": "Test Project",
            "github_url": "https://github.com/Test/test",
            "wiki_url": "",
            "homepage_url": "",
            "logo_url": "https://test.org/www-test-test/test/test/test.png",
            "created": "2024-07-16T19:08:44.846535Z",
            "modified": "2024-08-02T14:53:41.131125Z",
            "contributors": [
              {
                "id": 00,
                "name": "cont1",
                "github_id": 000111,
                "github_url": "https://github.com/cont1",
                "avatar_url": "https://avatars.githubusercontent.com/u/cont1",
                "contributor_type": "User",
                "contributions": 2,
                "created": "2024-08-04T19:03:52.956106Z"
              },
              {
                "id": 01,
                "name": "bot[bot]",
                "github_id": 002200,
                "github_url": "https://github.com/BOT/bot",
                "avatar_url": "https://avatars.githubusercontent.com/in/bot",
                "contributor_type": "Bot",
                "contributions": 1,
                "created": "2024-08-04T19:03:52.956106Z"
              },
            ]
          }
        ]
      };
      final client = MockClient((request) async {
        final response = mockResponse;
        return http.Response(jsonEncode(response), 200);
      });
      final result = await ProjectAPiClient.getAllProjects(testClient: client);
      expect(result?.length, 1);
      expect(result?[0].contributors?.length, 2);
      expect(result?[0].name, 'TestProject');
      expect(result?[0].contributors?[0].name, "cont1");
      expect(result?[0].contributors?[0].contributions, 2);
      expect(result?[0].contributors?[1].name, "bot[bot]");
      expect(result?[0].contributors?[1].contributions, 1);
    });
  });
}
