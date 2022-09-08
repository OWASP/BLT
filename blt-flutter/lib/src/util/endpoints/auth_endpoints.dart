/// Class to access the API's authentication endpoints.
class AuthEndPoints {
  AuthEndPoints._();

  static const String baseUrl = "https://www.bugheist.com/auth/";

  static const String emailpasswordLogin = baseUrl + "login/";

  static const String logout = baseUrl + "logout/";

  static const String register = baseUrl + "registration/";

  static const String reset = baseUrl + "password/reset/";
}
