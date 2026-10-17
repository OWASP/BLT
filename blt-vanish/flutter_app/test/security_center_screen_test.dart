import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vanish/models/security/exposure_event.dart';
import 'package:vanish/models/security/login_anomaly.dart';
import 'package:vanish/models/security/playbook_template.dart';
import 'package:vanish/screens/security_center_screen.dart';
import 'package:vanish/services/security_data_source.dart';

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

class MockNullPlaybookSecurityDataSource extends MockSuccessSecurityDataSource {
  @override
  Future<PlaybookTemplate?> fetchPlaybookTemplate(LoginAnomaly anomaly) async {
    return null;
  }
}

class MockPlaybookThrowsSecurityDataSource extends MockSuccessSecurityDataSource {
  @override
  Future<PlaybookTemplate?> fetchPlaybookTemplate(LoginAnomaly anomaly) async {
    throw Exception('Failed to fetch playbook');
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

    testWidgets('Renders login anomaly with unavailable playbook state when template is null', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: SecurityCenterScreen(
            securityDataSource: MockNullPlaybookSecurityDataSource(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Account: test_account'), findsOneWidget);
      expect(find.text('Playbook Unavailable'), findsOneWidget);
    });

    testWidgets('Renders login anomaly with unavailable playbook state when template fetch throws', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: SecurityCenterScreen(
            securityDataSource: MockPlaybookThrowsSecurityDataSource(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Account: test_account'), findsOneWidget);
      expect(find.text('Playbook Unavailable'), findsOneWidget);
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
