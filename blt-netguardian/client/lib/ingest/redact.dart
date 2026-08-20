/// Client-side payload redaction (parity with `src/payload_redact.py`).
library;

const redactKeys = {
  'password',
  'secret',
  'token',
  'api_key',
  'authorization',
  'private_key',
  'credential',
};

Object? redactValue(Object? value) {
  if (value is Map) {
    return redactPayload(
      value.map((k, v) => MapEntry(k.toString(), v as Object?)),
    );
  }
  if (value is List) {
    return value.map(redactValue).toList();
  }
  return value;
}

Map<String, Object?> redactPayload(Map<String, Object?> payload) {
  final redacted = <String, Object?>{};
  for (final entry in payload.entries) {
    if (redactKeys.contains(entry.key.toLowerCase())) {
      redacted[entry.key] = '[REDACTED]';
    } else if (entry.value is Map) {
      redacted[entry.key] = redactPayload(
        (entry.value as Map).map((k, v) => MapEntry(k.toString(), v as Object?)),
      );
    } else if (entry.value is List) {
      redacted[entry.key] = (entry.value as List).map(redactValue).toList();
    } else {
      redacted[entry.key] = entry.value;
    }
  }
  return redacted;
}
