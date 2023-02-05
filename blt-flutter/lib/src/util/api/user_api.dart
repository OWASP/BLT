import 'dart:convert';
import 'dart:io';

import 'package:bugheist/src/util/endpoints/user_endpoints.dart';
import 'package:http/http.dart' as http;
import 'package:bugheist/src/models/user_model.dart';
import 'package:image_picker/image_picker.dart';
import 'package:async/async.dart';

class UserApiClient {
  UserApiClient._();

  /// Get a user's details from username and token,
  /// used for currentUser.
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

  /// Get a user's details, queried
  /// against a [user]'s username.
  static Future<void> getUserInfo(User user) async {
    http.Response? response;
    try {
      String searchUrl = UserEndPoints.userInfo + "?search=${user.username}";
      response = await http.get(
        Uri.parse(searchUrl),
        headers: {
          "Authorization": "Token ${user.token}",
        },
      );
      var decodedResponse =
          jsonDecode(utf8.decode(response.bodyBytes))["results"][0];
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

  static Future<void> updatePfp(XFile image, User user) async {
    try {
      String updateUrl = "${UserEndPoints.userInfo}${user.id}/";

      final uri = Uri.parse(updateUrl);
      var request = new http.MultipartRequest('PUT', uri);
      final httpImage = await http.MultipartFile.fromPath('user_avatar', image.path,
          filename: image.name);
      request.files.add(httpImage);
      request.headers.addAll(
        {
          "Authorization": "Token ${user.token}",
        },
      );
      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);
      var decodedResponse = jsonDecode(utf8.decode(response.bodyBytes));
      user.pfpLink = decodedResponse["user_avatar"];
    } catch (e) {
      print(e);
    }
  }
}
