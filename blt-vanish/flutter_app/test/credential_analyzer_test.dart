import 'package:flutter_test/flutter_test.dart';
import 'package:selferase/models/security/credential_snapshot.dart';
import 'package:selferase/models/security/security_alert.dart';
import 'package:selferase/services/credential_analyzer.dart';

void main() {
  group('CredentialAnalyzer', () {
    const analyzer = CredentialAnalyzer();

    test('scores a strong unique passphrase as low risk', () {
      final snapshot = analyzer.analyze(
        accountLabel: 'GitHub',
        username: 'ananya@example.com',
        password: 'Longer Passphrase 2026!',
        existingSnapshots: const <CredentialSnapshot>[],
      );

      expect(snapshot.severity, AlertSeverity.low);
      expect(snapshot.reasonCodes, isEmpty);
      expect(snapshot.passwordHash, isNot('Longer Passphrase 2026!'));
    });

    test('flags weak reused credentials with deterministic reason codes', () {
      final first = analyzer.analyze(
        accountLabel: 'Legacy Portal',
        username: 'user@example.com',
        password: 'password123',
        existingSnapshots: const <CredentialSnapshot>[],
      );
      final second = analyzer.analyze(
        accountLabel: 'Banking',
        username: 'user@example.com',
        password: 'password123',
        existingSnapshots: <CredentialSnapshot>[first],
        knownBreached: true,
      );

      expect(second.severity.index, greaterThanOrEqualTo(AlertSeverity.high.index));
      expect(second.reasonCodes, contains('WEAK_COMPLEXITY'));
      expect(second.reasonCodes, contains('REUSED_CREDENTIAL'));
      expect(second.reasonCodes, contains('KNOWN_DATA_BREACH'));
      expect(second.reuseHash, equals(first.reuseHash));
    });
  });
}
