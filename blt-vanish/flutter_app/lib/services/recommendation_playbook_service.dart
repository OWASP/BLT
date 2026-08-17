import '../models/security/login_anomaly.dart';
import '../models/security/playbook_template.dart';

class RecommendationPlaybookService {
  /// Generates a playbook tailored to the specific login anomaly.
  PlaybookTemplate generatePlaybook(LoginAnomaly anomaly) {
    List<PlaybookStep> steps = [];

    // All high/critical anomalies require a session revoke.
    if (anomaly.riskBand == 'critical' || anomaly.riskBand == 'high') {
      steps.add(PlaybookStep(
        id: 'revoke_session',
        title: 'Revoke Sessions',
        description: 'Immediately log out of all active sessions to terminate unauthorized access.',
        actionType: 'revoke_session',
        isRequired: true,
      ));
    }

    // If there is a prior phishing alert, password reset is absolutely critical.
    if (anomaly.reasonCodes.contains('PRIOR_PHISHING_ALERT')) {
      steps.add(PlaybookStep(
        id: 'reset_password_phishing',
        title: 'Reset Password',
        description: 'Your account may have been compromised by a recent phishing attempt. Change your password now.',
        actionType: 'password_reset',
        isRequired: true,
      ));
    }

    // New device logins from new locations suggest a credential leak, recommend MFA.
    if (anomaly.reasonCodes.contains('NEW_GEO') && anomaly.reasonCodes.contains('NEW_DEVICE')) {
      steps.add(PlaybookStep(
        id: 'enable_mfa',
        title: 'Enable Two-Factor Authentication',
        description: 'Add an extra layer of security to prevent logins from unknown devices.',
        actionType: 'enable_mfa',
        isRequired: true,
      ));
    }

    // If it's just a medium risk (e.g., just an odd hour), maybe just a password reset recommendation.
    if (steps.isEmpty) {
      steps.add(PlaybookStep(
        id: 'reset_password_precaution',
        title: 'Consider Resetting Password',
        description: 'We detected some unusual activity. Resetting your password is a safe precaution.',
        actionType: 'password_reset',
        isRequired: false,
      ));
    }

    return PlaybookTemplate(
      id: 'pb_${anomaly.accountId}_${DateTime.now().millisecondsSinceEpoch}',
      title: _getPlaybookTitle(anomaly.riskBand),
      severityTrigger: anomaly.riskBand,
      steps: steps,
    );
  }

  String _getPlaybookTitle(String riskBand) {
    if (riskBand == 'critical') return 'Critical Account Takeover Prevention';
    if (riskBand == 'high') return 'High Risk Login Mitigation';
    return 'Precautionary Security Steps';
  }
}
