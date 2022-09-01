/// Class for API endpoints needed to access users data on BugHeist.
class UserEndPoints {
  UserEndPoints._();

  static const String baseUrl = "https://www.bugheist.com/";

  static const String userInfo = baseUrl + "api/v1/profile/";

  static const String userData = baseUrl + "api/v1/profile/auth/user/";
}
