import 'dart:convert';
import 'package:blt/src/models/contributors_model.dart';
import 'package:http/http.dart' as http;

class GithubApis {
  GithubApis._();

  static Future<List<Contributors>> getContributors(
      String projectName, String ownerName) async {
    String searchUrl =
        "https://api.github.com/repos/$ownerName/$projectName/contributors";
    List<Contributors> contributors = [];
    try {
      var response = await http.get(
        Uri.parse(
          searchUrl,
        ),
      );
      var json = jsonDecode(response.body);
      contributors = Contributors.fromSnapshot(json);
    } catch (e) {
      print(e);
    }
    return contributors;
  }

  static Future<Contributors?> getContributorsInfoFromID(int id) async {
    String searchUrl = "https://api.github.com/user/$id";
    Contributors? contributors;
    try {
      var response = await http.get(
        Uri.parse(
          searchUrl,
        ),
      );
      var json = jsonDecode(response.body);
      print(json);
      contributors = Contributors.fromJson(json);
    } catch (e) {
      print(e);
    }
    return contributors;
  }
}
