import 'dart:math' as math;

/// Extracts normalized lexical phishing indicators from a URL.
class UrlSignalExtractor {
  /// Produces bounded feature scores from the provided URI.
  Map<String, double> extract(Uri uri) {
    final host = uri.host.toLowerCase();
    final entropy = _calculateShannonEntropy(host);

    return {
      'entropy': (entropy / 5.0).clamp(0.0, 1.0),
      'suspicious_tokens': _hasSuspiciousTokens(uri) ? 0.7 : 0.0,
      'risky_tld': _hasRiskyTld(host) ? 1.0 : 0.0,
      'query_anomaly': (uri.query.length / 120).clamp(0.0, 1.0),
    };
  }

  double _calculateShannonEntropy(String text) {
    if (text.isEmpty) return 0.0;
    final frequencies = <String, int>{};
    
    for (var i = 0; i < text.length; i++) {
      final char = text[i];
      frequencies[char] = (frequencies[char] ?? 0) + 1;
    }

    var entropy = 0.0;
    for (final count in frequencies.values) {
      final p = count / text.length;
      entropy -= p * (math.log(p) / math.ln2);
    }
    return entropy;
  }

  bool _hasSuspiciousTokens(Uri uri) {
    final pattern = RegExp(r'(verify|secure|login|account|banking|update)');
    return pattern.hasMatch(uri.toString().toLowerCase());
  }

  bool _hasRiskyTld(String host) {
    final pattern = RegExp(r'\.(zip|click|top|xyz|link)$');
    return pattern.hasMatch(host);
  }
}
