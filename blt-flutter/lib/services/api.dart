import 'package:http/http.dart' as http;
import 'dart:convert';
import '../data/models.dart';

class ApiBackend {
  Future<DataModel> getApiData(String paginatedUrl) async {
    return http
        .get(
      Uri.parse(paginatedUrl),
    )
        .then((http.Response response) {
      final data = DataModel.fromJson(jsonDecode(response.body));
      return data;
    });
  }

  Future<List> getLeaderData(String paginatedUrl) async {
    return http
        .get(
      Uri.parse(paginatedUrl),
    )
        .then((http.Response response) {
      List<Leaders> leaders = (json.decode(response.body) as List)
          .map((data) => Leaders.fromJson(data))
          .toList();
      return leaders;
    });
  }
}
