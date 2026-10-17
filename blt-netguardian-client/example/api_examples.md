# API Examples

This document provides examples of how to use the BLT NetGuardian Client API.

## Task Queue Examples

### Queue a Web2 Crawler Task

```dart
import 'package:blt_netguardian_client/services/task_manager.dart';

final taskManager = TaskManager(apiService: apiService);

final task = await taskManager.queueTask(
  type: 'web2Crawler',
  target: 'https://example.com',
  parameters: {
    'depth': 3,
    'timeout': 30000,
    'userAgent': 'NetGuardian/1.0',
  },
);

print('Task queued: ${task.id}');
```

### Queue a Web3 Monitor Task

```dart
final task = await taskManager.queueTask(
  type: 'web3Monitor',
  target: '0x1234567890123456789012345678901234567890',
  parameters: {
    'network': 'ethereum',
    'eventTypes': ['Transfer', 'Approval'],
  },
);
```

### Queue a Smart Contract Scanner Task

```dart
final task = await taskManager.queueTask(
  type: 'contractScanner',
  target: '0xabcdef1234567890abcdef1234567890abcdef12',
  parameters: {
    'network': 'polygon',
    'scanType': 'security',
    'includeAbi': true,
  },
);
```

## Target Registration Examples

### Register a Website Target

```dart
import 'package:blt_netguardian_client/services/target_manager.dart';
import 'package:blt_netguardian_client/models/target.dart';

final targetManager = TargetManager(apiService: apiService);

final target = await targetManager.registerTarget(
  url: 'https://example.com',
  type: TargetType.website,
  metadata: {
    'industry': 'technology',
    'priority': 'high',
  },
);

print('Target registered: ${target.id}');
```

## Result Ingestion Examples

### Ingest Web2 Crawler Results

```dart
import 'package:blt_netguardian_client/services/result_manager.dart';
import 'package:blt_netguardian_client/models/agent_result.dart';

final resultManager = ResultManager(apiService: apiService);

final result = await resultManager.ingestResult(
  taskId: 'task-123',
  agentId: 'crawler-agent-1',
  agentType: 'web2Crawler',
  findings: {
    'pagesScanned': 145,
    'linksFound': 523,
    'vulnerabilitiesDetected': 3,
  },
  vulnerabilities: [
    Vulnerability(
      id: 'vuln-1',
      title: 'SQL Injection Vulnerability',
      description: 'SQL injection detected in login form',
      severity: VulnerabilitySeverity.critical,
      cve: 'CVE-2024-12345',
      cwe: 'CWE-89',
      details: {
        'location': '/login',
        'parameter': 'username',
      },
    ),
  ],
);
```

## Error Handling

```dart
try {
  final task = await taskManager.queueTask(
    type: 'web2Crawler',
    target: 'https://example.com',
    parameters: {},
  );
} on DuplicateTaskException catch (e) {
  print('Task already exists: $e');
} on ApiException catch (e) {
  print('API error: ${e.message} (Status: ${e.statusCode})');
}
```