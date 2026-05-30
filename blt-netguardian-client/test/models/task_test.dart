import 'package:flutter_test/flutter_test.dart';
import 'package:blt_netguardian_client/models/task.dart';

void main() {
  group('Task Model Tests', () {
    test('Task should be created with required fields', () {
      final task = Task(
        id: '123',
        type: 'web2Crawler',
        target: 'https://example.com',
        parameters: {'depth': 3},
        status: TaskStatus.pending,
        createdAt: DateTime.now(),
      );

      expect(task.id, '123');
      expect(task.type, 'web2Crawler');
      expect(task.target, 'https://example.com');
      expect(task.status, TaskStatus.pending);
      expect(task.parameters['depth'], 3);
    });

    test('Task should serialize to JSON correctly', () {
      final now = DateTime.now();
      final task = Task(
        id: '123',
        type: 'web2Crawler',
        target: 'https://example.com',
        parameters: {'depth': 3},
        status: TaskStatus.completed,
        createdAt: now,
        completedAt: now,
        result: 'success',
      );

      final json = task.toJson();

      expect(json['id'], '123');
      expect(json['type'], 'web2Crawler');
      expect(json['target'], 'https://example.com');
      expect(json['status'], 'completed');
      expect(json['result'], 'success');
    });

    test('Task should deserialize from JSON correctly', () {
      final json = {
        'id': '123',
        'type': 'web3Monitor',
        'target': '0x1234567890123456789012345678901234567890',
        'parameters': {'network': 'ethereum'},
        'status': 'processing',
        'createdAt': '2024-01-01T00:00:00.000Z',
      };

      final task = Task.fromJson(json);

      expect(task.id, '123');
      expect(task.type, 'web3Monitor');
      expect(task.target, '0x1234567890123456789012345678901234567890');
      expect(task.status, TaskStatus.processing);
      expect(task.parameters['network'], 'ethereum');
    });

    test('Task copyWith should update only specified fields', () {
      final task = Task(
        id: '123',
        type: 'web2Crawler',
        target: 'https://example.com',
        parameters: {},
        status: TaskStatus.pending,
        createdAt: DateTime.now(),
      );

      final updatedTask = task.copyWith(
        status: TaskStatus.completed,
        result: 'success',
      );

      expect(updatedTask.id, task.id);
      expect(updatedTask.type, task.type);
      expect(updatedTask.status, TaskStatus.completed);
      expect(updatedTask.result, 'success');
    });
  });

  group('TaskStatus Tests', () {
    test('All task statuses should be available', () {
      expect(TaskStatus.values.length, 5);
      expect(TaskStatus.values.contains(TaskStatus.pending), true);
      expect(TaskStatus.values.contains(TaskStatus.queued), true);
      expect(TaskStatus.values.contains(TaskStatus.processing), true);
      expect(TaskStatus.values.contains(TaskStatus.completed), true);
      expect(TaskStatus.values.contains(TaskStatus.failed), true);
    });
  });

  group('TaskType Tests', () {
    test('All task types should be available', () {
      expect(TaskType.values.length, 5);
      expect(TaskType.values.contains(TaskType.web2Crawler), true);
      expect(TaskType.values.contains(TaskType.web3Monitor), true);
      expect(TaskType.values.contains(TaskType.staticAnalyzer), true);
      expect(TaskType.values.contains(TaskType.contractScanner), true);
      expect(TaskType.values.contains(TaskType.volunteerAgent), true);
    });
  });
}