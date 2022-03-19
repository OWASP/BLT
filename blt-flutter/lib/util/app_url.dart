class AppUrl {
  //static const String liveURL = "https://www.bugheist.com";
  static const String liveURL = "https://bugheist-staging.herokuapp.com";
  //static const String liveURL = "http://127.0.0.1:8000";
  //static const String liveURL = "http://127.0.0.1:4000";

  static const String baseURL = liveURL + "/api/v1";

  static const String login = baseURL + "/auth/login/";
  static const String forgotPassword = baseURL + "/forgot-password";
  static const String user = baseURL + "/auth/user/";

  static const String register = liveURL + "/auth/registration/";
}
