import 'package:http/http.dart' as http;
import '../test_imports.dart';

void main() {
  final mockRespUP = [
    {
      "id": 2,
      "name": "Mobile App Functionality",
      "url": "http://www.testhunt2.com",
      "prize": 5,
      "logo": "logos.png",
      "banner": "",
      "description":
          "Objective:\r\nIdentify and report functionality and performance issues in the organization's newly launched mobile app, ensuring it provides a smooth and bug-free user experience.\r\n\r\nScope:\r\n\r\nTest the app on various devices and operating systems (iOS and Android).\r\nCheck for UI/UX inconsistencies, crashes, and unexpected behaviors.\r\nEvaluate app performance under different network conditions.\r\nTest all features, including push notifications, in-app purchases, and data synchronization.\r\nTools:\r\n\r\nAppium\r\nTestComplete\r\nFirebase Test Lab\r\nRewards:\r\nParticipants will receive points for each valid bug report, which can be redeemed for gift cards, app credits, or exclusive access to future app updates and beta versions.",
      "starts_on": "2024-07-18T16:03:51Z",
      "end_on": "2024-07-27T16:03:54Z"
    },
    {
      "id": 1,
      "name": "API Security",
      "url": "http://hunt-new.com",
      "prize": 10,
      "logo": "logos.png",
      "banner": "banners.png",
      "description":
          "Objective:\r\nIdentify and report security vulnerabilities and functionality issues in the organization's public APIs to ensure they are secure, reliable, and perform as expected.\r\n\r\nScope:\r\n\r\nTest API endpoints for security vulnerabilities such as unauthorized access, data leakage, and input validation issues.\r\nEvaluate API performance under load and stress conditions.\r\nEnsure proper error handling and response codes.\r\nCheck for compliance with API documentation and expected functionality.\r\nTools:\r\n\r\nPostman\r\nInsomnia\r\nJMeter\r\nRewards:\r\nParticipants will be rewarded with bounty points based on the severity of the discovered issues. Top contributors will receive special recognition, monetary rewards, and opportunities for collaboration with the organization's development team.",
      "starts_on": "2024-07-09T09:06:24Z",
      "end_on": "2024-07-26T09:06:30Z"
    },
  ];
  final mockResp = [
    {
      "id": 1,
      "name": "Application Vulnerability",
      "url": "http://www.test.com",
      "prize": 2,
      "logo": "logos.jpg",
      "banner": "banners.png",
      "description":
          "Objective:\r\nIdentify and report security vulnerabilities in the organization's web application, focusing on potential threats such as SQL injection, cross-site scripting (XSS), and broken authentication.\r\n\r\nScope:\r\n\r\nTest all user input fields, including login forms, search bars, and data submission fields.\r\nAssess session management and authentication mechanisms.\r\nEvaluate access controls and permissions.\r\nCheck for outdated libraries and dependencies.\r\nTools:\r\n\r\nBurp Suite\r\nOWASP ZAP\r\nSQLMap\r\nRewards:\r\nParticipants will be rewarded based on the severity and impact of the discovered vulnerabilities. Rewards include cash prizes, recognition in the organization's Hall of Fame, and exclusive swag.",
      "starts_on": "2024-07-01T18:17:13Z",
      "end_on": "2024-04-02T18:17:16Z"
    }
  ];
  group("Bug Hunt API's Test", () {
    test("Get List of Upcomming Bug Hunts", () async {
      final client = MockClient((response) async {
        final response = mockRespUP;
        return http.Response(jsonEncode(response), 200);
      });
      final response =
          await BugHuntApiClient.getListOfUpcomingBugHunts(client: client);
      expect(response.length, 2);
      expect(response[0].name, "Mobile App Functionality");
      expect(response[0].url, "http://www.testhunt2.com");
      expect(response[0].prize, 5);
      expect(response[1].name, "API Security");
      expect(response[1].url, "http://hunt-new.com");
      expect(response[1].prize, 10);
    });

    test("Get List of Previous Bug Hunts", () async {
      final client = MockClient((response) async {
        final response = mockResp;
        return http.Response(jsonEncode(response), 200);
      });
      final response =
          await BugHuntApiClient.getListOfPreviousBugHunts(client: client);
      expect(response.length, 1);
      expect(response[0].name, "Application Vulnerability");
      expect(response[0].url, "http://www.test.com");
      expect(response[0].prize, 2);
    });
    test("Get List of Active Bug Hunts", () async {
      final String url = GeneralEndPoints.apiBaseUrl + "/hunt/?activeHunt=true";
      final client = MockClient((response) async {
        final response = mockResp;
        return http.Response(jsonEncode(response), 200);
      });
      final response = await client.get(Uri.parse(url));
      var decodedResponse = jsonDecode(utf8.decode(response.bodyBytes));
      List<BugHunt> bugHuntList = BugHunt.fromSnapshot(decodedResponse);
      expect(bugHuntList.length, 1);
      expect(bugHuntList[0].name, "Application Vulnerability");
      expect(bugHuntList[0].url, "http://www.test.com");
      expect(bugHuntList[0].prize, 2);
    });

    test("Get List of Active and Upcomming Bug Hunts", () async {
      final urlToResponseMap = {
        GeneralEndPoints.apiBaseUrl + "/hunt/?activeHunt=true": mockResp,
        GeneralEndPoints.apiBaseUrl + "/hunt/?upcomingHunt=true": mockRespUP,
      };

      // Create the mock client
      final client = MockClient((request) async {
        final response = urlToResponseMap[request.url.toString()];
        if (response != null) {
          return http.Response(jsonEncode(response), 200);
        } else {
          return http.Response('Not Found', 404);
        }
      });
      final response =
          await BugHuntApiClient.getListOfActiveBugHunts(client: client);
      expect(response.length, 3);
      expect(response[0].name, "Application Vulnerability");
      expect(response[0].url, "http://www.test.com");
      expect(response[0].prize, 2);
      expect(response[1].name, "Mobile App Functionality");
      expect(response[1].url, "http://www.testhunt2.com");
      expect(response[1].prize, 5);
      expect(response[2].name, "API Security");
      expect(response[2].url, "http://hunt-new.com");
      expect(response[2].prize, 10);
    });
  });
}
