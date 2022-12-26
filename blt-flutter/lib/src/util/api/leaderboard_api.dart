import 'package:bugheist/src/models/company_model.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../../models/leader_model.dart';

class LeaderboardApiClient {
  LeaderboardApiClient._();

  static Future<List<Leaders>> getLeaderData(String paginatedUrl) async {
    return http
        .get(
      Uri.parse(paginatedUrl),
    )
        .then((http.Response response) {
      List<Leaders> leaders =
          (json.decode(utf8.decode(response.bodyBytes)) as List)
              .map((data) => Leaders.fromJson(data))
              .toList();
      return leaders;
    });
  }

  static Future<List<Company>> getScoreBoardData(String paginatedUrl) async {
    return http
        .get(
      Uri.parse(paginatedUrl),
    )
        .then((http.Response response) {
      List<Company> companies =
          (json.decode(utf8.decode(response.bodyBytes)) as List)
              .map((data) => Company.fromJson(data))
              .toList();
      return companies;
    });
  }
}
