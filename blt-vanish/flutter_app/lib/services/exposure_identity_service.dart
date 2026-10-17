import 'dart:convert';
import 'package:crypto/crypto.dart';

/// Service responsible for managing privacy-safe identities.
/// It uses HMAC-SHA256 to hash sensitive data (like emails) with an app secret,
/// ensuring that plain text identifiers never persist beyond their initial processing.
class ExposureIdentityService {
  final List<int> _appSecretBytes;

  /// Initializes the service with a securely loaded secret.
  ExposureIdentityService(String appSecret)
      : _appSecretBytes = utf8.encode(appSecret);

  /// Generates a privacy-safe account hash for an email address.
  /// The email is lowercased and trimmed before hashing.
  String generateAccountHash(String email) {
    final normalizedEmail = email.trim().toLowerCase();
    final hmac = Hmac(sha256, _appSecretBytes);
    final digest = hmac.convert(utf8.encode(normalizedEmail));
    return digest.toString();
  }

  /// Verifies if a given email matches the provided account hash.
  bool verifyEmail(String email, String expectedHash) {
    return generateAccountHash(email) == expectedHash;
  }
}
