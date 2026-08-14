import '../models/security/exposure_event.dart';

/// Abstract adapter interface for external breach/exposure services (e.g. HIBP).
abstract class ExposureAdapter {
  /// The name of the exposure provider.
  String get providerName;

  /// Checks if a given email hash is present in the exposure dataset.
  /// Implementations must ensure the email is hashed appropriately before checking (e.g., k-anonymity for HIBP).
  Future<List<ExposureEvent>> checkEmailExposure(String emailHash);

  /// Checks if a given password hash is present in the exposure dataset.
  /// Implementations must ensure the password is hashed (e.g., SHA-1 first 5 chars for HIBP k-anonymity).
  Future<List<ExposureEvent>> checkPasswordExposure(String passwordHash);
}

/// A scaffold implementation for HIBP (Have I Been Pwned).
class HibpExposureAdapter implements ExposureAdapter {
  @override
  String get providerName => 'HIBP';

  @override
  Future<List<ExposureEvent>> checkEmailExposure(String emailHash) async {
    // TODO: Phase 3 implement HIBP Breached Accounts endpoint lookup.
    return [];
  }

  @override
  Future<List<ExposureEvent>> checkPasswordExposure(String passwordHash) async {
    // TODO: Phase 3 implement HIBP Pwned Passwords endpoint lookup using k-anonymity.
    return [];
  }
}
