import '../models/security/credential_snapshot.dart';
import 'credential_analyzer.dart';
import 'remediation_planner.dart';
import 'storage_service.dart';

/// Local-only encrypted vault service for credential hygiene snapshots.
class CredentialVaultService {
  /// Creates a vault service backed by encrypted local storage.
  CredentialVaultService({
    required StorageService storageService,
    CredentialAnalyzer analyzer = const CredentialAnalyzer(),
    RemediationPlanner planner = const RemediationPlanner(),
  })  : _storageService = storageService,
        _analyzer = analyzer,
        _planner = planner;

  final StorageService _storageService;
  final CredentialAnalyzer _analyzer;
  final RemediationPlanner _planner;

  /// Loads all stored credential snapshots.
  Future<List<CredentialSnapshot>> getSnapshots() {
    return _storageService.getCredentialSnapshots();
  }

  /// Analyzes a raw credential and returns a hash-only snapshot.
  Future<CredentialSnapshot> analyzeCredential({
    required String accountLabel,
    required String username,
    required String password,
    bool knownBreached = false,
  }) async {
    final existingSnapshots = await getSnapshots();
    return _analyzer.analyze(
      accountLabel: accountLabel,
      username: username,
      password: password,
      existingSnapshots: existingSnapshots,
      knownBreached: knownBreached,
    );
  }

  /// Saves a hash-only snapshot.
  Future<void> saveSnapshot(CredentialSnapshot snapshot) async {
    await _storageService.saveCredentialSnapshot(snapshot);
    final tasks = _planner.planForCredential(snapshot);
    for (final task in tasks) {
      await _storageService.saveRemediationTask(task);
    }
  }

  /// Deletes a stored snapshot by id.
  Future<void> deleteSnapshot(String snapshotId) {
    return _storageService.deleteCredentialSnapshot(snapshotId);
  }
}
