/// Class to access the General endpoints.
class GeneralEndPoints {
  GeneralEndPoints._();

  static const String domain = "www.owasp.org/BLT/";

  static const String baseUrl = "https://www.owasp.org/BLT/";

  static const String apiBaseUrl = baseUrl + "api/v1/";

  static const String stats = apiBaseUrl + "stats/";

  static const String duplicateURL = apiBaseUrl + "urlcheck/";

  static const String contributors = apiBaseUrl + "contributors/";
}
