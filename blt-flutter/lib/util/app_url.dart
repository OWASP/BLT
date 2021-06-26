class AppUrl {
  static const String liveURL = "https://www.bugheist.com";
  static const String liveBaseURL = "https://www.bugheist.com/api/v1";
  static const String localBaseURL = "http://127.0.0.1:4000/api/v1";
  static const String testBaseURL = "http://127.0.0.1:8000";
  static const String liveStagingURL = "https://bugheist-staging.herokuapp.com";
  static const String baseURL = liveURL;
  static const String login = liveURL + "/auth/login/";
  static const String register = liveURL + "/auth/registration/";
  static const String forgotPassword = baseURL + "/forgot-password";
  static const String user = liveURL + "/auth/user/";
}
