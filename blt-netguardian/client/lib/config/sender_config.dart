/// Persisted sender credentials for the desktop client.
library;

import 'package:shared_preferences/shared_preferences.dart';

class SenderConfig {
  const SenderConfig({
    required this.baseUrl,
    required this.orgId,
    required this.senderId,
    required this.kid,
    required this.secretHex,
  });

  final String baseUrl;
  final String orgId;
  final String senderId;
  final String kid;
  final String secretHex;

  /// Loopback demo defaults matching `local_dev/send_finding.py`.
  static const SenderConfig demo = SenderConfig(
    baseUrl: 'http://127.0.0.1:8787',
    orgId: 'org-demo',
    senderId: 'scanner-1',
    kid: 'k1',
    secretHex: '736563726574',
  );

  SenderConfig copyWith({
    String? baseUrl,
    String? orgId,
    String? senderId,
    String? kid,
    String? secretHex,
  }) {
    return SenderConfig(
      baseUrl: baseUrl ?? this.baseUrl,
      orgId: orgId ?? this.orgId,
      senderId: senderId ?? this.senderId,
      kid: kid ?? this.kid,
      secretHex: secretHex ?? this.secretHex,
    );
  }

  static Future<SenderConfig> load() async {
    final prefs = await SharedPreferences.getInstance();
    return SenderConfig(
      baseUrl: prefs.getString('baseUrl') ?? demo.baseUrl,
      orgId: prefs.getString('orgId') ?? demo.orgId,
      senderId: prefs.getString('senderId') ?? demo.senderId,
      kid: prefs.getString('kid') ?? demo.kid,
      secretHex: prefs.getString('secretHex') ?? demo.secretHex,
    );
  }

  Future<void> save() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('baseUrl', baseUrl);
    await prefs.setString('orgId', orgId);
    await prefs.setString('senderId', senderId);
    await prefs.setString('kid', kid);
    await prefs.setString('secretHex', secretHex);
  }
}
