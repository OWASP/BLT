import '../models/security/login_anomaly.dart';
import 'login_anomaly_service.dart';

class RiskCorrelationService {
  final LoginAnomalyService _anomalyService;

  RiskCorrelationService(this._anomalyService);

  /// Correlates a new login event with existing risk context.
  LoginAnomaly correlateLogin({
    required String accountId,
    required bool newGeo,
    required bool newDevice,
    required bool oddHour,
    required bool hasRecentPhishingAlert,
    required bool hasWeakCredential,
  }) {
    return _anomalyService.analyzeLogin(
      accountId: accountId,
      newGeo: newGeo,
      newDevice: newDevice,
      oddHour: oddHour,
      priorPhishingAlert: hasRecentPhishingAlert,
      weakCredential: hasWeakCredential,
    );
  }
}
