import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/task.dart';
import '../models/target.dart';
import '../models/agent_result.dart';

class ApiService {
  final String baseUrl;
  final http.Client client;

  ApiService({
    required this.baseUrl,
    http.Client? client,
  }) : client = client ?? http.Client();

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
      };

  // Task Queue Endpoints
  Future<Task> queueTask(Task task) async {
    final response = await client.post(
      Uri.parse('$baseUrl/api/tasks/queue'),
      headers: _headers,
      body: jsonEncode(task.toJson()),
    );

    if (response.statusCode == 200 || response.statusCode == 201) {
      return Task.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
    } else {
      throw ApiException(
        'Failed to queue task: ${response.statusCode}',
        response.statusCode,
      );
    }
  }

  Future<List<Task>> getTasks({TaskStatus? status}) async {
    final queryParams = status != null ? '?status=${status.name}' : '';
    final response = await client.get(
      Uri.parse('$baseUrl/api/tasks$queryParams'),
      headers: _headers,
    );

    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body) as List<dynamic>;
      return data
          .map((json) => Task.fromJson(json as Map<String, dynamic>))
          .toList();
    } else {
      throw ApiException(
        'Failed to get tasks: ${response.statusCode}',
        response.statusCode,
      );
    }
  }

  Future<Task> getTask(String taskId) async {
    final response = await client.get(
      Uri.parse('$baseUrl/api/tasks/$taskId'),
      headers: _headers,
    );

    if (response.statusCode == 200) {
      return Task.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
    } else {
      throw ApiException(
        'Failed to get task: ${response.statusCode}',
        response.statusCode,
      );
    }
  }

  // Target Registration Endpoints
  Future<Target> registerTarget(Target target) async {
    final response = await client.post(
      Uri.parse('$baseUrl/api/targets/register'),
      headers: _headers,
      body: jsonEncode(target.toJson()),
    );

    if (response.statusCode == 200 || response.statusCode == 201) {
      return Target.fromJson(
          jsonDecode(response.body) as Map<String, dynamic>);
    } else {
      throw ApiException(
        'Failed to register target: ${response.statusCode}',
        response.statusCode,
      );
    }
  }

  Future<List<Target>> getTargets({bool? isActive}) async {
    final queryParams = isActive != null ? '?isActive=$isActive' : '';
    final response = await client.get(
      Uri.parse('$baseUrl/api/targets$queryParams'),
      headers: _headers,
    );

    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body) as List<dynamic>;
      return data
          .map((json) => Target.fromJson(json as Map<String, dynamic>))
          .toList();
    } else {
      throw ApiException(
        'Failed to get targets: ${response.statusCode}',
        response.statusCode,
      );
    }
  }

  Future<Target> getTarget(String targetId) async {
    final response = await client.get(
      Uri.parse('$baseUrl/api/targets/$targetId'),
      headers: _headers,
    );

    if (response.statusCode == 200) {
      return Target.fromJson(
          jsonDecode(response.body) as Map<String, dynamic>);
    } else {
      throw ApiException(
        'Failed to get target: ${response.statusCode}',
        response.statusCode,
      );
    }
  }

  Future<void> deactivateTarget(String targetId) async {
    final response = await client.delete(
      Uri.parse('$baseUrl/api/targets/$targetId'),
      headers: _headers,
    );

    if (response.statusCode != 200 && response.statusCode != 204) {
      throw ApiException(
        'Failed to deactivate target: ${response.statusCode}',
        response.statusCode,
      );
    }
  }

  // Agent Result Ingestion Endpoints
  Future<AgentResult> ingestResult(AgentResult result) async {
    final response = await client.post(
      Uri.parse('$baseUrl/api/results/ingest'),
      headers: _headers,
      body: jsonEncode(result.toJson()),
    );

    if (response.statusCode == 200 || response.statusCode == 201) {
      return AgentResult.fromJson(
          jsonDecode(response.body) as Map<String, dynamic>);
    } else {
      throw ApiException(
        'Failed to ingest result: ${response.statusCode}',
        response.statusCode,
      );
    }
  }

  Future<List<AgentResult>> getResults({String? taskId}) async {
    final queryParams = taskId != null ? '?taskId=$taskId' : '';
    final response = await client.get(
      Uri.parse('$baseUrl/api/results$queryParams'),
      headers: _headers,
    );

    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body) as List<dynamic>;
      return data
          .map((json) => AgentResult.fromJson(json as Map<String, dynamic>))
          .toList();
    } else {
      throw ApiException(
        'Failed to get results: ${response.statusCode}',
        response.statusCode,
      );
    }
  }

  Future<AgentResult> getResult(String resultId) async {
    final response = await client.get(
      Uri.parse('$baseUrl/api/results/$resultId'),
      headers: _headers,
    );

    if (response.statusCode == 200) {
      return AgentResult.fromJson(
          jsonDecode(response.body) as Map<String, dynamic>);
    } else {
      throw ApiException(
        'Failed to get result: ${response.statusCode}',
        response.statusCode,
      );
    }
  }

  void dispose() {
    client.close();
  }
}

class ApiException implements Exception {
  final String message;
  final int statusCode;

  ApiException(this.message, this.statusCode);

  @override
  String toString() => 'ApiException: $message (Status: $statusCode)';
}