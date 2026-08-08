import 'package:http/http.dart' as http;

/// Resolves short-link redirects without following unbounded chains.
class UrlExpansionService {
  final http.Client _client;

  /// Creates a service with an optional injected HTTP client for testing.
  UrlExpansionService({http.Client? client}) : _client = client ?? http.Client();

  /// Expands a URL through a limited number of HEAD redirect hops.
  Future<String> expandUrl(String urlString, {int maxHops = 3}) async {
    String currentUrl = urlString;

    for (int hop = 0; hop < maxHops; hop++) {
      try {
        final uri = Uri.tryParse(currentUrl);
        if (uri == null || !uri.hasScheme) return currentUrl;

        final request = http.Request('HEAD', uri)..followRedirects = false;
        final streamedResponse = await _client.send(request).timeout(
          const Duration(milliseconds: 500),
        );

        final response = await http.Response.fromStream(streamedResponse);
        
        if (response.statusCode >= 300 && response.statusCode <= 308) {
          final location = response.headers['location'];
          if (location == null || location.isEmpty) return currentUrl;

          // Resolve relative redirect paths paths relative to current URI
          final redirectUri = uri.resolve(location);
          currentUrl = redirectUri.toString();
        } else {
          break; // Final destination reached
        }
      } catch (_) {
        break; // Return last successfully resolved URL on timeout or network failure
      }
    }
    return currentUrl;
  }
}
