import 'package:flutter/foundation.dart';
import '../models/agent_result.dart';
import '../services/result_manager.dart';

class ResultProvider extends ChangeNotifier {
  final ResultManager resultManager;
  
  List<AgentResult> _results = [];
  List<Vulnerability> _vulnerabilities = [];
  ResultStatistics? _statistics;
  bool _isLoading = false;
  String? _errorMessage;

  ResultProvider({required this.resultManager});

  // Getters
  List<AgentResult> get results => _results;
  List<Vulnerability> get vulnerabilities => _vulnerabilities;
  ResultStatistics? get statistics => _statistics;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  // Load all results
  Future<void> loadResults({String? taskId}) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _results = await resultManager.getResults(taskId: taskId);
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _errorMessage = e.toString();
      _isLoading = false;
      notifyListeners();
    }
  }

  // Ingest a new result
  Future<AgentResult?> ingestResult({
    required String taskId,
    required String agentId,
    required String agentType,
    required Map<String, dynamic> findings,
    required List<Vulnerability> vulnerabilities,
  }) async {
    _errorMessage = null;
    notifyListeners();

    try {
      final result = await resultManager.ingestResult(
        taskId: taskId,
        agentId: agentId,
        agentType: agentType,
        findings: findings,
        vulnerabilities: vulnerabilities,
      );
      _results.add(result);
      notifyListeners();
      return result;
    } catch (e) {
      _errorMessage = e.toString();
      notifyListeners();
      return null;
    }
  }

  // Load all vulnerabilities
  Future<void> loadVulnerabilities() async {
    try {
      _vulnerabilities = await resultManager.getAllVulnerabilities();
      notifyListeners();
    } catch (e) {
      _errorMessage = e.toString();
      notifyListeners();
    }
  }

  // Load statistics
  Future<void> loadStatistics() async {
    try {
      _statistics = await resultManager.getStatistics();
      notifyListeners();
    } catch (e) {
      _errorMessage = e.toString();
      notifyListeners();
    }
  }

  // Get results by agent type
  List<AgentResult> getResultsByAgentType(String agentType) {
    return _results.where((result) => result.agentType == agentType).toList();
  }

  // Get vulnerabilities by severity
  List<Vulnerability> getVulnerabilitiesBySeverity(VulnerabilitySeverity severity) {
    return _vulnerabilities.where((vuln) => vuln.severity == severity).toList();
  }

  // Get critical vulnerabilities
  List<Vulnerability> getCriticalVulnerabilities() {
    return getVulnerabilitiesBySeverity(VulnerabilitySeverity.critical);
  }

  // Refresh all data
  Future<void> refresh() async {
    await loadResults();
    await loadVulnerabilities();
    await loadStatistics();
  }

  // Clear error
  void clearError() {
    _errorMessage = null;
    notifyListeners();
  }
}