import 'package:http/http.dart' as http;
import 'package:blt/src/util/util_import.dart';

class LeaderboardApiClient {
  LeaderboardApiClient._();

  static Future<List<Leaders>> getLeaderData(
      http.Client client, String paginatedUrl) async {
    return client
        .get(
      Uri.parse(paginatedUrl),
    )
        .then((var response) {
      List<Leaders> leaders =
          (json.decode(utf8.decode(response.bodyBytes)) as List)
              .map((data) => Leaders.fromJson(data))
              .toList();
      return leaders;
    });
  }

  static Future<LeaderData> getMonthlyLeaderData(
      http.Client client, String paginatedUrl, int? year, int? month) async {
    final queryParams = {
      "filter": '1',
      "year": year.toString(),
      "month": month.toString(),
    };
    // print(Uri.parse(paginatedUrl).replace(queryParameters: queryParams));
    return client
        .get(
      Uri.parse(paginatedUrl).replace(queryParameters: queryParams),
    )
        .then((var response) {
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
        .then((var response) {
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

  static Future<List<Company>> getScoreBoardData(
      http.Client client, String? paginatedUrl) async {
    var req = await client.get(
      Uri.parse(paginatedUrl!),
    );
    var response = jsonDecode(req.body);
    return (response["results"] as List)
        .map((data) => Company.fromJson(data))
        .toList();
  }
}
