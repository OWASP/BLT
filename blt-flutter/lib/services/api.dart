import 'package:bugheist/models/company_model.dart';
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
      final data =
          DataModel.fromJson(jsonDecode(utf8.decode(response.bodyBytes)));
      return data;
    });
  }

  Future<List> getLeaderData(String paginatedUrl) async {
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

  Future<List> getScoreBoardData(String paginatedUrl) async {
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
