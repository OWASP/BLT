/// Class to access the API's authentication endpoints.
class AuthEndPoints {
  AuthEndPoints._();

  static const String baseUrl = "https://www.bugheist.com/";

  static const String baseUrl2 = "https://www.bugheist.com/auth/";

  static const String emailpasswordLogin = baseUrl + "authenticate/";

  static const String logout = baseUrl2 + "logout/";

  static const String register = baseUrl2 + "registration/";

  static const String reset = baseUrl2 + "password/reset/";
}
