import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import '../lib/screens/security_center_screen.dart';
import '../lib/services/security_data_source.dart';
import '../lib/models/security/exposure_event.dart';
import '../lib/models/security/login_anomaly.dart';
import '../lib/models/security/playbook_template.dart';

class MockSuccessSecurityDataSource implements SecurityDataSource {
  @override
  Future<List<ExposureEvent>> fetchExposureEvents() async {
    return [
      ExposureEvent(
        id: 'exp_test_1',
        source: 'Test Breach Source',
        urgency: 'high',
        occurredAt: DateTime(2026, 1, 1),
      ),
    ];
  }

  @override
  Future<LoginAnomaly?> fetchLoginAnomaly() async {
    return LoginAnomaly(
      accountId: 'test_account',
      score: 0.75,
      riskBand: 'high',
      reasonCodes: ['NEW_DEVICE'],
      detectedAt: DateTime(2026, 1, 1),
    );
  }

  @override
  Future<PlaybookTemplate?> fetchPlaybookTemplate(LoginAnomaly anomaly) async {
    return PlaybookTemplate(
      id: 'pb_test',
      title: 'Test Playbook',
      severityTrigger: 'high',
      steps: [
        PlaybookStep(
          id: 'step_1',
          title: 'Test Step Title',
          description: 'Test Step Description',
          actionType: 'password_reset',
          isRequired: true,
        ),
      ],
    );
  }
}

class MockFailingSecurityDataSource implements SecurityDataSource {
  @override
  Future<List<ExposureEvent>> fetchExposureEvents() async {
    throw Exception('Network error');
  }

  @override
  Future<LoginAnomaly?> fetchLoginAnomaly() async {
    throw Exception('Network error');
  }

  @override
  Future<PlaybookTemplate?> fetchPlaybookTemplate(LoginAnomaly anomaly) async {
    throw Exception('Network error');
  }
}

void main() {
  group('SecurityCenterScreen SecurityDataSource Tests', () {
    testWidgets('Populates security data on successful fetch', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: SecurityCenterScreen(
            securityDataSource: MockSuccessSecurityDataSource(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Test Breach Source'), findsOneWidget);
      expect(find.text('Account: test_account'), findsOneWidget);
      expect(find.text('HIGH'), findsWidgets);
      expect(find.text('Playbook: Test Playbook'), findsOneWidget);
    });

    testWidgets('Shows degraded banner when fetch fails', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: SecurityCenterScreen(
            securityDataSource: MockFailingSecurityDataSource(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Provider Feed Unavailable'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
    });
  });
}
