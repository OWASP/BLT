import 'package:flutter/foundation.dart';
import '../models/target.dart';
import '../services/target_manager.dart';

class TargetProvider extends ChangeNotifier {
  final TargetManager targetManager;
  
  List<Target> _targets = [];
  TargetStatistics? _statistics;
  bool _isLoading = false;
  String? _errorMessage;

  TargetProvider({required this.targetManager});

  // Getters
  List<Target> get targets => _targets;
  TargetStatistics? get statistics => _statistics;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  // Load all targets
  Future<void> loadTargets({bool? isActive}) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _targets = await targetManager.getTargets(isActive: isActive);
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _errorMessage = e.toString();
      _isLoading = false;
      notifyListeners();
    }
  }

  // Register a new target
  Future<Target?> registerTarget({
    required String url,
    required TargetType type,
    Map<String, dynamic>? metadata,
  }) async {
    _errorMessage = null;
    notifyListeners();

    try {
      final target = await targetManager.registerTarget(
        url: url,
        type: type,
        metadata: metadata,
      );
      _targets.add(target);
      notifyListeners();
      return target;
    } catch (e) {
      _errorMessage = e.toString();
      notifyListeners();
      return null;
    }
  }

  // Deactivate a target
  Future<void> deactivateTarget(String targetId) async {
    _errorMessage = null;
    notifyListeners();

    try {
      await targetManager.deactivateTarget(targetId);
      final index = _targets.indexWhere((t) => t.id == targetId);
      if (index != -1) {
        _targets[index] = _targets[index].copyWith(isActive: false);
      }
      notifyListeners();
    } catch (e) {
      _errorMessage = e.toString();
      notifyListeners();
    }
  }

  // Load statistics
  Future<void> loadStatistics() async {
    try {
      _statistics = await targetManager.getStatistics();
      notifyListeners();
    } catch (e) {
      _errorMessage = e.toString();
      notifyListeners();
    }
  }

  // Get targets by type
  List<Target> getTargetsByType(TargetType type) {
    return _targets.where((target) => target.type == type).toList();
  }

  // Get active targets
  List<Target> getActiveTargets() {
    return _targets.where((target) => target.isActive).toList();
  }

  // Refresh targets
  Future<void> refresh() async {
    await loadTargets();
    await loadStatistics();
  }

  // Clear error
  void clearError() {
    _errorMessage = null;
    notifyListeners();
  }
}