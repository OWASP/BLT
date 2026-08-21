/// Normalize hosts for the shared domain queue (parity with domain_normalize.py).
library;

String stripWww(String host) {
  var h = host.toLowerCase();
  if (h.endsWith('.')) h = h.substring(0, h.length - 1);
  if (h.startsWith('www.')) return h.substring(4);
  return h;
}

class NormalizedDomain {
  const NormalizedDomain(this.hostKey, this.seedUrl);
  final String hostKey;
  final String seedUrl;
}

NormalizedDomain? normalizeDomain(String raw) {
  var text = raw.trim();
  if (text.isEmpty) return null;
  final Uri? parsed;
  if (text.contains('://')) {
    parsed = Uri.tryParse(text);
  } else {
    final head = text.split('/').first;
    if (head.contains(':')) return null;
    parsed = Uri.tryParse('https://$text');
  }
  if (parsed == null) return null;
  if (parsed.scheme != 'http' && parsed.scheme != 'https') return null;
  var host = (parsed.host).toLowerCase();
  if (host.endsWith('.')) host = host.substring(0, host.length - 1);
  host = stripWww(host);
  if (host.isEmpty ||
      host == 'localhost' ||
      host == '127.0.0.1' ||
      host == '::1' ||
      !host.contains('.')) {
    return null;
  }
  return NormalizedDomain(host, 'https://$host/');
}
