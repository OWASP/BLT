import 'dart:collection';
import 'package:uuid/uuid.dart';
import '../models/task.dart';
import 'api_service.dart';

class TaskManager {
  final ApiService apiService;
  final Map<String, Task> _taskCache = {};
  final Set<String> _taskHashes = {};
  final Uuid _uuid = const Uuid();

  TaskManager({required this.apiService});

  // Generate a unique hash for task deduplication
  String _generateTaskHash(String type, String target, Map<String, dynamic> parameters) {
    final sortedParams = SplayTreeMap<String, dynamic>.from(parameters);
    return '$type:$target:${sortedParams.toString()}';
  }

  // Check if task already exists (deduplication)
  bool isDuplicate(String type, String target, Map<String, dynamic> parameters) {
    final hash = _generateTaskHash(type, target, parameters);
    return _taskHashes.contains(hash);
  }

  // Queue a new task with deduplication
  Future<Task> queueTask({
    required String type,
    required String target,
    required Map<String, dynamic> parameters,
    bool skipDeduplication = false,
  }) async {
    if (!skipDeduplication && isDuplicate(type, target, parameters)) {
      throw DuplicateTaskException('Task already exists in queue');
    }

    final task = Task(
      id: _uuid.v4(),
      type: type,
      target: target,
      parameters: parameters,
      status: TaskStatus.pending,
      createdAt: DateTime.now(),
    );

    final queuedTask = await apiService.queueTask(task);
    
    // Update cache and hash set
    _taskCache[queuedTask.id] = queuedTask;
    _taskHashes.add(_generateTaskHash(type, target, parameters));

    return queuedTask;
  }

  // Get task by ID
  Future<Task> getTask(String taskId) async {
    // Check cache first
    if (_taskCache.containsKey(taskId)) {
      return _taskCache[taskId]!;
    }

    final task = await apiService.getTask(taskId);
    _taskCache[taskId] = task;
    return task;
  }

  // Get all tasks with optional status filter
  Future<List<Task>> getTasks({TaskStatus? status}) async {
    final tasks = await apiService.getTasks(status: status);
    
    // Update cache
    for (final task in tasks) {
      _taskCache[task.id] = task;
      _taskHashes.add(_generateTaskHash(task.type, task.target, task.parameters));
    }

    return tasks;
  }

  // Get tasks by type
  Future<List<Task>> getTasksByType(String type) async {
    final allTasks = await getTasks();
    return allTasks.where((task) => task.type == type).toList();
  }

  // Get pending tasks
  Future<List<Task>> getPendingTasks() async {
    return await getTasks(status: TaskStatus.pending);
  }

  // Get completed tasks
  Future<List<Task>> getCompletedTasks() async {
    return await getTasks(status: TaskStatus.completed);
  }

  // Get failed tasks
  Future<List<Task>> getFailedTasks() async {
    return await getTasks(status: TaskStatus.failed);
  }

  // Update local task state
  void updateTaskState(String taskId, TaskStatus status, {String? result, String? error}) {
    if (_taskCache.containsKey(taskId)) {
      _taskCache[taskId] = _taskCache[taskId]!.copyWith(
        status: status,
        result: result,
        error: error,
        completedAt: status == TaskStatus.completed || status == TaskStatus.failed
            ? DateTime.now()
            : null,
      );
    }
  }

  // Clear cache
  void clearCache() {
    _taskCache.clear();
    _taskHashes.clear();
  }

  // Get task statistics
  Future<TaskStatistics> getStatistics() async {
    final tasks = await getTasks();
    
    return TaskStatistics(
      total: tasks.length,
      pending: tasks.where((t) => t.status == TaskStatus.pending).length,
      queued: tasks.where((t) => t.status == TaskStatus.queued).length,
      processing: tasks.where((t) => t.status == TaskStatus.processing).length,
      completed: tasks.where((t) => t.status == TaskStatus.completed).length,
      failed: tasks.where((t) => t.status == TaskStatus.failed).length,
    );
  }
}

class TaskStatistics {
  final int total;
  final int pending;
  final int queued;
  final int processing;
  final int completed;
  final int failed;

  TaskStatistics({
    required this.total,
    required this.pending,
    required this.queued,
    required this.processing,
    required this.completed,
    required this.failed,
  });
}

class DuplicateTaskException implements Exception {
  final String message;
  DuplicateTaskException(this.message);

  @override
  String toString() => 'DuplicateTaskException: $message';
}