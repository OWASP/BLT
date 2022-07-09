import 'dart:convert';

import 'package:bugheist/models/user_model.dart';
import 'package:bugheist/util/endpoints/auth_endpoints.dart';
import 'package:http/http.dart' as http;

class AuthApiClient {
  AuthApiClient._();

  static Future<User?> login(Map<String, String?> userCreds) async {
    http.Response? response;
    User? authenticatedUser;

    try {
      response = await http.post(
        Uri.parse(AuthEndPoints.emailpasswordLogin),
        body: userCreds,
      );
      var decodedResponse = jsonDecode(response.body);
      authenticatedUser = User(
        email: userCreds["email"],
        username: userCreds["username"],
        token: decodedResponse["token"],
      );
    } catch (e) {
      print(e);
    }
    return authenticatedUser;
  }

  static Future<bool> logout() async {
    http.Response? response;
    bool isLoggedOut = false;
    try {
      response = await http.get(
        Uri.parse(AuthEndPoints.logout),
      );
      if (response.statusCode == 200) isLoggedOut = true;
    } catch (e) {}
    return isLoggedOut;
  }

  static Future signup() async {}
}
