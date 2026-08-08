import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/security/risk_assessment.dart';
import '../models/security/security_alert.dart';
import '../services/remediation_planner.dart';
import '../services/reputation_enrichment_service.dart';
import '../services/risk_assessment_builder.dart';
import '../services/storage_service.dart';
import '../services/telemetry_service.dart';
import '../services/url_expansion_service.dart';
import '../services/url_signal_extractor.dart';

enum _ScanUiState {
  idle,
  loading,
  success,
  parseError,
  offlineFallback,
}

/// Entry screen for manual and share-sheet phishing scans.
class SecurityCenterScreen extends StatefulWidget {
  /// Optional initial content supplied by a share intent.
  final String initialInput;
  /// Optional URL expansion override for tests.
  final UrlExpansionService? expansionService;
  /// Optional lexical signal extractor override for tests.
  final UrlSignalExtractor? signalExtractor;
  /// Optional reputation enrichment override for tests.
  final ReputationEnrichmentService? enrichmentService;
  /// Optional assessment builder override for tests.
  final RiskAssessmentBuilder? assessmentBuilder;
  /// Optional telemetry override for tests.
  final TelemetryService? telemetryService;

  /// Creates the Security Center screen.
  const SecurityCenterScreen({
    super.key,
    this.initialInput = '',
    this.expansionService,
    this.signalExtractor,
    this.enrichmentService,
    this.assessmentBuilder,
    this.telemetryService,
  });

  @override
  State<SecurityCenterScreen> createState() => _SecurityCenterScreenState();
}

class _SecurityCenterScreenState extends State<SecurityCenterScreen> {
  late final TextEditingController _inputController;
  late final UrlExpansionService _expansionService;
  late final UrlSignalExtractor _signalExtractor;
  late final RiskAssessmentBuilder _assessmentBuilder;
  late final TelemetryService _telemetry;
  late final ReputationEnrichmentService _enrichmentService;
  final RemediationPlanner _remediationPlanner = const RemediationPlanner();

  RiskAssessment? _currentAssessment;
  _ScanUiState _scanState = _ScanUiState.idle;
  String? _errorMessage;
  String _lastSource = 'manual_paste';

  bool get _isScanning => _scanState == _ScanUiState.loading;

  static const _defaultWorkerBaseUrl = String.fromEnvironment(
    'WORKER_BASE_URL',
    defaultValue: 'https://cloudflare-worker-api.owasp.workers.dev',
  );

  @override
  void initState() {
    super.initState();
    _inputController = TextEditingController(text: widget.initialInput);
    _expansionService = widget.expansionService ?? UrlExpansionService();
    _signalExtractor = widget.signalExtractor ?? UrlSignalExtractor();
    _assessmentBuilder = widget.assessmentBuilder ?? RiskAssessmentBuilder();
    _telemetry = widget.telemetryService ?? TelemetryService();
    _enrichmentService = widget.enrichmentService ??
        ReputationEnrichmentService(
          baseUrl: _defaultWorkerBaseUrl,
        );

    if (widget.initialInput.isNotEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _handleScan(widget.initialInput, source: 'share_sheet');
      });
    }
  }

  @override
  void dispose() {
    if (_inputController.text.trim().isNotEmpty &&
        _scanState != _ScanUiState.success &&
        _scanState != _ScanUiState.offlineFallback) {
      _telemetry.trackAbandonment(
        inputSource: _lastSource,
        state: _scanState.name,
      );
    }
    _inputController.dispose();
    super.dispose();
  }

  Future<void> _handleScan(String input, {String source = 'manual_paste'}) async {
    if (input.trim().isEmpty) return;
    _lastSource = source;

    setState(() {
      _scanState = _ScanUiState.loading;
      _errorMessage = null;
      _currentAssessment = null;
    });

    final stopwatch = Stopwatch()..start();

    try {
      final expandedUrl = await _expansionService.expandUrl(input.trim());
      final uri = Uri.tryParse(expandedUrl);

      if (uri == null || !uri.hasScheme) {
        throw const FormatException('Invalid URL format');
      }

      final localSignals = _signalExtractor.extract(uri);
      final edgeSignals = await _enrichmentService.fetchReputation(
        uri.host,
        timeoutMs: 1500,
      );

      final assessment = _assessmentBuilder.buildAssessment(
        url: expandedUrl,
        localSignals: localSignals,
        enrichmentSignals: edgeSignals,
      );

      final wasOfflineFallback = edgeSignals['reputation'] == 'unknown';
      await _persistAssessmentAndTasks(assessment);

      setState(() {
        _currentAssessment = assessment;
        _scanState = wasOfflineFallback
            ? _ScanUiState.offlineFallback
            : _ScanUiState.success;
      });

      stopwatch.stop();
      _telemetry.trackScanEvent(
        inputSource: source,
        finalSeverity: assessment.severity.name,
        latencyMs: stopwatch.elapsedMilliseconds,
        wasOfflineFallback: wasOfflineFallback,
      );
    } on FormatException catch (error) {
      stopwatch.stop();
      setState(() {
        _scanState = _ScanUiState.parseError;
        _errorMessage = 'Scan pipeline failure: Unable to safely parse entry target.';
      });
      _telemetry.trackError(
        errorType: error.toString(),
        component: 'SecurityCenterScreen',
      );
    } catch (error) {
      stopwatch.stop();
      setState(() {
        _scanState = _ScanUiState.parseError;
        _errorMessage = 'Scan pipeline failure: Unable to safely parse entry target.';
      });
      _telemetry.trackError(
        errorType: error.toString(),
        component: 'SecurityCenterScreen',
      );
    }
  }

  Future<void> _persistAssessmentAndTasks(RiskAssessment assessment) async {
    try {
      final storageService = context.read<StorageService>();
      await storageService.saveRiskAssessment(assessment);
      final tasks = _remediationPlanner.planForAssessment(assessment);
      for (final task in tasks) {
        await storageService.saveRemediationTask(task);
      }
    } catch (_) {
      // Tests and standalone previews may render this screen without storage.
    }
  }

  void _handleRemediationAction(String title, String description) {
    _telemetry.trackRemediationCtaClicked(title);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(description)),
    );
  }

  Color _getSeverityColor(AlertSeverity severity) {
    switch (severity) {
      case AlertSeverity.critical:
        return const Color(0xFFD32F2F);
      case AlertSeverity.high:
        return const Color(0xFFF57C00);
      case AlertSeverity.medium:
        return const Color(0xFFFBC02D);
      case AlertSeverity.low:
        return const Color(0xFF388E3C);
    }
  }

  Widget _buildInputModes() {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        const Chip(label: Text('Manual Paste')),
        Chip(
          label: Text(
            widget.initialInput.isNotEmpty
                ? 'Share Sheet Connected'
                : 'Share Sheet Ready',
          ),
        ),
        const Chip(label: Text('Email Forwarding Prototype Pending')),
      ],
    );
  }

  Widget _buildStateBanner() {
    switch (_scanState) {
      case _ScanUiState.idle:
        return const Card(
          elevation: 0,
          color: Color(0xFFF1F8E9),
          child: Padding(
            padding: EdgeInsets.all(16.0),
            child: Text(
              'Ready to scan. Paste a link manually or continue from a shared link intent.',
            ),
          ),
        );
      case _ScanUiState.loading:
        return const Card(
          elevation: 0,
          color: Color(0xFFE8F0FE),
          child: Padding(
            padding: EdgeInsets.all(16.0),
            child: Row(
              children: [
                SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
                SizedBox(width: 12),
                Expanded(
                  child: Text('Analyzing link signals and reputation data...'),
                ),
              ],
            ),
          ),
        );
      case _ScanUiState.success:
        return const Card(
          elevation: 0,
          color: Color(0xFFE8F5E9),
          child: Padding(
            padding: EdgeInsets.all(16.0),
            child: Text(
              'Scan complete. Review the indicators and remediation guidance below.',
            ),
          ),
        );
      case _ScanUiState.parseError:
        return Card(
          color: const Color(0xFFFFEBEE),
          elevation: 0,
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Text(
              _errorMessage ??
                  'Scan pipeline failure: Unable to safely parse entry target.',
              style: const TextStyle(color: Color(0xFFC62828)),
            ),
          ),
        );
      case _ScanUiState.offlineFallback:
        return const Card(
          elevation: 0,
          color: Color(0xFFFFF8E1),
          child: Padding(
            padding: EdgeInsets.all(16.0),
            child: Text(
              'Offline-safe result. Edge reputation was unavailable, so this assessment used local signals only.',
            ),
          ),
        );
    }
  }

  Widget _buildAssessmentCard() {
    final assessment = _currentAssessment!;

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: Colors.grey.shade200),
      ),
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  assessment.severity.name.toUpperCase(),
                  style: TextStyle(
                    color: _getSeverityColor(assessment.severity),
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1.2,
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.grey.shade100,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    'Score: ${(assessment.finalScore * 100).toStringAsFixed(0)}%',
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              'Target: ${assessment.targetAsset}',
              style: TextStyle(color: Colors.grey.shade600, fontSize: 14),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 20),
            const Divider(),
            const SizedBox(height: 12),
            const Text(
              'Analysis Indicators',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            if (assessment.alerts.first.reasonCodes.isEmpty)
              Text(
                'No active anomalies found.',
                style: TextStyle(color: Colors.grey.shade500),
              )
            else
              Wrap(
                spacing: 8.0,
                runSpacing: 4.0,
                children: assessment.alerts.first.reasonCodes
                    .map(
                      (code) => Chip(
                        label: Text(
                          code,
                          style: const TextStyle(fontSize: 12),
                        ),
                        backgroundColor: Colors.grey.shade100,
                        side: BorderSide(color: Colors.grey.shade300),
                      ),
                    )
                    .toList(),
              ),
            if (assessment.recommendedActions.isNotEmpty) ...[
              const SizedBox(height: 16),
              const Divider(),
              const SizedBox(height: 12),
              const Text(
                'Recommended Actions',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 10),
              ...assessment.recommendedActions.map(
                (action) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(12),
                      color: Colors.grey.shade50,
                      border: Border.all(color: Colors.grey.shade200),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          action.title,
                          style: const TextStyle(
                            fontWeight: FontWeight.w700,
                            fontSize: 15,
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(action.description),
                        const SizedBox(height: 10),
                        Align(
                          alignment: Alignment.centerLeft,
                          child: FilledButton.tonal(
                            onPressed: () => _handleRemediationAction(
                              action.title,
                              action.description,
                            ),
                            child: const Text('Review Action'),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFFAF9F6),
      appBar: AppBar(
        title: const Text(
          'Security Center',
          style: TextStyle(fontWeight: FontWeight.w600),
        ),
        backgroundColor: Colors.white,
        foregroundColor: Colors.black87,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              elevation: 0,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
                side: BorderSide(color: Colors.grey.shade200),
              ),
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 16.0,
                  vertical: 8.0,
                ),
                child: TextField(
                  controller: _inputController,
                  decoration: InputDecoration(
                    hintText: 'Paste link or message context to verify...',
                    border: InputBorder.none,
                    suffixIcon: _isScanning
                        ? const SizedBox(
                            width: 24,
                            height: 24,
                            child: Padding(
                              padding: EdgeInsets.all(8.0),
                              child: CircularProgressIndicator(strokeWidth: 2),
                            ),
                          )
                        : IconButton(
                            icon: const Icon(
                              Icons.security,
                              color: Color(0xFF388E3C),
                            ),
                            onPressed: () => _handleScan(_inputController.text),
                          ),
                  ),
                  onSubmitted: (value) => _handleScan(value),
                ),
              ),
            ),
            const SizedBox(height: 20),
            _buildInputModes(),
            const SizedBox(height: 12),
            _buildStateBanner(),
            if (_currentAssessment != null) ...[
              const SizedBox(height: 20),
              _buildAssessmentCard(),
            ],
          ],
        ),
      ),
    );
  }
}
