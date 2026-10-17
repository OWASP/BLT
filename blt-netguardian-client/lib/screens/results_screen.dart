import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/agent_result.dart';
import '../providers/result_provider.dart';

class ResultsScreen extends StatefulWidget {
  const ResultsScreen({super.key});

  @override
  State<ResultsScreen> createState() => _ResultsScreenState();
}

class _ResultsScreenState extends State<ResultsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ResultProvider>().loadResults();
      context.read<ResultProvider>().loadVulnerabilities();
    });
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          automaticallyImplyLeading: false,
          title: const TabBar(
            tabs: [
              Tab(text: 'Results'),
              Tab(text: 'Vulnerabilities'),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            _buildResultsList(),
            _buildVulnerabilitiesList(),
          ],
        ),
      ),
    );
  }

  Widget _buildResultsList() {
    return Consumer<ResultProvider>(
      builder: (context, provider, child) {
        if (provider.isLoading) {
          return const Center(child: CircularProgressIndicator());
        }

        if (provider.errorMessage != null) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text('Error: ${provider.errorMessage}'),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: () => provider.loadResults(),
                  child: const Text('Retry'),
                ),
              ],
            ),
          );
        }

        final results = provider.results;
        if (results.isEmpty) {
          return const Center(child: Text('No results found'));
        }

        return RefreshIndicator(
          onRefresh: () => provider.loadResults(),
          child: ListView.builder(
            itemCount: results.length,
            itemBuilder: (context, index) {
              final result = results[index];
              return _buildResultCard(result);
            },
          ),
        );
      },
    );
  }

  Widget _buildResultCard(AgentResult result) {
    Color statusColor;
    switch (result.status) {
      case ResultStatus.stored:
        statusColor = Colors.green;
        break;
      case ResultStatus.triaged:
        statusColor = Colors.blue;
        break;
      case ResultStatus.processing:
        statusColor = Colors.orange;
        break;
      default:
        statusColor = Colors.grey;
    }

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: ExpansionTile(
        leading: CircleAvatar(
          backgroundColor: statusColor.withOpacity(0.2),
          child: Icon(Icons.bug_report, color: statusColor),
        ),
        title: Text('${result.agentType} - Task ${result.taskId.substring(0, 8)}'),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Agent: ${result.agentId.substring(0, 8)}'),
            Text('Submitted: ${_formatDate(result.submittedAt)}'),
            Text('Vulnerabilities: ${result.vulnerabilities.length}'),
          ],
        ),
        trailing: Chip(
          label: Text(
            result.status.name.toUpperCase(),
            style: TextStyle(color: statusColor, fontSize: 10),
          ),
          backgroundColor: statusColor.withOpacity(0.1),
        ),
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Findings:',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                Text(result.findings.toString()),
                const SizedBox(height: 16),
                const Text(
                  'Vulnerabilities:',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                ...result.vulnerabilities.map((vuln) => _buildVulnerabilityChip(vuln)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildVulnerabilitiesList() {
    return Consumer<ResultProvider>(
      builder: (context, provider, child) {
        if (provider.isLoading) {
          return const Center(child: CircularProgressIndicator());
        }

        final vulnerabilities = provider.vulnerabilities;
        if (vulnerabilities.isEmpty) {
          return const Center(child: Text('No vulnerabilities found'));
        }

        return RefreshIndicator(
          onRefresh: () => provider.loadVulnerabilities(),
          child: ListView.builder(
            itemCount: vulnerabilities.length,
            itemBuilder: (context, index) {
              final vulnerability = vulnerabilities[index];
              return _buildVulnerabilityCard(vulnerability);
            },
          ),
        );
      },
    );
  }

  Widget _buildVulnerabilityCard(Vulnerability vulnerability) {
    Color severityColor;
    switch (vulnerability.severity) {
      case VulnerabilitySeverity.critical:
        severityColor = Colors.red;
        break;
      case VulnerabilitySeverity.high:
        severityColor = Colors.orange;
        break;
      case VulnerabilitySeverity.medium:
        severityColor = Colors.yellow;
        break;
      case VulnerabilitySeverity.low:
        severityColor = Colors.blue;
        break;
      default:
        severityColor = Colors.grey;
    }

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: ExpansionTile(
        leading: Icon(
          Icons.warning,
          color: severityColor,
          size: 32,
        ),
        title: Text(vulnerability.title),
        subtitle: Text(vulnerability.description),
        trailing: Chip(
          label: Text(
            vulnerability.severity.name.toUpperCase(),
            style: TextStyle(color: severityColor, fontSize: 10),
          ),
          backgroundColor: severityColor.withOpacity(0.1),
        ),
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (vulnerability.cve != null) ...[
                  Text('CVE: ${vulnerability.cve}'),
                  const SizedBox(height: 8),
                ],
                if (vulnerability.cwe != null) ...[
                  Text('CWE: ${vulnerability.cwe}'),
                  const SizedBox(height: 8),
                ],
                const Text(
                  'Details:',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                Text(vulnerability.details.toString()),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildVulnerabilityChip(Vulnerability vulnerability) {
    Color severityColor;
    switch (vulnerability.severity) {
      case VulnerabilitySeverity.critical:
        severityColor = Colors.red;
        break;
      case VulnerabilitySeverity.high:
        severityColor = Colors.orange;
        break;
      case VulnerabilitySeverity.medium:
        severityColor = Colors.yellow;
        break;
      case VulnerabilitySeverity.low:
        severityColor = Colors.blue;
        break;
      default:
        severityColor = Colors.grey;
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Chip(
        avatar: Icon(Icons.warning, color: severityColor, size: 16),
        label: Text(vulnerability.title),
        backgroundColor: severityColor.withOpacity(0.1),
      ),
    );
  }

  String _formatDate(DateTime date) {
    return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')} ${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}';
  }
}