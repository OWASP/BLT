import '../test_imports.dart';
import 'package:http/http.dart' as http;

void main() {
  setUp(() {
    currentUser = guestUser;
  });

  group("Companie Api's Test", () {
    test("Get All Companies", () async {
      final paginatedUrl = 'https://www.bugheist.com/company/';
      final dynamic mockResponse = {
        "count": 1,
        "next": null,
        "previous": null,
        "results": [
          {
            "id": 1,
            "name": "BLT Test",
            "description":
                "Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop p",
            "logo":
                "http://127.454.545.43:8000/media/company_logos/Screenshot_2023-11-17_184658_6qvsATu.png",
            "url": "http://www.bltTest.com",
            "email": "bltTest@gmail.com",
            "twitter": null,
            "facebook": null,
            "created": "2024-05-31T10:32:30.585653Z",
            "modified": "2024-06-11T14:33:37.271785Z",
            "is_active": false,
            "admin": 1,
            "subscription": null,
            "managers": [1]
          },
        ]
      };
      final client = MockClient((request) async {
        final response = mockResponse;
        return http.Response(jsonEncode(response), 200);
      });
      final result =
          await CompanyApiClient.getListOfCompanies(client, paginatedUrl);

      expect(result.length, 1);
      expect(result[0].id, 1);
      expect(result[0].companyName, "BLT Test");
      expect(result[0].email, "bltTest@gmail.com");
      expect(result[0].url, "http://www.bltTest.com");
    });

    test("Get Company by keyword", () async {
      final paginatedUrl = 'https://www.bugheist.com/company/';
      final dynamic mockResponse = {
        "count": 1,
        "next": null,
        "previous": null,
        "results": [
          {
            "id": 1,
            "name": "BLT Test",
            "description":
                "Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop p",
            "logo":
                "http://123.435.554.66:8000/media/company_logos/Screenshot_2023-11-17_184658_6qvsATu.png",
            "url": "http://www.bltTest.com",
            "email": "bltTest@gmail.com",
            "twitter": null,
            "facebook": null,
            "created": "2024-05-31T10:32:30.585653Z",
            "modified": "2024-06-11T14:33:37.271785Z",
            "is_active": false,
            "admin": 1,
            "subscription": null,
            "managers": [1]
          },
        ]
      };
      final client = MockClient((request) async {
        final response = mockResponse;
        return http.Response(jsonEncode(response), 200);
      });
      final result = await CompanyApiClient.getCompanyByKeyWord(
          client, paginatedUrl, "BLT Test");

      expect(result?.companyName, "BLT Test");
      expect(result?.email, "bltTest@gmail.com");
      expect(result?.url, "http://www.bltTest.com");
    });
  });
}
