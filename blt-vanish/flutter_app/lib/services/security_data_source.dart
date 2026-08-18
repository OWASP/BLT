import '../models/security/exposure_event.dart';
import '../models/security/login_anomaly.dart';
import '../models/security/playbook_template.dart';
import 'recommendation_playbook_service.dart';

/// Abstract contract for fetching or streaming security events, anomalies, and playbooks.
abstract class SecurityDataSource {
  /// Fetches exposure timeline events.
  Future<List<ExposureEvent>> fetchExposureEvents();

  /// Fetches current login anomaly, if any.
  Future<LoginAnomaly?> fetchLoginAnomaly();

  /// Fetches recommended playbook for a given login anomaly.
  Future<PlaybookTemplate?> fetchPlaybookTemplate(LoginAnomaly anomaly);
}

/// Default implementation of [SecurityDataSource] providing fallback security data.
class DefaultSecurityDataSource implements SecurityDataSource {
  final RecommendationPlaybookService _playbookService;

  /// Creates the default security data source.
  DefaultSecurityDataSource({
    RecommendationPlaybookService? playbookService,
  }) : _playbookService = playbookService ?? RecommendationPlaybookService();

  @override
  Future<List<ExposureEvent>> fetchExposureEvents() async {
    return [
      ExposureEvent(
        id: 'exp_1',
        source: 'Breach Data Network',
        urgency: 'high',
        occurredAt: DateTime.now().subtract(const Duration(days: 2)),
      ),
    ];
  }

  @override
  Future<LoginAnomaly?> fetchLoginAnomaly() async {
    return LoginAnomaly(
      accountId: 'usr_sec_994',
      score: 0.85,
      riskBand: 'critical',
      reasonCodes: const ['NEW_GEO', 'NEW_DEVICE', 'PRIOR_PHISHING_ALERT'],
      detectedAt: DateTime.now().subtract(const Duration(hours: 3)),
    );
  }

  @override
  Future<PlaybookTemplate?> fetchPlaybookTemplate(LoginAnomaly anomaly) async {
    return _playbookService.generatePlaybook(anomaly);
  }
}
