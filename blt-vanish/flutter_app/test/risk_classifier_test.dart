import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as path;
import 'package:selferase/models/security/security_alert.dart';
import 'package:selferase/services/risk_classifier.dart';

Map<String, dynamic> _fixtureAt(int index) {
  final fixturePath = path.join(
    Directory.current.path,
    'test',
    'fixtures',
    'phase1_url_regression_cases.json',
  );
  final decoded =
      jsonDecode(File(fixturePath).readAsStringSync()) as List<dynamic>;
  return decoded[index] as Map<String, dynamic>;
}

void main() {
  group('RiskClassifier', () {
    const classifier = RiskClassifier();

    test('returns critical severity for redundant high-risk indicators', () {
      final classification = classifier.classifyPhishing(
        localSignals: const {
          'entropy': 0.82,
          'suspicious_tokens': 0.7,
          'risky_tld': 1.0,
          'query_anomaly': 0.15,
          'urgency_token': 0.9,
        },
        enrichmentSignals: const {
          'reputation': 'malicious',
          'threat_score': '0.95',
        },
      );

      expect(classification.severity, AlertSeverity.critical);
      expect(classification.reasonCodes, contains('EDGE_REPUTATION_MATCH'));
      expect(classification.confidence, greaterThanOrEqualTo(0.5));
    });

    test('marks offline results as degraded confidence', () {
      final classification = classifier.classifyPhishing(
        localSignals: const {
          'entropy': 0.80,
          'suspicious_tokens': 0.7,
          'risky_tld': 1.0,
          'query_anomaly': 0.20,
          'urgency_token': 0.6,
        },
        enrichmentSignals: const {
          'reputation': 'unknown',
          'threat_score': '0.0',
        },
      );

      expect(classification.isOfflineFallback, isTrue);
      expect(classification.severity, AlertSeverity.medium);
      expect(classification.confidence, lessThan(0.8));
    });

    test('meets benchmark precision and recall on the labeled regression set', () {
      final fixturePath = path.join(
        Directory.current.path,
        'test',
        'fixtures',
        'phase1_url_regression_cases.json',
      );
      final decoded =
          jsonDecode(File(fixturePath).readAsStringSync()) as List<dynamic>;

      var truePositives = 0;
      var falsePositives = 0;
      var falseNegatives = 0;

      for (final item in decoded.cast<Map<String, dynamic>>()) {
        final classification = classifier.classifyPhishing(
          localSignals:
              Map<String, double>.from(item['localSignals'] as Map<dynamic, dynamic>),
          enrichmentSignals: Map<String, String>.from(
            item['enrichmentSignals'] as Map<dynamic, dynamic>,
          ),
        );
        final expectedMalicious = item['label'] == 'malicious';
        final predictedMalicious =
            classification.severity.index >= AlertSeverity.medium.index;

        if (expectedMalicious && predictedMalicious) {
          truePositives++;
        } else if (!expectedMalicious && predictedMalicious) {
          falsePositives++;
        } else if (expectedMalicious && !predictedMalicious) {
          falseNegatives++;
        }
      }

      final precision = truePositives / (truePositives + falsePositives);
      final recall = truePositives / (truePositives + falseNegatives);

      expect(precision, greaterThanOrEqualTo(0.83));
      expect(recall, greaterThanOrEqualTo(0.75));
    });

    test('fixture keeps benign marketing content below the malicious threshold', () {
      final item = _fixtureAt(4);
      final classification = classifier.classifyPhishing(
        localSignals:
            Map<String, double>.from(item['localSignals'] as Map<dynamic, dynamic>),
        enrichmentSignals: Map<String, String>.from(
          item['enrichmentSignals'] as Map<dynamic, dynamic>,
        ),
      );

      expect(classification.severity, AlertSeverity.low);
    });
  });
}
