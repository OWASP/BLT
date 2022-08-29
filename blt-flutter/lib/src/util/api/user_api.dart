import 'dart:convert';

import 'package:bugheist/src/util/endpoints/user_endpoints.dart';
import 'package:http/http.dart' as http;
import 'package:bugheist/src/models/user_model.dart';

class UserApiClient {
  UserApiClient._();

  static Future<void> getUserDetails(User user) async {
    http.Response? response;
    try {
      response = await http.get(
        Uri.parse(UserEndPoints.userData),
        headers: {
          "username": user.username!,
          "token": user.token!,
        },
      );
      print(response.body);
    } catch (e) {}
  }

  static Future<void> getUserInfo(User user) async {
    http.Response? response;
    try {
      String searchUrl = UserEndPoints.userInfo + "?search=${user.username}";
      response = await http.get(Uri.parse(searchUrl));
      var decodedResponse =
          jsonDecode(utf8.decode(response.bodyBytes))["results"][0];
      print(decodedResponse["issue_upvoted"].runtimeType);
      user.id = decodedResponse["user"]["id"];
      user.pfpLink = decodedResponse["user_avatar"];
      user.title = decodedResponse["title"];
      user.winning = decodedResponse["winnings"];
      user.description = decodedResponse["description"];
      user.following = decodedResponse["follows"].cast<int>();
      user.upvotedIssueId = decodedResponse["issue_upvoted"].cast<int>();
      user.savedIssueId = decodedResponse["issue_saved"].cast<int>();
    } catch (e) {
      print(e);
    }
  }
}
