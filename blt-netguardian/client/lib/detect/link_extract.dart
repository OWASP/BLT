/// Extract crawlable absolute URLs from HTML (href / src / action / srcset).
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

/// Resolve relative/absolute [raw] against [base] into an absolute http(s) URL.
Uri? resolveCrawlUrl(Uri base, String raw) {
  final trimmed = raw.trim();
  if (trimmed.isEmpty) return null;
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
    // Drop fragment; Uri.replace(fragment: '') can leave a trailing "#".
    return Uri(
      scheme: resolved.scheme,
      userInfo: resolved.userInfo.isEmpty ? null : resolved.userInfo,
      host: resolved.host,
      port: resolved.hasPort ? resolved.port : null,
      path: resolved.path.isEmpty ? '/' : resolved.path,
      query: resolved.hasQuery ? resolved.query : null,
    );
  } catch (_) {
    return null;
  }
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

  return out;
}

/// Registrable-ish host key for de-dupe (lowercased host).
String hostKey(Uri uri) => uri.host.toLowerCase();
