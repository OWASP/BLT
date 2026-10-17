import '../models/security/login_anomaly.dart';

/// Non-blocking adapter for intercepting desktop background events.
/// This serves as the contract hook for post-GSoC full desktop integration.
abstract class DesktopEventAdapter {
  /// Start listening to background OS events (e.g., suspicious process spawning, strange login times via PAM).
  void startListening();

  /// Stop listening to background OS events.
  void stopListening();

  /// Stream of anomalies detected from the desktop environment.
  Stream<LoginAnomaly> get onDesktopAnomalyDetected;
}
