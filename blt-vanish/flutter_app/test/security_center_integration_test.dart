import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:selferase/models/security/remediation_action.dart';
import 'package:selferase/models/security/risk_assessment.dart';
import 'package:selferase/models/security/security_alert.dart';
import 'package:selferase/screens/security_center_screen.dart';
import 'package:selferase/services/reputation_enrichment_service.dart';
import 'package:selferase/services/risk_assessment_builder.dart';
import 'package:selferase/services/telemetry_service.dart';
import 'package:selferase/services/url_expansion_service.dart';
import 'package:selferase/services/url_signal_extractor.dart';

class FakeUrlExpansionService extends UrlExpansionService {
  FakeUrlExpansionService(this._handler);

  final Future<String> Function(String urlString, int maxHops) _handler;

  @override
  Future<String> expandUrl(String urlString, {int maxHops = 3}) {
    return _handler(urlString, maxHops);
  }
}

class FakeUrlSignalExtractor extends UrlSignalExtractor {
  FakeUrlSignalExtractor(this.signals);

  final Map<String, double> signals;

  @override
  Map<String, double> extract(Uri uri) => signals;
}

class FakeReputationEnrichmentService extends ReputationEnrichmentService {
  FakeReputationEnrichmentService(this._handler)
    : super(
        baseUrl: 'https://worker.test',
        client: MockClient((request) async => http.Response('{}', 200)),
      );

  final Future<Map<String, String>> Function(String domain, int timeoutMs)
  _handler;

  @override
  Future<Map<String, String>> fetchReputation(
    String domain, {
    int timeoutMs = 1500,
  }) {
    return _handler(domain, timeoutMs);
  }
}

class FakeRiskAssessmentBuilder extends RiskAssessmentBuilder {
  FakeRiskAssessmentBuilder(this._handler);

  final RiskAssessment Function(
    String url,
    Map<String, double> localSignals,
    Map<String, String> enrichmentSignals,
  ) _handler;

  @override
  RiskAssessment buildAssessment({
    required String url,
    required Map<String, double> localSignals,
    required Map<String, String> enrichmentSignals,
  }) {
    return _handler(url, localSignals, enrichmentSignals);
  }
}

class FakeTelemetryService extends TelemetryService {
  final List<Map<String, String>> events = [];

  @override
  void trackScanEvent({
    required String inputSource,
    required String finalSeverity,
    required int latencyMs,
    required bool wasOfflineFallback,
  }) {
    events.add({
      'event': 'scan_completed',
      'source': inputSource,
      'severity': finalSeverity,
      'offline_fallback': wasOfflineFallback.toString(),
    });
  }

  @override
  void trackError({
    required String errorType,
    required String component,
  }) {
    events.add({
      'event': 'scan_error',
      'error_type': errorType,
      'component': component,
    });
  }

  @override
  void trackRemediationCtaClicked(String actionType) {
    events.add({
      'event': 'remediation_cta_clicked',
      'action_type': actionType,
    });
  }

  @override
  void trackAbandonment({
    required String inputSource,
    required String state,
  }) {
    events.add({
      'event': 'abandonment_tracked',
      'source': inputSource,
      'state': state,
    });
  }
}

RiskAssessment makeAssessment({
  required AlertSeverity severity,
  required List<String> reasonCodes,
  required List<RemediationAction> actions,
  required Map<String, String> enrichmentSignals,
}) {
  return RiskAssessment(
    id: 'assessment-1',
    targetAsset: 'https://secure-login-verify.xyz/update',
    severity: severity,
    finalScore: severity == AlertSeverity.critical ? 0.92 : 0.56,
    localSignals: const {
      'entropy': 0.8,
      'suspicious_tokens': 0.7,
      'risky_tld': 1.0,
    },
    enrichmentSignals: enrichmentSignals,
    assessedAt: DateTime.parse('2026-06-30T12:00:00Z'),
    alerts: [
      SecurityAlert(
        id: 'alert-1',
        type: AlertType.phishing,
        severity: severity,
        confidence: 0.9,
        reasonCodes: reasonCodes,
        createdAt: DateTime.parse('2026-06-30T12:00:00Z'),
      ),
    ],
    recommendedActions: actions,
  );
}

void main() {
  group('Security Center Scan Lifecycle Integration Tests', () {
    testWidgets(
      'submit enrich assess render flow shows loading, findings, and remediation CTA',
      (WidgetTester tester) async {
        final telemetry = FakeTelemetryService();

        await tester.pumpWidget(
          MaterialApp(
            home: SecurityCenterScreen(
              expansionService: FakeUrlExpansionService((url, maxHops) async {
                await Future<void>.delayed(const Duration(milliseconds: 10));
                return 'https://secure-login-verify.xyz/update';
              }),
              signalExtractor: FakeUrlSignalExtractor(const {
                'entropy': 0.8,
                'suspicious_tokens': 0.7,
                'risky_tld': 1.0,
                'query_anomaly': 0.2,
              }),
              enrichmentService: FakeReputationEnrichmentService((
                domain,
                timeoutMs,
              ) async {
                await Future<void>.delayed(const Duration(milliseconds: 10));
                return {'reputation': 'malicious', 'threat_score': '0.9'};
              }),
              assessmentBuilder: FakeRiskAssessmentBuilder((
                url,
                localSignals,
                enrichmentSignals,
              ) {
                return makeAssessment(
                  severity: AlertSeverity.critical,
                  reasonCodes: const [
                    'SUSPICIOUS_KEYWORDS',
                    'RISKY_TLD_EXTENSION',
                    'EDGE_REPUTATION_MATCH',
                  ],
                  actions: const [
                    RemediationAction(
                      id: 'action-1',
                      title: 'Do not submit credentials',
                      description:
                          'Avoid entering passwords until the site is independently verified.',
                      urgency: AlertSeverity.critical,
                    ),
                  ],
                  enrichmentSignals: enrichmentSignals,
                );
              }),
              telemetryService: telemetry,
            ),
          ),
        );

        await tester.enterText(
          find.byType(TextField),
          'https://verify-secure-login.xyz/update',
        );
        await tester.tap(find.byIcon(Icons.security));
        await tester.pump();

        expect(
          find.text('Analyzing link signals and reputation data...'),
          findsOneWidget,
        );

        await tester.pumpAndSettle();

        expect(
          find.text(
            'Scan complete. Review the indicators and remediation guidance below.',
          ),
          findsOneWidget,
        );
        expect(find.text('SUSPICIOUS_KEYWORDS'), findsOneWidget);
        expect(find.text('RISKY_TLD_EXTENSION'), findsOneWidget);
        expect(find.text('Do not submit credentials'), findsOneWidget);
        expect(
          telemetry.events.any((event) => event['event'] == 'scan_completed'),
          isTrue,
        );

        await tester.ensureVisible(find.text('Review Action'));
        await tester.tap(find.text('Review Action'));
        await tester.pump();

        expect(
          telemetry.events.any(
            (event) => event['event'] == 'remediation_cta_clicked',
          ),
          isTrue,
        );
      },
    );

    testWidgets(
      'share-sheet initialization auto-scans and surfaces offline fallback state',
      (WidgetTester tester) async {
        final telemetry = FakeTelemetryService();

        await tester.pumpWidget(
          MaterialApp(
            home: SecurityCenterScreen(
              initialInput: 'https://malicious-redirect.zip',
              expansionService: FakeUrlExpansionService((
                url,
                maxHops,
              ) async => url),
              signalExtractor: FakeUrlSignalExtractor(const {
                'entropy': 0.7,
                'suspicious_tokens': 0.7,
                'risky_tld': 1.0,
                'query_anomaly': 0.0,
              }),
              enrichmentService: FakeReputationEnrichmentService((
                domain,
                timeoutMs,
              ) async {
                return {'reputation': 'unknown', 'threat_score': '0.0'};
              }),
              assessmentBuilder: FakeRiskAssessmentBuilder((
                url,
                localSignals,
                enrichmentSignals,
              ) {
                return makeAssessment(
                  severity: AlertSeverity.high,
                  reasonCodes: const ['RISKY_TLD_EXTENSION'],
                  actions: const [
                    RemediationAction(
                      id: 'action-2',
                      title: 'Pause and verify the destination',
                      description:
                          'Confirm the domain before opening it elsewhere.',
                      urgency: AlertSeverity.high,
                    ),
                  ],
                  enrichmentSignals: enrichmentSignals,
                );
              }),
              telemetryService: telemetry,
            ),
          ),
        );

        await tester.pumpAndSettle();

        expect(find.textContaining('Offline-safe result.'), findsOneWidget);
        expect(
          telemetry.events.any(
            (event) =>
                event['event'] == 'scan_completed' &&
                event['offline_fallback'] == 'true',
          ),
          isTrue,
        );
      },
    );

    testWidgets(
      'invalid input enters parse error state and records scan_error telemetry',
      (WidgetTester tester) async {
        final telemetry = FakeTelemetryService();

        await tester.pumpWidget(
          MaterialApp(
            home: SecurityCenterScreen(
              expansionService: FakeUrlExpansionService((url, maxHops) async {
                return 'not-a-valid-url';
              }),
              signalExtractor: FakeUrlSignalExtractor(const {}),
              enrichmentService: FakeReputationEnrichmentService((
                domain,
                timeoutMs,
              ) async {
                return {'reputation': 'clean', 'threat_score': '0.0'};
              }),
              assessmentBuilder: FakeRiskAssessmentBuilder((
                url,
                localSignals,
                enrichmentSignals,
              ) {
                return makeAssessment(
                  severity: AlertSeverity.low,
                  reasonCodes: const [],
                  actions: const [],
                  enrichmentSignals: enrichmentSignals,
                );
              }),
              telemetryService: telemetry,
            ),
          ),
        );

        await tester.enterText(find.byType(TextField), 'bad input');
        await tester.tap(find.byIcon(Icons.security));
        await tester.pumpAndSettle();

        expect(
          find.text(
            'Scan pipeline failure: Unable to safely parse entry target.',
          ),
          findsOneWidget,
        );
        expect(
          telemetry.events.any((event) => event['event'] == 'scan_error'),
          isTrue,
        );
      },
    );
  });
}
