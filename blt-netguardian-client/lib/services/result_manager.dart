import 'package:uuid/uuid.dart';
import '../models/agent_result.dart';
import 'api_service.dart';

class ResultManager {
  final ApiService apiService;
  final Map<String, AgentResult> _resultCache = {};
  final Uuid _uuid = const Uuid();

  ResultManager({required this.apiService});

  // Ingest agent result
  Future<AgentResult> ingestResult({
    required String taskId,
    required String agentId,
    required String agentType,
    required Map<String, dynamic> findings,
    required List<Vulnerability> vulnerabilities,
  }) async {
    final result = AgentResult(
      id: _uuid.v4(),
      taskId: taskId,
      agentId: agentId,
      agentType: agentType,
      findings: findings,
      vulnerabilities: vulnerabilities,
      submittedAt: DateTime.now(),
      status: ResultStatus.pending,
    );

    final ingestedResult = await apiService.ingestResult(result);
    
    // Update cache
    _resultCache[ingestedResult.id] = ingestedResult;

    return ingestedResult;
  }

  // Get result by ID
  Future<AgentResult> getResult(String resultId) async {
    // Check cache first
    if (_resultCache.containsKey(resultId)) {
      return _resultCache[resultId]!;
    }

    final result = await apiService.getResult(resultId);
    _resultCache[resultId] = result;
    return result;
  }

  // Get all results
  Future<List<AgentResult>> getResults({String? taskId}) async {
    final results = await apiService.getResults(taskId: taskId);
    
    // Update cache
    for (final result in results) {
      _resultCache[result.id] = result;
    }

    return results;
  }

  // Get results by task
  Future<List<AgentResult>> getResultsByTask(String taskId) async {
    return await getResults(taskId: taskId);
  }

  // Get results by agent
  Future<List<AgentResult>> getResultsByAgent(String agentId) async {
    final allResults = await getResults();
    return allResults.where((result) => result.agentId == agentId).toList();
  }

  // Get results by agent type
  Future<List<AgentResult>> getResultsByAgentType(String agentType) async {
    final allResults = await getResults();
    return allResults.where((result) => result.agentType == agentType).toList();
  }

  // Get all vulnerabilities from results
  Future<List<Vulnerability>> getAllVulnerabilities() async {
    final results = await getResults();
    final vulnerabilities = <Vulnerability>[];
    
    for (final result in results) {
      vulnerabilities.addAll(result.vulnerabilities);
    }
    
    return vulnerabilities;
  }

  // Get vulnerabilities by severity
  Future<List<Vulnerability>> getVulnerabilitiesBySeverity(
      VulnerabilitySeverity severity) async {
    final allVulnerabilities = await getAllVulnerabilities();
    return allVulnerabilities
        .where((vuln) => vuln.severity == severity)
        .toList();
  }

  // Get critical vulnerabilities
  Future<List<Vulnerability>> getCriticalVulnerabilities() async {
    return await getVulnerabilitiesBySeverity(VulnerabilitySeverity.critical);
  }

  // Get high severity vulnerabilities
  Future<List<Vulnerability>> getHighSeverityVulnerabilities() async {
    return await getVulnerabilitiesBySeverity(VulnerabilitySeverity.high);
  }

  // Clear cache
  void clearCache() {
    _resultCache.clear();
  }

  // Get result statistics
  Future<ResultStatistics> getStatistics() async {
    final results = await getResults();
    final allVulnerabilities = await getAllVulnerabilities();
    
    return ResultStatistics(
      totalResults: results.length,
      pending: results.where((r) => r.status == ResultStatus.pending).length,
      processing: results.where((r) => r.status == ResultStatus.processing).length,
      triaged: results.where((r) => r.status == ResultStatus.triaged).length,
      stored: results.where((r) => r.status == ResultStatus.stored).length,
      totalVulnerabilities: allVulnerabilities.length,
      criticalVulnerabilities: allVulnerabilities
          .where((v) => v.severity == VulnerabilitySeverity.critical)
          .length,
      highVulnerabilities: allVulnerabilities
          .where((v) => v.severity == VulnerabilitySeverity.high)
          .length,
      mediumVulnerabilities: allVulnerabilities
          .where((v) => v.severity == VulnerabilitySeverity.medium)
          .length,
      lowVulnerabilities: allVulnerabilities
          .where((v) => v.severity == VulnerabilitySeverity.low)
          .length,
    );
  }
}

class ResultStatistics {
  final int totalResults;
  final int pending;
  final int processing;
  final int triaged;
  final int stored;
  final int totalVulnerabilities;
  final int criticalVulnerabilities;
  final int highVulnerabilities;
  final int mediumVulnerabilities;
  final int lowVulnerabilities;

  ResultStatistics({
    required this.totalResults,
    required this.pending,
    required this.processing,
    required this.triaged,
    required this.stored,
    required this.totalVulnerabilities,
    required this.criticalVulnerabilities,
    required this.highVulnerabilities,
    required this.mediumVulnerabilities,
    required this.lowVulnerabilities,
  });
}