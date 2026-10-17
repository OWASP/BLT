import 'package:uuid/uuid.dart';
import '../models/target.dart';
import 'api_service.dart';

class TargetManager {
  final ApiService apiService;
  final Map<String, Target> _targetCache = {};
  final Set<String> _targetUrls = {};
  final Uuid _uuid = const Uuid();

  TargetManager({required this.apiService});

  // Check if target URL is already registered
  bool isUrlRegistered(String url) {
    return _targetUrls.contains(url);
  }

  // Register a new target
  Future<Target> registerTarget({
    required String url,
    required TargetType type,
    Map<String, dynamic>? metadata,
  }) async {
    if (isUrlRegistered(url)) {
      throw DuplicateTargetException('Target URL already registered');
    }

    final target = Target(
      id: _uuid.v4(),
      url: url,
      type: type,
      metadata: metadata ?? {},
      registeredAt: DateTime.now(),
      isActive: true,
    );

    final registeredTarget = await apiService.registerTarget(target);
    
    // Update cache
    _targetCache[registeredTarget.id] = registeredTarget;
    _targetUrls.add(url);

    return registeredTarget;
  }

  // Get target by ID
  Future<Target> getTarget(String targetId) async {
    // Check cache first
    if (_targetCache.containsKey(targetId)) {
      return _targetCache[targetId]!;
    }

    final target = await apiService.getTarget(targetId);
    _targetCache[targetId] = target;
    _targetUrls.add(target.url);
    return target;
  }

  // Get all targets
  Future<List<Target>> getTargets({bool? isActive}) async {
    final targets = await apiService.getTargets(isActive: isActive);
    
    // Update cache
    for (final target in targets) {
      _targetCache[target.id] = target;
      _targetUrls.add(target.url);
    }

    return targets;
  }

  // Get active targets
  Future<List<Target>> getActiveTargets() async {
    return await getTargets(isActive: true);
  }

  // Get targets by type
  Future<List<Target>> getTargetsByType(TargetType type) async {
    final allTargets = await getTargets();
    return allTargets.where((target) => target.type == type).toList();
  }

  // Deactivate a target
  Future<void> deactivateTarget(String targetId) async {
    await apiService.deactivateTarget(targetId);
    
    // Update cache
    if (_targetCache.containsKey(targetId)) {
      final target = _targetCache[targetId]!;
      _targetCache[targetId] = target.copyWith(isActive: false);
      _targetUrls.remove(target.url);
    }
  }

  // Clear cache
  void clearCache() {
    _targetCache.clear();
    _targetUrls.clear();
  }

  // Get target statistics
  Future<TargetStatistics> getStatistics() async {
    final targets = await getTargets();
    
    return TargetStatistics(
      total: targets.length,
      active: targets.where((t) => t.isActive).length,
      inactive: targets.where((t) => !t.isActive).length,
      websites: targets.where((t) => t.type == TargetType.website).length,
      smartContracts: targets.where((t) => t.type == TargetType.smartContract).length,
      apis: targets.where((t) => t.type == TargetType.api).length,
      repositories: targets.where((t) => t.type == TargetType.repository).length,
    );
  }
}

class TargetStatistics {
  final int total;
  final int active;
  final int inactive;
  final int websites;
  final int smartContracts;
  final int apis;
  final int repositories;

  TargetStatistics({
    required this.total,
    required this.active,
    required this.inactive,
    required this.websites,
    required this.smartContracts,
    required this.apis,
    required this.repositories,
  });
}

class DuplicateTargetException implements Exception {
  final String message;
  DuplicateTargetException(this.message);

  @override
  String toString() => 'DuplicateTargetException: $message';
}