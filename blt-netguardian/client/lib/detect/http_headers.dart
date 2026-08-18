/// HTTP response-header detector — parity with `src/detect/http_headers.py`.
library;

import 'dart:convert';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;

import 'normalize.dart';

const minHstsMaxAge = 15552000;

String? _header(Map<String, String> headers, String name) {
  final want = name.toLowerCase();
  for (final entry in headers.entries) {
    if (entry.key.toLowerCase() == want) return entry.value;
  }
  return null;
}

bool _isHttps(String url) => url.trim().toLowerCase().startsWith('https://');

final _maxAge = RegExp(r'max-age\s*=\s*(\d+)', caseSensitive: false);
final _versionedServer = RegExp(r'[0-9]+\.[0-9]+');
final _frameAncestors = RegExp(
  r'(?:^|;)\s*frame-ancestors\s+([^;]+)',
  caseSensitive: false,
);
const _protectiveXfo = {'deny', 'sameorigin'};

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
        evidence: {
          'value': value.length > 120 ? value.substring(0, 120) : value,
        },
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
      remediation:
          'Send Strict-Transport-Security with max-age of at least 15552000.',
    );
    return;
  }
  final match = _maxAge.firstMatch(hsts);
  final maxAge = match == null ? 0 : int.tryParse(match.group(1)!) ?? 0;
  if (maxAge < minHstsMaxAge) {
    yield DetectionFinding(
      ruleId: 'http.weak-hsts-max-age',
      severity: 'medium',
      title: 'Strict-Transport-Security max-age is too short',
      target: url,
      locator: 'Strict-Transport-Security',
      evidence: {'max_age': maxAge, 'minimum': minHstsMaxAge},
      remediation: 'Raise max-age to at least $minHstsMaxAge seconds.',
    );
  }
}

Iterable<DetectionFinding> _csp(String url, Map<String, String> headers) sync* {
  final csp = _header(headers, 'Content-Security-Policy');
  if (csp == null) {
    yield DetectionFinding(
      ruleId: 'http.missing-csp',
      severity: 'medium',
      title: 'Missing Content-Security-Policy header',
      target: url,
      locator: 'Content-Security-Policy',
      remediation:
          'Add a Content-Security-Policy restricting script and object sources.',
    );
    return;
  }
  final lower = csp.toLowerCase();
  final unsafe = [
    for (final d in ['unsafe-inline', 'unsafe-eval'])
      if (lower.contains(d)) d,
  ];
  if (unsafe.isNotEmpty) {
    yield DetectionFinding(
      ruleId: 'http.unsafe-csp-directive',
      severity: 'medium',
      title: 'Content-Security-Policy allows unsafe script execution',
      target: url,
      locator: 'Content-Security-Policy',
      evidence: {'directives': unsafe},
      remediation:
          'Remove unsafe-inline/unsafe-eval; use nonces or hashes instead.',
    );
  }
}

bool _xfoProtective(String? value) {
  if (value == null) return false;
  final token = value.trim().split(RegExp(r'\s+')).first.toLowerCase();
  return _protectiveXfo.contains(token);
}

bool _frameAncestorsProtective(String csp) {
  final match = _frameAncestors.firstMatch(csp);
  if (match == null) return false;
  final sources = match.group(1)!.split(RegExp(r'\s+'));
  if (sources.isEmpty) return false;
  return !sources.any((src) => src.replaceAll(RegExp(r'''['"]'''), '') == '*');
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
    title: 'No clickjacking protection (X-Frame-Options or frame-ancestors)',
    target: url,
    locator: 'X-Frame-Options',
    remediation:
        "Set X-Frame-Options: DENY or a CSP frame-ancestors directive that is not '*'.",
  );
}

List<String> _iterSetCookies(Map<String, String> headers) {
  final values = <String>[];
  for (final entry in headers.entries) {
    if (entry.key.toLowerCase() != 'set-cookie') continue;
    for (final part in entry.value.split('\n')) {
      final trimmed = part.trim();
      if (trimmed.isNotEmpty) values.add(trimmed);
    }
  }
  return values;
}

Set<String> _cookieAttributeNames(String cookie) {
  final names = <String>{};
  final parts = cookie.split(';');
  for (final attr in parts.skip(1)) {
    final name = attr.trim().split('=').first.trim().toLowerCase();
    if (name.isNotEmpty) names.add(name);
  }
  return names;
}

String _cookieName(String cookie) {
  final pair = cookie.split(';').first;
  final name = pair.split('=').first.trim();
  return name.isEmpty ? 'cookie' : name;
}

Iterable<DetectionFinding> _cookies(
  String url,
  Map<String, String> headers,
) sync* {
  for (final cookie in _iterSetCookies(headers)) {
    final attrs = _cookieAttributeNames(cookie);
    final missing = [
      for (final flag in ['secure', 'httponly'])
        if (!attrs.contains(flag)) flag,
    ];
    if (missing.isEmpty) continue;
    final name = _cookieName(cookie);
    yield DetectionFinding(
      ruleId: 'http.insecure-cookie-flags',
      severity: missing.contains('secure') ? 'high' : 'medium',
      title: 'Set-Cookie is missing security flags',
      target: url,
      locator: 'Set-Cookie:$name',
      evidence: {'cookie': name, 'missing_flags': missing},
      remediation:
          'Add Secure and HttpOnly (and a SameSite policy) to session cookies.',
    );
  }
}

Future<List<DetectionFinding>> _scanViaApiProxy(
  String apiBaseUrl,
  String url, {
  http.Client? client,
}) async {
  final httpClient = client ?? http.Client();
  final owned = client == null;
  try {
    final base = apiBaseUrl.replaceAll(RegExp(r'/+$'), '');
    final uri = Uri.parse('$base/api/detect/headers').replace(
      queryParameters: {'url': url},
    );
    final response = await httpClient.get(uri).timeout(const Duration(seconds: 25));
    if (response.statusCode != 200) {
      throw Exception('scan proxy HTTP ${response.statusCode}: ${response.body}');
    }
    final decoded = jsonDecode(utf8.decode(response.bodyBytes));
    if (decoded is! Map) {
      throw Exception('scan proxy returned non-object JSON');
    }
    final findings = decoded['findings'];
    if (findings is! List) return [];
    return findings
        .whereType<Map>()
        .map((m) => DetectionFinding.fromPayload(
              m.map((k, v) => MapEntry(k.toString(), v as Object?)),
            ))
        .toList();
  } finally {
    if (owned) httpClient.close();
  }
}

/// Fetch [url] and return header findings (skips HTTP ≥400 like the Python pack).
///
/// On Flutter web, uses `{apiBaseUrl}/api/detect/headers` (browser CORS safe).
Future<List<DetectionFinding>> scanUrlHeaders(
  String url, {
  String? apiBaseUrl,
  http.Client? client,
}) async {
  if (kIsWeb && apiBaseUrl != null && apiBaseUrl.trim().isNotEmpty) {
    return _scanViaApiProxy(apiBaseUrl.trim(), url, client: client);
  }
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
