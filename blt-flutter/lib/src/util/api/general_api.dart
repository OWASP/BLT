import 'dart:convert';

import 'package:bugheist/src/util/endpoints/general_endpoints.dart';
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
}
