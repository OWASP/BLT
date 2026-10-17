/// Extract crawlable absolute URLs from HTML/JS/CSS source.
library;

final _attrUrl = RegExp(
  r'''(?:href|src|action)\s*=\s*(["'])(.*?)\1''',
  caseSensitive: false,
  dotAll: true,
);

final _srcset = RegExp(
  r'''srcset\s*=\s*(["'])(.*?)\1''',
  caseSensitive: false,
  dotAll: true,
);

final _cssUrl = RegExp(
  r'''url\(\s*['"]?([^'")\s]+)['"]?\s*\)''',
  caseSensitive: false,
);

/// Absolute http(s) URLs embedded in scripts, JSON, comments, etc.
final _bareHttp = RegExp(
  r'''https?://[^\s"'<>\\)]+''',
  caseSensitive: false,
);

Uri stripFragment(Uri uri) {
  return Uri(
    scheme: uri.scheme,
    userInfo: uri.userInfo.isEmpty ? null : uri.userInfo,
    host: uri.host,
    port: uri.hasPort ? uri.port : null,
    path: uri.path.isEmpty ? '/' : uri.path,
    query: uri.hasQuery ? uri.query : null,
  );
}

/// Resolve relative/absolute [raw] against [base] into an absolute http(s) URL.
Uri? resolveCrawlUrl(Uri base, String raw) {
  var trimmed = raw.trim();
  if (trimmed.isEmpty) return null;
  // Trailing punctuation common in JS strings / HTML text.
  trimmed = trimmed.replaceAll(RegExp(r'''[.,;)\]]+$'''), '');
  final lower = trimmed.toLowerCase();
  if (lower.startsWith('javascript:') ||
      lower.startsWith('mailto:') ||
      lower.startsWith('tel:') ||
      lower.startsWith('data:') ||
      lower.startsWith('#') ||
      lower.startsWith('about:')) {
    return null;
  }
  try {
    final resolved = base.resolve(trimmed);
    if (resolved.scheme != 'http' && resolved.scheme != 'https') return null;
    if (resolved.host.isEmpty) return null;
    return stripFragment(resolved);
  } catch (_) {
    return null;
  }
}

Uri hostRoot(Uri uri) {
  return Uri(
    scheme: uri.scheme,
    host: uri.host,
    port: uri.hasPort ? uri.port : null,
    path: '/',
  );
}

/// Unique absolute http(s) URLs found in [html], resolved against [pageUrl].
List<Uri> extractUrlsFromHtml(String html, String pageUrl) {
  final base = Uri.tryParse(pageUrl.trim());
  if (base == null || !base.hasScheme || base.host.isEmpty) return const [];

  final seen = <String>{};
  final out = <Uri>[];

  void add(String raw) {
    final uri = resolveCrawlUrl(base, raw);
    if (uri == null) return;
    final key = uri.toString();
    if (seen.add(key)) out.add(uri);
  }

  for (final m in _attrUrl.allMatches(html)) {
    add(m.group(2) ?? '');
  }
  for (final m in _srcset.allMatches(html)) {
    final value = m.group(2) ?? '';
    for (final part in value.split(',')) {
      final url = part.trim().split(RegExp(r'\s+')).first;
      add(url);
    }
  }
  for (final m in _cssUrl.allMatches(html)) {
    add(m.group(1) ?? '');
  }
  for (final m in _bareHttp.allMatches(html)) {
    add(m.group(0) ?? '');
  }

  return out;
}

/// Registrable-ish host key for de-dupe (lowercased host).
String hostKey(Uri uri) => uri.host.toLowerCase();
