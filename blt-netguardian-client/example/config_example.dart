/// Example configuration for BLT NetGuardian Client
/// 
/// This file demonstrates how to configure and initialize the client
/// for different environments and use cases.

import 'package:blt_netguardian_client/services/api_service.dart';
import 'package:blt_netguardian_client/services/task_manager.dart';
import 'package:blt_netguardian_client/services/target_manager.dart';
import 'package:blt_netguardian_client/services/result_manager.dart';
import 'package:blt_netguardian_client/models/target.dart';

/// Development environment configuration
class DevelopmentConfig {
  static const String apiBaseUrl = 'https://api-dev.netguardian.example.com';
  static const int apiTimeout = 30000;
  static const bool enableLogging = true;
}

/// Production environment configuration
class ProductionConfig {
  static const String apiBaseUrl = 'https://api.netguardian.example.com';
  static const int apiTimeout = 60000;
  static const bool enableLogging = false;
}

/// Initialize client for development
void initializeDevelopment() {
  final apiService = ApiService(
    baseUrl: DevelopmentConfig.apiBaseUrl,
  );

  final taskManager = TaskManager(apiService: apiService);
  final targetManager = TargetManager(apiService: apiService);
  final resultManager = ResultManager(apiService: apiService);

  // Use the managers...
}

/// Initialize client for production
void initializeProduction() {
  final apiService = ApiService(
    baseUrl: ProductionConfig.apiBaseUrl,
  );

  final taskManager = TaskManager(apiService: apiService);
  final targetManager = TargetManager(apiService: apiService);
  final resultManager = ResultManager(apiService: apiService);

  // Use the managers...
}

/// Custom configuration example
void initializeCustom() {
  final apiService = ApiService(
    baseUrl: 'https://custom-api.example.com',
  );

  final taskManager = TaskManager(apiService: apiService);
  final targetManager = TargetManager(apiService: apiService);
  final resultManager = ResultManager(apiService: apiService);

  // Use the managers...
}

/// Example: Queue multiple task types
Future<void> queueExampleTasks(TaskManager taskManager) async {
  // Web2 crawler task
  await taskManager.queueTask(
    type: 'web2Crawler',
    target: 'https://example.com',
    parameters: {
      'depth': 3,
      'timeout': 30000,
      'followExternal': false,
    },
  );

  // Web3 monitor task
  await taskManager.queueTask(
    type: 'web3Monitor',
    target: '0x1234567890123456789012345678901234567890',
    parameters: {
      'network': 'ethereum',
      'monitorEvents': true,
    },
  );

  // Static analyzer task
  await taskManager.queueTask(
    type: 'staticAnalyzer',
    target: 'https://github.com/example/repo',
    parameters: {
      'language': 'javascript',
      'scanDepth': 'deep',
    },
  );

  // Contract scanner task
  await taskManager.queueTask(
    type: 'contractScanner',
    target: '0xabcdef1234567890abcdef1234567890abcdef12',
    parameters: {
      'network': 'polygon',
      'scanType': 'security',
    },
  );
}

/// Example: Register multiple targets
Future<void> registerExampleTargets(TargetManager targetManager) async {
  // Register website
  await targetManager.registerTarget(
    url: 'https://example.com',
    type: TargetType.website,
    metadata: {'priority': 'high'},
  );

  // Register smart contract
  await targetManager.registerTarget(
    url: '0x1234567890123456789012345678901234567890',
    type: TargetType.smartContract,
    metadata: {'network': 'ethereum'},
  );

  // Register API
  await targetManager.registerTarget(
    url: 'https://api.example.com',
    type: TargetType.api,
    metadata: {'version': 'v2'},
  );

  // Register repository
  await targetManager.registerTarget(
    url: 'https://github.com/example/repo',
    type: TargetType.repository,
    metadata: {'language': 'dart'},
  );
}