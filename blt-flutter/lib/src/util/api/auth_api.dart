import 'package:blt/src/util/util_import.dart';
import 'package:http/http.dart' as http;

/// Class for accessing the auth client.
class AuthApiClient {
  AuthApiClient._();

  /// Send login creds and get back the user token.
  static Future<User?> login(Map<String, String?> userCreds) async {
    http.Response? response;
    User? authenticatedUser;

    try {
      response = await http.post(
        Uri.parse(AuthEndPoints.emailpasswordLogin),
        body: userCreds,
      );
      if (response.statusCode == 200) {
        var decodedResponse = jsonDecode(response.body);
        authenticatedUser = User(
          username: userCreds["username"],
          token: decodedResponse["token"],
        );
      }
    } catch (e) {
      print(e);
    }
    return authenticatedUser;
  }

  /// Send a request for logging out the current session.
  static Future<bool> logout() async {
    http.Response? response;
    bool isLoggedOut = false;
    try {
      response = await http.post(
        Uri.parse(AuthEndPoints.logout),
        headers: {
          "Authorization": "Token ${currentUser!.token!}",
        },
      );
      print(response.statusCode);
      if (response.statusCode == 200) isLoggedOut = true;
    } catch (e) {
      print(e);
    }
    return isLoggedOut;
  }

  /// Request a new user signup on BLT.
  ///
  /// Accounts lived on the old BLT backend, which is offline while its data is
  /// migrated, so creating an account is not available yet.
  static Future<void> signup(
    String username,
    String email,
    String password,
    BuildContext parentContext,
  ) async {
    showNotAvailableYet(parentContext, "Creating an account");
  }

  /// Request a password reset email. Not available yet (see [signup]).
  static Future<void> resetPassword(String email, BuildContext context) async {
    showNotAvailableYet(context, "Password reset");
  }

  static Future<bool> checkPassword(String password) async {
    http.Response? response;
    try {
      response = await http.post(
        Uri.parse(AuthEndPoints.emailpasswordLogin),
        body: {
          "username": currentUser!.username,
          "password": password,
        },
      );
      print(response.body);
      return response.statusCode == 200;
    } catch (e) {}
    return false;
  }

  /// Change the password of the logged in user.
  static Future<void> changePassword(
      String newPassword1, String newPassword2, BuildContext context) async {
    http.Response? response;
    try {
      response = await http.post(
        Uri.parse(AuthEndPoints.change),
        body: {
          "new_password1": newPassword1,
          "new_password2": newPassword2,
        },
        headers: {
          "Authorization": "Token ${currentUser!.token!}",
        },
      );
      print(response.body);
      if (response.statusCode == 200) {
        SnackBar sentSnack = SnackBar(
          content: Text("Password changed successfully"),
        );
        ScaffoldMessenger.of(context).showSnackBar(sentSnack);
      } else {
        var decodedResponse = jsonDecode(response.body);
        SnackBar sentSnack = SnackBar(
          content: Text(decodedResponse["new_password2"][0]),
        );
        ScaffoldMessenger.of(context).showSnackBar(sentSnack);
      }
    } catch (e) {}
  }

  // Send a request to delete the current User.
  static Future<bool> delete() async {
    bool isDeleted = false;
    print(currentUser!.token);
    try {
      var response = await http.delete(
        Uri.parse(GeneralEndPoints.baseUrl + "auth/" + "delete"),
        headers: {
          "Authorization": "Token ${currentUser!.token!}",
        },
      );
      var json = jsonDecode(response.body);
      isDeleted = json['success'];
    } catch (e) {
      print(e);
    }
    return isDeleted;
  }
}
