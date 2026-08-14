import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../models/security/remediation_task.dart';
import '../models/security/security_alert.dart';
import '../services/midterm_metrics_aggregator.dart';
import '../services/remediation_planner.dart';
import '../services/storage_service.dart';
import '../services/unified_triage_service.dart';
import '../theme/blt_theme.dart';

/// Unified triage timeline for phishing, credential, and remediation findings.
class UnifiedTriageScreen extends StatefulWidget {
  /// Creates the unified triage screen.
  const UnifiedTriageScreen({super.key});

  @override
  State<UnifiedTriageScreen> createState() => _UnifiedTriageScreenState();
}

class _UnifiedTriageScreenState extends State<UnifiedTriageScreen> {
  final _triageService = UnifiedTriageService();
  final _metricsAggregator = MidtermMetricsAggregator();
  final _planner = const RemediationPlanner();

  UnifiedTriageFilter _filter = UnifiedTriageFilter.all;
  List<UnifiedTriageItem> _items = [];
  MidtermMetrics? _metrics;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadTimeline();
  }

  Future<void> _loadTimeline() async {
    setState(() {
      _isLoading = true;
    });

    final storageService = context.read<StorageService>();
    final assessments = await storageService.getRiskAssessments();
    final credentials = await storageService.getCredentialSnapshots();
    final tasks = await storageService.getRemediationTasks();

    setState(() {
      _items = _triageService.buildTimeline(
        assessments: assessments,
        credentialSnapshots: credentials,
        remediationTasks: tasks,
        filter: _filter,
      );
      _metrics = _metricsAggregator.aggregate(
        assessments: assessments,
        credentialSnapshots: credentials,
        remediationTasks: tasks,
      );
      _isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return BltPageShell(
      padding: EdgeInsets.zero,
      child: RefreshIndicator(
        onRefresh: _loadTimeline,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 18, 16, 24),
          children: [
            _buildHeader(),
            const SizedBox(height: 14),
            _buildMetrics(),
            const SizedBox(height: 14),
            _buildFilters(),
            const SizedBox(height: 14),
            if (_isLoading)
              const Padding(
                padding: EdgeInsets.only(top: 80),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_items.isEmpty)
              _buildEmptyState()
            else
              ..._items.map(_buildTimelineCard),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const BltKicker('Unified triage'),
            const SizedBox(height: 14),
            Text(
              'One ranked queue for privacy risk.',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 10),
            Text(
              'Phishing scans, credential hygiene findings, and remediation tasks are ranked by severity, score, and recency.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMetrics() {
    final metrics = _metrics;
    if (metrics == null) {
      return const SizedBox.shrink();
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            _metricTile('Scans', metrics.scanCount.toString()),
            _metricTile('Credentials', metrics.credentialSnapshotCount.toString()),
            _metricTile('Open Tasks', metrics.openRemediationTaskCount.toString()),
            _metricTile(
              'Avg Risk',
              '${(metrics.averageRiskScore * 100).toStringAsFixed(0)}%',
            ),
          ],
        ),
      ),
    );
  }

  Widget _metricTile(String label, String value) {
    return Container(
      width: 132,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: BltColors.redTint,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFFECACA)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            value,
            style: const TextStyle(
              color: BltColors.red,
              fontSize: 24,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 2),
          Text(label, style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }

  Widget _buildFilters() {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: UnifiedTriageFilter.values.map((filter) {
        return FilterChip(
          label: Text(_filterLabel(filter)),
          selected: _filter == filter,
          onSelected: (_) {
            setState(() {
              _filter = filter;
            });
            _loadTimeline();
          },
        );
      }).toList(),
    );
  }

  Widget _buildTimelineCard(UnifiedTriageItem item) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  BltIconBox(_typeIcon(item.type), size: 40),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          item.title,
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 2),
                        Text(
                          item.subtitle,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                  _severityPill(item.severity),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Text(
                    'Priority ${(item.priorityScore * 100).toStringAsFixed(0)}%',
                    style: const TextStyle(
                      color: BltColors.ink,
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Text(
                    DateFormat.MMMd().add_jm().format(item.createdAt),
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
              if (item.reasonCodes.isNotEmpty) ...[
                const SizedBox(height: 10),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: item.reasonCodes
                      .take(3)
                      .map((code) => Chip(label: Text(code)))
                      .toList(),
                ),
              ],
              const SizedBox(height: 12),
              Align(
                alignment: Alignment.centerLeft,
                child: item.isActionable
                    ? FilledButton(
                        onPressed: () => _handleQuickAction(item),
                        child: Text(item.quickActionLabel),
                      )
                    : OutlinedButton(
                        onPressed: null,
                        child: const Text('Resolved'),
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          children: [
            const BltIconBox(Icons.inbox_outlined, size: 54),
            const SizedBox(height: 14),
            Text(
              'No triage items yet',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              'Run a Security Center scan or save a credential hygiene snapshot to populate this queue.',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }

  Widget _severityPill(AlertSeverity severity) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: _severityColor(severity).withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: _severityColor(severity).withValues(alpha: 0.25),
        ),
      ),
      child: Text(
        severity.name.toUpperCase(),
        style: TextStyle(
          color: _severityColor(severity),
          fontSize: 11,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.8,
        ),
      ),
    );
  }

  Future<void> _handleQuickAction(UnifiedTriageItem item) async {
    if (item.type != UnifiedTriageItemType.remediation) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${item.quickActionLabel} from its module.')),
      );
      return;
    }

    final storageService = context.read<StorageService>();
    final tasks = await storageService.getRemediationTasks();
    RemediationTask? task;
    for (final candidate in tasks) {
      if (candidate.id == item.id) {
        task = candidate;
        break;
      }
    }

    if (task == null || task.isTerminal) {
      return;
    }

    final nextStatus = task.status == RemediationTaskStatus.queued
        ? RemediationTaskStatus.inProgress
        : RemediationTaskStatus.completed;
    final updated = _planner.transition(task, nextStatus);
    await storageService.saveRemediationTask(updated);
    await _loadTimeline();

    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Task moved to ${nextStatus.name}.')),
    );
  }

  String _filterLabel(UnifiedTriageFilter filter) {
    return switch (filter) {
      UnifiedTriageFilter.all => 'All',
      UnifiedTriageFilter.phishing => 'Phishing',
      UnifiedTriageFilter.credentials => 'Credentials',
      UnifiedTriageFilter.remediation => 'Open Remediation',
    };
  }

  IconData _typeIcon(UnifiedTriageItemType type) {
    return switch (type) {
      UnifiedTriageItemType.phishing => Icons.link_off_outlined,
      UnifiedTriageItemType.credential => Icons.password_outlined,
      UnifiedTriageItemType.remediation => Icons.task_alt_outlined,
    };
  }

  Color _severityColor(AlertSeverity severity) {
    return switch (severity) {
      AlertSeverity.critical => BltColors.red,
      AlertSeverity.high => const Color(0xFFEA580C),
      AlertSeverity.medium => const Color(0xFFD97706),
      AlertSeverity.low => const Color(0xFF059669),
    };
  }
}
