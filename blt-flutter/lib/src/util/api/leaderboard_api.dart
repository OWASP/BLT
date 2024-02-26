import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:blt/src/util/util_import.dart';

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

  static Future<LeaderData> getMonthlyLeaderData(
      String paginatedUrl, int? year, int? month) async {
    final queryParams = {
      "filter": '1',
      "year": year.toString(),
      "month": month.toString(),
    };
    print(Uri.parse(paginatedUrl).replace(queryParameters: queryParams));
    return http
        .get(
      Uri.parse(paginatedUrl).replace(queryParameters: queryParams),
    )
        .then((http.Response response) {
      List<Leaders> leaderList = [];
      var decodedResponse = jsonDecode(utf8.decode(response.bodyBytes));
      decodedResponse["results"].forEach((element) {
        leaderList.add(Leaders.fromJson(element));
      });
      LeaderData leaderData = LeaderData(
        count: decodedResponse["count"],
        nextQuery: decodedResponse["next"],
        previousQuery: decodedResponse["previous"],
        leaderList: leaderList,
      );
      return leaderData;
    });
  }

  static Future<LeaderData> getMoreMonthlyLeaders(String? nextUrl) async {
    return http
        .get(
      Uri.parse(nextUrl!),
    )
        .then((http.Response response) {
      List<Leaders> leaderList = [];
      var decodedResponse = jsonDecode(utf8.decode(response.bodyBytes));
      decodedResponse["results"].forEach((element) {
        leaderList.add(Leaders.fromJson(element));
      });
      LeaderData leaderData = LeaderData(
        count: decodedResponse["count"],
        nextQuery: decodedResponse["next"],
        previousQuery: decodedResponse["previous"],
        leaderList: leaderList,
      );
      return leaderData;
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
