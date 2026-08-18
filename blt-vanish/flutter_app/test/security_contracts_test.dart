import 'package:flutter_test/flutter_test.dart';
import 'package:selferase/models/security/remediation_action.dart';
import 'package:selferase/models/security/risk_assessment.dart';
import 'package:selferase/models/security/security_alert.dart';

void main() {
  group('SecurityAlert contract', () {
    final baseAlertJson = <String, dynamic>{
      'id': 'alert-1',
      'type': 'phishing',
      'severity': 'high',
      'confidence': 0.9,
      'reasonCodes': ['RISKY_TLD_EXTENSION'],
      'createdAt': '2026-06-28T12:00:00Z',
    };

    test('serializes enums using frozen wire values', () {
      final alert = SecurityAlert.fromJson(baseAlertJson);
      final serialized = alert.toJson();

      expect(serialized['type'], 'phishing');
      expect(serialized['severity'], 'high');
      expect(serialized['confidence'], 0.9);
    });

    test('rejects missing required fields', () {
      final invalidJson = Map<String, dynamic>.from(baseAlertJson)
        ..remove('createdAt');

      expect(() => SecurityAlert.fromJson(invalidJson), throwsA(isA<TypeError>()));
    });

    test('rejects invalid enum values', () {
      final invalidJson = Map<String, dynamic>.from(baseAlertJson)
        ..['type'] = 'unknown';

      expect(
        () => SecurityAlert.fromJson(invalidJson),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('ignores forward-compatible extra fields', () {
      final enrichedJson = Map<String, dynamic>.from(baseAlertJson)
        ..['futureField'] = 'kept by newer producers';

      final alert = SecurityAlert.fromJson(enrichedJson);

      expect(alert.id, 'alert-1');
      expect(alert.reasonCodes, ['RISKY_TLD_EXTENSION']);
    });

    test('rejects out-of-range confidence values', () {
      final invalidJson = Map<String, dynamic>.from(baseAlertJson)
        ..['confidence'] = 1.4;

      expect(
        () => SecurityAlert.fromJson(invalidJson),
        throwsA(isA<AssertionError>()),
      );
    });
  });

  group('RiskAssessment contract', () {
    final baseAssessmentJson = <String, dynamic>{
      'id': 'assessment-1',
      'targetAsset': 'https://secure-login-verify.xyz/login',
      'severity': 'critical',
      'finalScore': 0.95,
      'localSignals': {
        'entropy': 0.81,
        'suspicious_tokens': 1.0,
      },
      'enrichmentSignals': {
        'reputation': 'malicious',
        'threat_score': '0.9',
      },
      'assessedAt': '2026-06-28T12:00:00Z',
      'alerts': [
        {
          'id': 'alert-1',
          'type': 'phishing',
          'severity': 'critical',
          'confidence': 0.95,
          'reasonCodes': ['EDGE_REPUTATION_MATCH'],
          'createdAt': '2026-06-28T12:00:00Z',
        },
      ],
      'recommendedActions': [
        {
          'id': 'action-1',
          'title': 'Block Navigation Target',
          'description': 'Do not submit credentials on this domain.',
          'urgency': 'critical',
          'deepLink': null,
        },
      ],
    };

    test('deserializes nested contracts and preserves enum wire values', () {
      final assessment = RiskAssessment.fromJson(baseAssessmentJson);
      final serialized = assessment.toJson();

      expect(assessment.severity, AlertSeverity.critical);
      expect(assessment.alerts.single.type, AlertType.phishing);
      expect(assessment.recommendedActions.single.urgency, AlertSeverity.critical);
      expect(serialized['severity'], 'critical');
      expect(
        (serialized['recommendedActions'] as List).single['urgency'],
        'critical',
      );
    });

    test('rejects nested payloads with invalid severity values', () {
      final invalidJson = Map<String, dynamic>.from(baseAssessmentJson)
        ..['recommendedActions'] = [
          {
            'id': 'action-1',
            'title': 'Block Navigation Target',
            'description': 'Do not submit credentials on this domain.',
            'urgency': 'urgent',
          },
        ];

      expect(
        () => RiskAssessment.fromJson(invalidJson),
        throwsA(isA<ArgumentError>()),
      );
    });
  });

  group('RemediationAction contract', () {
    test('accepts nullable deep links', () {
      final action = RemediationAction.fromJson({
        'id': 'action-1',
        'title': 'Block Navigation Target',
        'description': 'Do not submit credentials on this domain.',
        'urgency': 'medium',
        'deepLink': null,
      });

      expect(action.deepLink, isNull);
      expect(action.toJson()['urgency'], 'medium');
    });
  });
}
