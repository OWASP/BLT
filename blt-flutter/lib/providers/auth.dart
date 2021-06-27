import 'dart:async';
import 'dart:convert';
//import 'dart:io';

import 'package:flutter/material.dart';
import 'package:http/http.dart';
import '../data/user.dart';
import '../util/app_url.dart';
import '../util/shared_preferences.dart';

enum Status {
  NotLoggedIn,
  NotRegistered,
  LoggedIn,
  Registered,
  Authenticating,
  Registering,
  LoggedOut
}

class AuthProvider with ChangeNotifier {
  Status _loggedInStatus = Status.NotLoggedIn;
  Status _registeredInStatus = Status.NotRegistered;

  Status get loggedInStatus => _loggedInStatus;
  Status get registeredInStatus => _registeredInStatus;

  Future<Map<String, dynamic>> login(
      String username, String password, String email) async {
    var result;

    final Map<String, dynamic> loginData = {
      'username': username,
      'password': password,
      'email': email,
    };

    _loggedInStatus = Status.Authenticating;
    notifyListeners();

    Response response = await post(
      Uri.parse(AppUrl.login),
      body: json.encode(loginData),
      headers: {'Content-Type': 'application/json'},
    );

    if (response.statusCode == 200 || response.statusCode == 201) {
      final Map<String, dynamic> responseData = json.decode(response.body);
      var accessToken = responseData['key'];
      Response responseUser = await post(
        Uri.parse(AppUrl.user),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Token ' + accessToken,
        },
      );
      final Map<String, dynamic> userData = json.decode(responseUser.body);
      User authUser = User.fromJson(userData, accessToken);

      UserPreferences().saveUser(authUser);
      _loggedInStatus = Status.LoggedIn;
      notifyListeners();

      result = {'status': true, 'message': 'Successful', 'user': authUser};
    } else {
      _loggedInStatus = Status.NotLoggedIn;
      notifyListeners();
      result = {
        'status': false,
        'message': json.decode(response.body)['non_field_errors']
      };
    }
    return result;
  }

  Future<Map<String, dynamic>> user(String key) async {
    Response response = await post(
      Uri.parse(AppUrl.user),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Token ' + key,
      },
    );
    final Map<String, dynamic> userData = json.decode(response.body);
    return userData;
  }

  Future<Map<String, dynamic>> register(
    String email,
    String username,
    String password,
    String passwordConfirmation,
  ) async {
    var result;
    final Map<String, dynamic> registrationData = {
      'email': email,
      'username': username,
      'password1': password,
      'password2': passwordConfirmation
    };
    Response response = await post(
      Uri.parse(AppUrl.register),
      body: json.encode(registrationData),
      headers: {'Content-Type': 'application/json'},
    );
    if (response.statusCode == 200 || response.statusCode == 201) {
      result = {
        'status': true,
        'message': 'Successfully registered',
      };
    } else {
      result = {
        'status': false,
        'message': "There is some problem with Registration!!",
        'username': json.decode(response.body)['username'],
        'email': json.decode(response.body)['email'],
      };
    }
    return result;
  }
}
