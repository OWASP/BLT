class AppUrl {
  static const String liveURL = "https://www.bugheist.com";
  static const String liveBaseURL = "https://www.bugheist.com/api/v1";
  static const String localBaseURL = "http://127.0.0.1:4000/api/v1";

  static const String baseURL = liveBaseURL;
  static const String login = liveURL + "/authenticate/";
  static const String register = baseURL + "/registration";
  static const String forgotPassword = baseURL + "/forgot-password";
}
