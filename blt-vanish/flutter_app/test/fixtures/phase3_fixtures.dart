import '../../lib/models/security/exposure_event.dart';
import '../../lib/models/security/login_anomaly.dart';
import '../../lib/models/security/playbook_template.dart';

/// Test fixtures for Exposure and Anomaly flows.

final testExposureEvent = ExposureEvent(
  source: 'HIBP',
  occurredAt: DateTime.parse('2026-08-01T00:00:00Z'),
  urgency: 'high',
  confidence: 0.95,
  accountHash: 'a5e744d0164540d33b1d7ea616c28f2fa97e754a', // Mock hash
);

final testLoginAnomaly = LoginAnomaly(
  accountId: 'user_123',
  score: 0.85,
  riskBand: 'critical',
  reasonCodes: ['NEW_GEO', 'NEW_DEVICE'],
  detectedAt: DateTime.parse('2026-08-14T12:00:00Z'),
);

final testPlaybookTemplate = PlaybookTemplate(
  id: 'pb_account_takeover',
  title: 'Account Takeover Prevention',
  severityTrigger: 'critical',
  steps: [
    PlaybookStep(
      id: 'step_1',
      title: 'Reset Password',
      description: 'Change your account password immediately.',
      actionType: 'password_reset',
      isRequired: true,
    ),
    PlaybookStep(
      id: 'step_2',
      title: 'Revoke Sessions',
      description: 'Log out of all active sessions.',
      actionType: 'revoke_session',
      isRequired: true,
    ),
  ],
);
