import 'general_endpoints.dart';

/// Class to access the API's authentication endpoints.
class AuthEndPoints {
  AuthEndPoints._();

  static const String authBaseUrl = GeneralEndPoints.baseUrl + "auth/";

  static const String emailpasswordLogin = GeneralEndPoints.baseUrl + "authenticate/";

  static const String logout = authBaseUrl + "logout/";

  static const String register = authBaseUrl + "registration/";

  static const String reset = authBaseUrl + "password/reset/";

  static const String change = authBaseUrl + "password/change/";
}
