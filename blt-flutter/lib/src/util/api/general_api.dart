import 'package:blt/src/util/util_import.dart';
import 'package:http/http.dart' as http;

/// Class for accessing the general client.
class GeneralApiClient {
  GeneralApiClient._();

  /// Get general stats from the BLT API (GET /stats).
  static Future<Map<String, String>> getStats() async {
    http.Response? response;
    Map<String, String> m = {};
    try {
      response = await http.get(
        Uri.parse(GeneralEndPoints.stats),
        headers: GeneralEndPoints.bltApiHeaders,
      );
      if (response.statusCode == 200) {
        var counts = jsonDecode(utf8.decode(response.bodyBytes))["data"] ?? {};
        m["bugs"] = '${counts["bugs"] ?? 0}';
        m["users"] = '${counts["users"] ?? 0}';
        m["hunts"] = '${counts["hunts"] ?? 0}';
        m["domains"] = '${counts["domains"] ?? 0}';
      }
    } catch (e) {
      print(e);
    }
    return m;
  }

  /// Check the BLT API for an earlier report on the same URL
  /// (GET /bugs/search?q=<url>). Returns its description and id, or null.
  static Future<Map<String, String>?> checkForDuplicate(String url) async {
    http.Response? response;
    Map<String, String>? m;

    try {
      response = await http.get(
        Uri.parse(GeneralEndPoints.bugSearch).replace(
          queryParameters: {"q": url.trim(), "limit": "1"},
        ),
        headers: GeneralEndPoints.bltApiHeaders,
      );
      if (response.statusCode == 200) {
        var decodedResponse = jsonDecode(utf8.decode(response.bodyBytes));
        List<dynamic> found = decodedResponse["data"] ?? [];
        if (found.isNotEmpty) {
          m = {};
          m["description"] = '${found[0]["description"] ?? ""}';
          m["id"] = '${found[0]["id"]}';
        }
      }
    } catch (e) {
      print(e);
    }
    return m;
  }

  /// Get contributors data.
  static Future<List<Map<String, String>>> getContributors() async {
    http.Response? response;
    List<Map<String, String>> m = [];
    try {
      response = await http.get(
        Uri.parse(GeneralEndPoints.contributors),
      );
      if (response.statusCode == 200) {
        var decodedResponse = jsonDecode(response.body);
        for (var contributor in decodedResponse["contributors"]) {
          m.add({
            "id": contributor["id"].toString(),
            "img": contributor["img"],
            "name": contributor["name"],
            "repository": contributor["repository"],
            "short_description": contributor["short_description"],
            "long_description": contributor["long_description"],
            "location": contributor["location"],
            "twitter": contributor["twitter"],
            "linkedin": contributor["linkedin"],
            "website": contributor["website"],
            "bch_addr": contributor["bch_addr"]
          });
        }
      }
    } catch (e) {
      print(e);
    }
    return m;
  }
}
