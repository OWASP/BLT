import 'dart:convert';

import 'package:bugheist/src/models/user_model.dart';
import 'package:bugheist/src/util/endpoints/auth_endpoints.dart';
import 'package:flutter/material.dart';
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

  static Future<bool> logout() async {
    http.Response? response;
    bool isLoggedOut = false;
    try {
      response = await http.post(
        Uri.parse(AuthEndPoints.logout),
      );
      print(response.statusCode);
      if (response.statusCode == 200) isLoggedOut = true;
    } catch (e) {
      print(e);
    }
    return isLoggedOut;
  }

  static Future<void> signup(
    String username,
    String email,
    String password,
    BuildContext parentContext,
  ) async {
    http.Response? response;

    try {
      response = await http.post(
        Uri.parse(AuthEndPoints.register),
        body: {
          "username": username,
          "email": email,
          "password1": password,
          "password2": password,
        },
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        SnackBar sentSnack = SnackBar(
          duration: const Duration(seconds: 6),
          content: Text(
            "Email Confirmation mail sent, please verify your email to login",
          ),
        );
        ScaffoldMessenger.of(parentContext).showSnackBar(sentSnack);
        await Future.delayed(const Duration(seconds: 6));
        Navigator.of(parentContext).pop();
      } else {
        ScaffoldMessenger.of(parentContext).clearSnackBars();
        Map responseMap = jsonDecode(utf8.decode(response.bodyBytes));
        String errorString = "";
        responseMap.forEach((key, value) {
          errorString +=
              "$key : ${value.toString().substring(1, value.toString().length - 1)} \n";
        });
        SnackBar errorSnack = SnackBar(
          content: Text("Error!\n ${errorString}"),
        );
        ScaffoldMessenger.of(parentContext).showSnackBar(errorSnack);
      }
    } catch (e) {
      print(e);
    }
  }

  static Future<void> resetPassword(String email, BuildContext context) async {
    http.Response? response;
    try {
      response = await http.post(
        Uri.parse(AuthEndPoints.reset),
        body: {
          "email": email,
        },
      );
      print(response.body);
      if (response.statusCode == 200) {
        SnackBar sentSnack = SnackBar(
          content: Text("Email sent successfully"),
        );
        ScaffoldMessenger.of(context).showSnackBar(sentSnack);
        await Future.delayed(const Duration(seconds: 3));
        Navigator.of(context).pop();
      }
    } catch (e) {}
  }
}
