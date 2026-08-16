/// HTTP response-header detector (parity subset of `src/detect/http_headers.py`).
library;

import 'package:http/http.dart' as http;

import 'normalize.dart';

String? _header(Map<String, String> headers, String name) {
  final want = name.toLowerCase();
  for (final entry in headers.entries) {
    if (entry.key.toLowerCase() == want) return entry.value;
  }
  return null;
}

bool _isHttps(String url) => url.trim().toLowerCase().startsWith('https://');

final _versionedServer = RegExp(r'\d+\.\d+');

List<DetectionFinding> scanHeaders(
  String url,
  Map<String, String> headers, {
  int status = 200,
}) {
  if (status >= 400) return [];

  final findings = <DetectionFinding>[];
  findings.addAll(_hsts(url, headers));
  findings.addAll(_csp(url, headers));
  findings.addAll(_clickjacking(url, headers));
  findings.addAll(_cookies(url, headers));

  if (_header(headers, 'X-Content-Type-Options') == null) {
    findings.add(DetectionFinding(
      ruleId: 'http.missing-x-content-type-options',
      severity: 'low',
      title: 'Missing X-Content-Type-Options header',
      target: url,
      locator: 'X-Content-Type-Options',
      remediation: 'Set X-Content-Type-Options: nosniff.',
    ));
  }

  if (_header(headers, 'Referrer-Policy') == null) {
    findings.add(DetectionFinding(
      ruleId: 'http.missing-referrer-policy',
      severity: 'info',
      title: 'Missing Referrer-Policy header',
      target: url,
      locator: 'Referrer-Policy',
      remediation: 'Set Referrer-Policy: strict-origin-when-cross-origin.',
    ));
  }

  for (final name in ['Server', 'X-Powered-By']) {
    final value = _header(headers, name);
    if (value != null && _versionedServer.hasMatch(value)) {
      findings.add(DetectionFinding(
        ruleId: 'http.server-version-disclosure',
        severity: 'low',
        title: '$name header discloses a software version',
        target: url,
        locator: name,
        evidence: {'value': value.length > 120 ? value.substring(0, 120) : value},
        remediation: 'Suppress or genericize the $name header.',
      ));
    }
  }

  return findings;
}

Iterable<DetectionFinding> _hsts(String url, Map<String, String> headers) sync* {
  if (!_isHttps(url)) return;
  final hsts = _header(headers, 'Strict-Transport-Security');
  if (hsts == null) {
    yield DetectionFinding(
      ruleId: 'http.missing-hsts',
      severity: 'high',
      title: 'Missing Strict-Transport-Security header',
      target: url,
      locator: 'Strict-Transport-Security',
      remediation: 'Send Strict-Transport-Security with a long max-age.',
    );
    return;
  }
  final match = RegExp(r'max-age\s*=\s*(\d+)', caseSensitive: false).firstMatch(hsts);
  final maxAge = match == null ? 0 : int.tryParse(match.group(1)!) ?? 0;
  if (maxAge < 15552000) {
    yield DetectionFinding(
      ruleId: 'http.weak-hsts-max-age',
      severity: 'medium',
      title: 'HSTS max-age is shorter than 180 days',
      target: url,
      locator: 'Strict-Transport-Security',
      evidence: {'max_age': maxAge},
      remediation: 'Raise max-age to at least 15552000 (180 days).',
    );
  }
}

Iterable<DetectionFinding> _csp(String url, Map<String, String> headers) sync* {
  final csp = _header(headers, 'Content-Security-Policy');
  if (csp == null) {
    yield DetectionFinding(
      ruleId: 'http.missing-csp',
      severity: 'high',
      title: 'Missing Content-Security-Policy header',
      target: url,
      locator: 'Content-Security-Policy',
      remediation: 'Add a restrictive Content-Security-Policy.',
    );
    return;
  }
  final lower = csp.toLowerCase();
  if (lower.contains('unsafe-inline') || lower.contains('unsafe-eval')) {
    yield DetectionFinding(
      ruleId: 'http.unsafe-csp-directive',
      severity: 'medium',
      title: 'CSP allows unsafe-inline or unsafe-eval',
      target: url,
      locator: 'Content-Security-Policy',
      remediation: 'Remove unsafe-inline / unsafe-eval where possible.',
    );
  }
}

bool _xfoProtective(String? value) {
  if (value == null) return false;
  final v = value.trim().toUpperCase();
  return v == 'DENY' || v == 'SAMEORIGIN';
}

bool _frameAncestorsProtective(String csp) {
  final match = RegExp(
    r'frame-ancestors\s+([^;]+)',
    caseSensitive: false,
  ).firstMatch(csp);
  if (match == null) return false;
  final token = match.group(1)!.trim().toLowerCase();
  return token == "'none'" || token == 'none';
}

Iterable<DetectionFinding> _clickjacking(
  String url,
  Map<String, String> headers,
) sync* {
  final xfo = _header(headers, 'X-Frame-Options');
  final csp = _header(headers, 'Content-Security-Policy') ?? '';
  if (_xfoProtective(xfo) || _frameAncestorsProtective(csp)) return;
  yield DetectionFinding(
    ruleId: 'http.missing-clickjacking-protection',
    severity: 'medium',
    title: 'Missing clickjacking protection',
    target: url,
    locator: 'X-Frame-Options / CSP frame-ancestors',
    remediation: "Prefer CSP frame-ancestors 'none' (or X-Frame-Options: DENY).",
  );
}

Iterable<DetectionFinding> _cookies(
  String url,
  Map<String, String> headers,
) sync* {
  // http package folds Set-Cookie; check any set-cookie style header values.
  for (final entry in headers.entries) {
    if (entry.key.toLowerCase() != 'set-cookie') continue;
    final cookie = entry.value;
    final lower = cookie.toLowerCase();
    final insecure = <String>[];
    if (_isHttps(url) && !lower.contains('secure')) insecure.add('Secure');
    if (!lower.contains('httponly')) insecure.add('HttpOnly');
    if (!lower.contains('samesite')) insecure.add('SameSite');
    if (insecure.isEmpty) continue;
    yield DetectionFinding(
      ruleId: 'http.insecure-cookie-flags',
      severity: 'medium',
      title: 'Cookie missing security flags (${insecure.join(', ')})',
      target: url,
      locator: 'Set-Cookie',
      evidence: {'missing': insecure},
      remediation: 'Add Secure, HttpOnly, and a SameSite policy to session cookies.',
    );
  }
}

/// Fetch [url] and return header findings (skips HTTP ≥400 like the Python pack).
Future<List<DetectionFinding>> scanUrlHeaders(
  String url, {
  http.Client? client,
}) async {
  final httpClient = client ?? http.Client();
  final owned = client == null;
  try {
    final response = await httpClient
        .get(Uri.parse(url))
        .timeout(const Duration(seconds: 20));
    return scanHeaders(url, response.headers, status: response.statusCode);
  } finally {
    if (owned) httpClient.close();
  }
}
