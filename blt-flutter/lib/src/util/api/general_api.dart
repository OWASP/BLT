import 'dart:convert';
import 'package:blt/src/util/util_import.dart';
import 'package:http/http.dart' as http;

/// Class for accessing the general client.
class GeneralApiClient {
  GeneralApiClient._();

  /// Get general stats.
  static Future<Map<String, String>> getStats() async {
    http.Response? response;
    Map<String, String> m = {};
    try {
      response = await http.get(
        Uri.parse(GeneralEndPoints.stats),
      );
      if (response.statusCode == 200) {
        var decodedResponse = jsonDecode(response.body);
        m["bugs"] = '${decodedResponse["bugs"]}';
        m["users"] = '${decodedResponse["users"]}';
        m["hunts"] = '${decodedResponse["hunts"]}';
        m["domains"] = '${decodedResponse["domains"]}';
      }
    } catch (e) {
      print(e);
    }
    return m;
  }

  /// Check for duplicate issues for a given URL.
  static Future<Map<String, String>?> checkForDuplicate(String url) async {
    http.Response? response;
    Map<String, String>? m;
    Map<String, String> body = {
      "dom_url": url,
    };

    try {
      response = await http.post(
        Uri.parse(GeneralEndPoints.duplicateURL),
        body: body,
      );
      if (response.statusCode == 200) {
        var decodedResponse = jsonDecode(response.body);
        if (decodedResponse["found"]) {
          m = {};
          m["description"] = decodedResponse["issue"]["description"];
          m["id"] = decodedResponse["issue"]["id"].toString();
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
