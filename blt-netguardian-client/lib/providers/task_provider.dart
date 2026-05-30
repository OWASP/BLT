import 'package:flutter/foundation.dart';
import '../models/task.dart';
import '../services/task_manager.dart';

class TaskProvider extends ChangeNotifier {
  final TaskManager taskManager;
  
  List<Task> _tasks = [];
  TaskStatistics? _statistics;
  bool _isLoading = false;
  String? _errorMessage;

  TaskProvider({required this.taskManager});

  // Getters
  List<Task> get tasks => _tasks;
  TaskStatistics? get statistics => _statistics;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  // Load all tasks
  Future<void> loadTasks({TaskStatus? status}) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _tasks = await taskManager.getTasks(status: status);
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _errorMessage = e.toString();
      _isLoading = false;
      notifyListeners();
    }
  }

  // Queue a new task
  Future<Task?> queueTask({
    required String type,
    required String target,
    required Map<String, dynamic> parameters,
  }) async {
    _errorMessage = null;
    notifyListeners();

    try {
      final task = await taskManager.queueTask(
        type: type,
        target: target,
        parameters: parameters,
      );
      _tasks.add(task);
      notifyListeners();
      return task;
    } catch (e) {
      _errorMessage = e.toString();
      notifyListeners();
      return null;
    }
  }

  // Load statistics
  Future<void> loadStatistics() async {
    try {
      _statistics = await taskManager.getStatistics();
      notifyListeners();
    } catch (e) {
      _errorMessage = e.toString();
      notifyListeners();
    }
  }

  // Get tasks by type
  List<Task> getTasksByType(String type) {
    return _tasks.where((task) => task.type == type).toList();
  }

  // Get tasks by status
  List<Task> getTasksByStatus(TaskStatus status) {
    return _tasks.where((task) => task.status == status).toList();
  }

  // Refresh tasks
  Future<void> refresh() async {
    await loadTasks();
    await loadStatistics();
  }

  // Clear error
  void clearError() {
    _errorMessage = null;
    notifyListeners();
  }
}