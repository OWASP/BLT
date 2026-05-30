import 'package:flutter/foundation.dart';
import '../models/task.dart';
import '../models/target.dart';
import '../models/agent_result.dart';
import '../services/api_service.dart';
import '../services/task_manager.dart';
import '../services/target_manager.dart';
import '../services/result_manager.dart';

class AppProvider extends ChangeNotifier {
  late final ApiService _apiService;
  late final TaskManager _taskManager;
  late final TargetManager _targetManager;
  late final ResultManager _resultManager;

  bool _isInitialized = false;
  String _baseUrl = '';
  String? _errorMessage;

  // Getters
  bool get isInitialized => _isInitialized;
  String get baseUrl => _baseUrl;
  String? get errorMessage => _errorMessage;
  TaskManager get taskManager => _taskManager;
  TargetManager get targetManager => _targetManager;
  ResultManager get resultManager => _resultManager;

  // Initialize the provider with API base URL
  void initialize(String baseUrl) {
    _baseUrl = baseUrl;
    _apiService = ApiService(baseUrl: baseUrl);
    _taskManager = TaskManager(apiService: _apiService);
    _targetManager = TargetManager(apiService: _apiService);
    _resultManager = ResultManager(apiService: _apiService);
    _isInitialized = true;
    _errorMessage = null;
    notifyListeners();
  }

  // Set error message
  void setError(String? error) {
    _errorMessage = error;
    notifyListeners();
  }

  // Clear error message
  void clearError() {
    _errorMessage = null;
    notifyListeners();
  }

  // Reset the app state
  void reset() {
    if (_isInitialized) {
      _taskManager.clearCache();
      _targetManager.clearCache();
      _resultManager.clearCache();
      _apiService.dispose();
    }
    _isInitialized = false;
    _baseUrl = '';
    _errorMessage = null;
    notifyListeners();
  }

  @override
  void dispose() {
    if (_isInitialized) {
      _apiService.dispose();
    }
    super.dispose();
  }
}