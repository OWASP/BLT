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
}
