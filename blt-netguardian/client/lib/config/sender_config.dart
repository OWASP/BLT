/// Persisted sender credentials for the desktop / hosted web client.
library;

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:shared_preferences/shared_preferences.dart';

class SenderConfig {
  const SenderConfig({
    required this.baseUrl,
    required this.orgId,
    required this.senderId,
    required this.kid,
    required this.secretHex,
    this.payloadKeyB64 = '',
    this.encrypt = false,
    this.redactBeforeSend = true,
  });

  final String baseUrl;
  final String orgId;
  final String senderId;
  final String kid;
  final String secretHex;
  final String payloadKeyB64;
  final bool encrypt;
  final bool redactBeforeSend;

  bool get isLoopback {
    final host = Uri.tryParse(baseUrl)?.host.toLowerCase() ?? '';
    return host == 'localhost' || host == '127.0.0.1' || host == '::1';
  }

  /// Loopback demo defaults matching `local_dev/send_finding.py`.
  static const SenderConfig demo = SenderConfig(
    baseUrl: 'http://127.0.0.1:8787',
    orgId: 'org-demo',
    senderId: 'scanner-1',
    kid: 'k1',
    secretHex: '736563726574',
    payloadKeyB64: 'bmV0Z3VhcmRpYW4tZGVtby1hZXNnY20ta2V5LTAwMzI=',
    encrypt: true,
    redactBeforeSend: true,
  );

  SenderConfig copyWith({
    String? baseUrl,
    String? orgId,
    String? senderId,
    String? kid,
    String? secretHex,
    String? payloadKeyB64,
    bool? encrypt,
    bool? redactBeforeSend,
  }) {
    return SenderConfig(
      baseUrl: baseUrl ?? this.baseUrl,
      orgId: orgId ?? this.orgId,
      senderId: senderId ?? this.senderId,
      kid: kid ?? this.kid,
      secretHex: secretHex ?? this.secretHex,
      payloadKeyB64: payloadKeyB64 ?? this.payloadKeyB64,
      encrypt: encrypt ?? this.encrypt,
      redactBeforeSend: redactBeforeSend ?? this.redactBeforeSend,
    );
  }

  /// Hosted Flutter web uses the Worker origin so mentors do not type a URL.
  static String _defaultBaseUrl() {
    if (kIsWeb) {
      final host = Uri.base.host.toLowerCase();
      if (host.isNotEmpty && host != 'localhost' && host != '127.0.0.1') {
        return Uri.base.origin;
      }
    }
    return demo.baseUrl;
  }

  static Future<SenderConfig> load() async {
    final prefs = await SharedPreferences.getInstance();
    var baseUrl = prefs.getString('baseUrl') ?? _defaultBaseUrl();
    if (kIsWeb) {
      final hosted = _defaultBaseUrl() != demo.baseUrl;
      final savedHost = Uri.tryParse(baseUrl)?.host.toLowerCase() ?? '';
      final savedLoopback =
          savedHost.isEmpty || savedHost == 'localhost' || savedHost == '127.0.0.1';
      if (hosted && savedLoopback) baseUrl = _defaultBaseUrl();
    }
    return SenderConfig(
      baseUrl: baseUrl,
      orgId: prefs.getString('orgId') ?? demo.orgId,
      senderId: prefs.getString('senderId') ?? demo.senderId,
      kid: prefs.getString('kid') ?? demo.kid,
      secretHex: prefs.getString('secretHex') ?? demo.secretHex,
      payloadKeyB64: prefs.getString('payloadKeyB64') ?? demo.payloadKeyB64,
      encrypt: prefs.getBool('encrypt') ?? demo.encrypt,
      redactBeforeSend: prefs.getBool('redactBeforeSend') ?? demo.redactBeforeSend,
    );
  }

  Future<void> save() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('baseUrl', baseUrl);
    await prefs.setString('orgId', orgId);
    await prefs.setString('senderId', senderId);
    await prefs.setString('kid', kid);
    await prefs.setString('secretHex', secretHex);
    await prefs.setString('payloadKeyB64', payloadKeyB64);
    await prefs.setBool('encrypt', encrypt);
    await prefs.setBool('redactBeforeSend', redactBeforeSend);
  }
}
