import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/task_provider.dart';
import '../providers/target_provider.dart';
import '../providers/result_provider.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadStatistics();
    });
  }

  void _loadStatistics() {
    context.read<TaskProvider>().loadStatistics();
    context.read<TargetProvider>().loadStatistics();
    context.read<ResultProvider>().loadStatistics();
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: () async {
        _loadStatistics();
      },
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Overview',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 16),
            _buildTaskStatistics(),
            const SizedBox(height: 16),
            _buildTargetStatistics(),
            const SizedBox(height: 16),
            _buildResultStatistics(),
          ],
        ),
      ),
    );
  }

  Widget _buildTaskStatistics() {
    return Consumer<TaskProvider>(
      builder: (context, provider, child) {
        final stats = provider.statistics;
        if (stats == null) {
          return const Card(
            child: Padding(
              padding: EdgeInsets.all(16),
              child: Center(child: CircularProgressIndicator()),
            ),
          );
        }

        return Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Tasks',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 16),
                _buildStatRow('Total', stats.total),
                _buildStatRow('Pending', stats.pending, Colors.orange),
                _buildStatRow('Queued', stats.queued, Colors.blue),
                _buildStatRow('Processing', stats.processing, Colors.purple),
                _buildStatRow('Completed', stats.completed, Colors.green),
                _buildStatRow('Failed', stats.failed, Colors.red),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildTargetStatistics() {
    return Consumer<TargetProvider>(
      builder: (context, provider, child) {
        final stats = provider.statistics;
        if (stats == null) {
          return const Card(
            child: Padding(
              padding: EdgeInsets.all(16),
              child: Center(child: CircularProgressIndicator()),
            ),
          );
        }

        return Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Targets',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 16),
                _buildStatRow('Total', stats.total),
                _buildStatRow('Active', stats.active, Colors.green),
                _buildStatRow('Inactive', stats.inactive, Colors.grey),
                const Divider(),
                _buildStatRow('Websites', stats.websites),
                _buildStatRow('Smart Contracts', stats.smartContracts),
                _buildStatRow('APIs', stats.apis),
                _buildStatRow('Repositories', stats.repositories),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildResultStatistics() {
    return Consumer<ResultProvider>(
      builder: (context, provider, child) {
        final stats = provider.statistics;
        if (stats == null) {
          return const Card(
            child: Padding(
              padding: EdgeInsets.all(16),
              child: Center(child: CircularProgressIndicator()),
            ),
          );
        }

        return Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Results & Vulnerabilities',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 16),
                _buildStatRow('Total Results', stats.totalResults),
                _buildStatRow('Pending', stats.pending, Colors.orange),
                _buildStatRow('Processing', stats.processing, Colors.blue),
                _buildStatRow('Triaged', stats.triaged, Colors.purple),
                _buildStatRow('Stored', stats.stored, Colors.green),
                const Divider(),
                _buildStatRow('Total Vulnerabilities', stats.totalVulnerabilities),
                _buildStatRow('Critical', stats.criticalVulnerabilities, Colors.red),
                _buildStatRow('High', stats.highVulnerabilities, Colors.orange),
                _buildStatRow('Medium', stats.mediumVulnerabilities, Colors.yellow),
                _buildStatRow('Low', stats.lowVulnerabilities, Colors.blue),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildStatRow(String label, int value, [Color? color]) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            decoration: BoxDecoration(
              color: color?.withOpacity(0.2) ?? Colors.grey.withOpacity(0.2),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              value.toString(),
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
          ),
        ],
      ),
    );
  }
}