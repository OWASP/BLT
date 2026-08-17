import '../models/security/login_anomaly.dart';

class LoginAnomalyService {
  /// Analyzes a login attempt based on heuristics and provider flags.
  LoginAnomaly analyzeLogin({
    required String accountId,
    required bool newGeo,
    required bool newDevice,
    required bool oddHour,
    required bool priorPhishingAlert,
  }) {
    double score = 0.0;
    List<String> reasonCodes = [];

    if (newGeo) {
      score += 0.35;
      reasonCodes.add('NEW_GEO');
    }
    if (newDevice) {
      score += 0.30;
      reasonCodes.add('NEW_DEVICE');
    }
    if (oddHour) {
      score += 0.15;
      reasonCodes.add('ODD_HOUR');
    }
    if (priorPhishingAlert) {
      score += 0.20; // Correlation boost
      reasonCodes.add('PRIOR_PHISHING_ALERT');
    }

    // Clamp score to 1.0 max
    if (score > 1.0) score = 1.0;

    return LoginAnomaly(
      accountId: accountId,
      score: score,
      riskBand: _determineRiskBand(score),
      reasonCodes: reasonCodes,
      detectedAt: DateTime.now(),
    );
  }

  String _determineRiskBand(double score) {
    if (score >= 0.80) return 'critical';
    if (score >= 0.60) return 'high';
    if (score >= 0.40) return 'medium';
    return 'low';
  }
}
