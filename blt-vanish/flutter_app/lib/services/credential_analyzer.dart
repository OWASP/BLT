import 'dart:convert';

import 'package:crypto/crypto.dart';
import 'package:uuid/uuid.dart';

import '../models/security/credential_snapshot.dart';
import '../models/security/security_alert.dart';

/// Deterministic local-only credential hygiene analyzer.
class CredentialAnalyzer {
  /// Creates a credential analyzer with stable deterministic defaults.
  const CredentialAnalyzer();

  static const List<String> _commonCompromisedPasswords = <String>[
    '123456',
    'password',
    'password123',
    'qwerty',
    'letmein',
    'welcome1',
    'admin123',
  ];

  /// Analyzes a credential without persisting plaintext.
  CredentialSnapshot analyze({
    required String accountLabel,
    required String username,
    required String password,
    required List<CredentialSnapshot> existingSnapshots,
    bool knownBreached = false,
  }) {
    final trimmedPassword = password.trim();
    final lowerPassword = trimmedPassword.toLowerCase();
    final passwordHash = _sha256(trimmedPassword);
    final reuseHash = _sha256(lowerPassword);
    final now = DateTime.now();

    final strengthScore = _computeStrengthScore(
      password: trimmedPassword,
      username: username,
    );
    final isReused = existingSnapshots.any(
      (snapshot) => snapshot.reuseHash == reuseHash,
    );
    final reuseLikelihoodScore = isReused ? 1.0 : 0.0;
    final exposureTriggered =
        knownBreached || _commonCompromisedPasswords.contains(lowerPassword);
    final exposureScore = exposureTriggered ? 1.0 : 0.0;
    final finalScore = ((1.0 - strengthScore) * 0.55 +
            reuseLikelihoodScore * 0.25 +
            exposureScore * 0.20)
        .clamp(0.0, 1.0);
    final severity = _mapScoreToSeverity(finalScore);

    final reasonCodes = <String>[];
    if (strengthScore < 0.55) {
      reasonCodes.add('WEAK_COMPLEXITY');
    }
    if (reuseLikelihoodScore > 0.0) {
      reasonCodes.add('REUSED_CREDENTIAL');
    }
    if (exposureScore > 0.0) {
      reasonCodes.add('KNOWN_DATA_BREACH');
    }

    final rotationGuidance = _buildRotationGuidance(
      severity: severity,
      isReused: isReused,
      exposureTriggered: exposureTriggered,
      strengthScore: strengthScore,
    );

    return CredentialSnapshot(
      id: const Uuid().v4(),
      accountLabel: accountLabel.trim(),
      username: username.trim(),
      passwordHash: passwordHash,
      reuseHash: reuseHash,
      strengthScore: strengthScore,
      reuseLikelihoodScore: reuseLikelihoodScore,
      exposureScore: exposureScore,
      finalScore: finalScore,
      severity: severity,
      reasonCodes: reasonCodes,
      rotationGuidance: rotationGuidance,
      createdAt: now,
      updatedAt: now,
    );
  }

  double _computeStrengthScore({
    required String password,
    required String username,
  }) {
    final lengthScore = (password.length / 18.0).clamp(0.0, 1.0);
    final hasLower = password.contains(RegExp('[a-z]'));
    final hasUpper = password.contains(RegExp('[A-Z]'));
    final hasDigit = password.contains(RegExp('[0-9]'));
    final hasSymbol = password.contains(RegExp(r'[^A-Za-z0-9]'));
    final characterClasses = <bool>[hasLower, hasUpper, hasDigit, hasSymbol]
        .where((value) => value)
        .length;
    final classScore = characterClasses / 4.0;
    final uniqueRatio =
        password.isEmpty ? 0.0 : password.split('').toSet().length / password.length;
    final passphraseBonus = password.length >= 16 ? 1.0 : 0.0;
    final usernamePenalty = username.isNotEmpty &&
            password.toLowerCase().contains(username.trim().toLowerCase())
        ? 0.15
        : 0.0;

    final score = (lengthScore * 0.35) +
        (classScore * 0.30) +
        (uniqueRatio * 0.20) +
        (passphraseBonus * 0.15) -
        usernamePenalty;

    return score.clamp(0.0, 1.0);
  }

  AlertSeverity _mapScoreToSeverity(double score) {
    if (score >= 0.85) {
      return AlertSeverity.critical;
    }
    if (score >= 0.65) {
      return AlertSeverity.high;
    }
    if (score >= 0.40) {
      return AlertSeverity.medium;
    }
    return AlertSeverity.low;
  }

  String _buildRotationGuidance({
    required AlertSeverity severity,
    required bool isReused,
    required bool exposureTriggered,
    required double strengthScore,
  }) {
    if (severity == AlertSeverity.low) {
      return 'Credential snapshot looks healthy. Keep using a unique passphrase and rotate on your normal schedule.';
    }
    if (exposureTriggered) {
      return 'Rotate this password immediately and review any other accounts that may share the same secret.';
    }
    if (isReused) {
      return 'Create a unique password for this account and update reused accounts in the same session.';
    }
    if (strengthScore < 0.55) {
      return 'Replace this password with a longer passphrase that mixes multiple character classes.';
    }
    return 'Review this credential soon and prefer a unique passphrase plus MFA where available.';
  }

  String _sha256(String input) {
    return sha256.convert(utf8.encode(input)).toString();
  }
}
