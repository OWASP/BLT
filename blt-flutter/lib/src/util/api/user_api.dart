import 'package:blt/src/util/util_import.dart';
import 'package:http/http.dart' as http;

class UserApiClient {
  UserApiClient._();

  /// Get a user's details from username and token,
  /// used for currentUser.
  static Future<void> getUserDetails(http.Client client, User user) async {
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
  static Future<User?> getUserInfo(http.Client client, User user) async {
    try {
      String searchUrl = UserEndPoints.userInfo + "?search=${user.username}";
      var response = await client.get(
        Uri.parse(searchUrl),
        headers: {
          "Authorization": "Token ${user.token}",
        },
      );
      var decodedResponse =
          jsonDecode(utf8.decode(response.bodyBytes))["results"][0];
      // user.id = decodedResponse["user"]["id"];
      user.pfpLink = decodedResponse["user_avatar"];
      user.title = decodedResponse["title"];
      user.email = decodedResponse["email"];
      user.winning = decodedResponse["winnings"];
      user.description = decodedResponse["description"];
      user.following = decodedResponse["follows"] as List<int>? ?? [];
      user.likedIssueId = decodedResponse["issue_upvoted"] as List<int>? ?? [];
      user.savedIssueId = decodedResponse["issue_saved"] as List<int>? ?? [];
      user.totalScore = decodedResponse["total_score"];
      return user;
    } catch (e) {
      print(e);
    }
    return null;
  }

  static Future<void> updatePfp(XFile image, User user) async {
    try {
      String updateUrl = "${UserEndPoints.userInfo}${user.id}/";

      final uri = Uri.parse(updateUrl);
      var request = new http.MultipartRequest('PUT', uri);
      final httpImage = await http.MultipartFile.fromPath(
          'user_avatar', image.path,
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
