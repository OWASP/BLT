import 'package:flutter_test/flutter_test.dart';
import 'package:blt_netguardian_client/services/task_manager.dart';
import 'package:blt_netguardian_client/services/api_service.dart';
import 'package:blt_netguardian_client/models/task.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'dart:convert';

void main() {
  group('TaskManager Tests', () {
    late TaskManager taskManager;
    late MockClient mockClient;

    setUp(() {
      mockClient = MockClient((request) async {
        if (request.url.path.contains('/api/tasks/queue')) {
          final body = jsonDecode(request.body);
          final response = {
            ...body,
            'id': body['id'] ?? 'test-id',
            'status': 'queued',
          };
          return http.Response(jsonEncode(response), 200);
        }
        if (request.url.path.contains('/api/tasks')) {
          return http.Response(jsonEncode([]), 200);
        }
        return http.Response('Not Found', 404);
      });

      final apiService = ApiService(
        baseUrl: 'https://api.test.com',
        client: mockClient,
      );
      taskManager = TaskManager(apiService: apiService);
    });

    test('Duplicate detection should work', () async {
      await taskManager.queueTask(
        type: 'web2Crawler',
        target: 'https://example.com',
        parameters: {'depth': 3},
      );

      final isDuplicate = taskManager.isDuplicate(
        'web2Crawler',
        'https://example.com',
        {'depth': 3},
      );

      expect(isDuplicate, true);
    });

    test('Should throw DuplicateTaskException for duplicate tasks', () async {
      await taskManager.queueTask(
        type: 'web2Crawler',
        target: 'https://example.com',
        parameters: {'depth': 3},
      );

      expect(
        () => taskManager.queueTask(
          type: 'web2Crawler',
          target: 'https://example.com',
          parameters: {'depth': 3},
        ),
        throwsA(isA<DuplicateTaskException>()),
      );
    });

    test('Should allow same task with different parameters', () async {
      await taskManager.queueTask(
        type: 'web2Crawler',
        target: 'https://example.com',
        parameters: {'depth': 3},
      );

      // Should not throw
      await taskManager.queueTask(
        type: 'web2Crawler',
        target: 'https://example.com',
        parameters: {'depth': 5}, // Different depth
      );

      expect(true, true); // Test passes if no exception
    });

    test('Should allow skipping deduplication', () async {
      await taskManager.queueTask(
        type: 'web2Crawler',
        target: 'https://example.com',
        parameters: {'depth': 3},
      );

      // Should not throw with skipDeduplication
      await taskManager.queueTask(
        type: 'web2Crawler',
        target: 'https://example.com',
        parameters: {'depth': 3},
        skipDeduplication: true,
      );

      expect(true, true); // Test passes if no exception
    });
  });
}