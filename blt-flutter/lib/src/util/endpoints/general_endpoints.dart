/// Class to access the General endpoints.
class GeneralEndPoints {
  GeneralEndPoints._();

  // ---- The BLT API (blt-api), used for bug reports, bug search and stats ----

  static const String bltApiBaseUrl = "https://api.owaspblt.org";

  /// The BLT API's public shared key (PUBLIC_BLT_API_KEY in
  /// blt-api/src/libs/api_key.py). It is published on purpose for clients
  /// and is not a secret; user-owned keys are not supported by the app yet.
  static const String bltApiKey =
      "f5537412b459790f9fa1cc47b862b9c7016471957178dc9b161d59355b6fd051";

  static const Map<String, String> bltApiHeaders = {
    "X-BLT-API-Key": bltApiKey,
    "Content-Type": "application/json",
    "Accept": "application/json",
  };

  static const String bugs = bltApiBaseUrl + "/bugs";
  static const String bugSearch = bltApiBaseUrl + "/bugs/search";
  static const String stats = bltApiBaseUrl + "/stats";

  /// The new BLT website.
  static const String newSiteUrl = "https://next.owaspblt.org/";

  // ---- The old Django API ----
  //
  // /api/v1/*, /authenticate/ and /auth/* belonged to the old BLT app
  // (blt-legacy), which is offline while its data is migrated. Features that
  // still use these addresses (sign-in, leaderboards, companies, bug hunts,
  // profiles, likes and flags) are not available yet; the app says so
  // (see util/migration_notice.dart) instead of pretending to work.
  static const bool oldApiAvailable = false;

  static const String domain = "next.owaspblt.org/";

  static const String baseUrl = newSiteUrl;

  static const String apiBaseUrl = baseUrl + "api/v1/";

  static const String duplicateURL = apiBaseUrl + "urlcheck/";

  static const String contributors = apiBaseUrl + "contributors/";
}
