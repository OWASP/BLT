/// Class to access the General endpoints.
class GeneralEndPoints {
  GeneralEndPoints._();

  // The app talks to the legacy Django app (blt-legacy), which serves /api/v1/*,
  // /authenticate/ and /auth/*. blt.owasp.org now redirects to the new site.
  static const String domain = "legacy.owaspblt.org/api/";

  static const String baseUrl = "https://legacy.owaspblt.org/";

  static const String apiBaseUrl = baseUrl + "api/v1/";

  static const String stats = apiBaseUrl + "stats/";

  static const String duplicateURL = apiBaseUrl + "urlcheck/";

  static const String contributors = apiBaseUrl + "contributors/";
}
