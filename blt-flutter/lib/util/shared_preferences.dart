import '../data/user.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:async';

class UserPreferences {
  Future<bool> saveUser(User user) async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();

    prefs.setInt("id", user.id ?? 0);
    prefs.setString("username", user.username ?? "");
    prefs.setString("email", user.email ?? "");
    prefs.setString("token", user.token ?? "");

    return true;
  }

  Future<User> getUser() async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();

    int id = prefs.getInt("id")!;
    String username = prefs.getString("username")!;
    String email = prefs.getString("email")!;
    String token = prefs.getString("token")!;

    return User(
      id: id,
      username: username,
      email: email,
      token: token,
    );
  }

  void removeUser() async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    prefs.remove("email");
    prefs.remove("username");
    prefs.remove("id");
    prefs.remove("token");
  }

  Future<String> getToken(args) async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    String token = prefs.getString("token")!;
    return token;
  }
}
