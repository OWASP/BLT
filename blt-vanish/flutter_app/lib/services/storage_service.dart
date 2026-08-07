import 'dart:convert';
import 'package:encrypt/encrypt.dart' as encrypt_pkg;
import 'package:shared_preferences/shared_preferences.dart';

import '../models/monitor_entry.dart';
import '../models/opt_out_request.dart';
import '../models/security/credential_snapshot.dart';
import '../models/security/remediation_action.dart';
import '../models/security/remediation_task.dart';
import '../models/security/risk_assessment.dart';
import '../models/security/security_alert.dart';
import '../models/user_data.dart';

/// Service for encrypted local storage of sensitive data
/// All PII is encrypted with AES-256 and stored only on device
class StorageService {
  static const String _encryptionKeyKey = 'encryption_key';
  static const String _userDataKey = 'user_data';
  static const String _requestsKey = 'opt_out_requests';
  static const String _monitorEntriesKey = 'monitor_entries';
  static const String _credentialSnapshotsKey = 'credential_snapshots';
  static const String _riskAssessmentsKey = 'risk_assessments';
  static const String _remediationTasksKey = 'remediation_tasks';
  
  late SharedPreferences _prefs;
  encrypt_pkg.Encrypter? _encrypter;
  encrypt_pkg.IV? _iv;
  
  bool _initialized = false;

  /// Initialize the storage service
  Future<void> initialize() async {
    if (_initialized) return;
    
    _prefs = await SharedPreferences.getInstance();
    await _initializeEncryption();
    _initialized = true;
  }

  /// Initialize encryption with AES-256
  Future<void> _initializeEncryption() async {
    // Try to get existing key
    String? keyString = _prefs.getString(_encryptionKeyKey);
    
    if (keyString == null) {
      // Generate new key
      final key = encrypt_pkg.Key.fromSecureRandom(32); // 256-bit key
      keyString = base64Encode(key.bytes);
      await _prefs.setString(_encryptionKeyKey, keyString);
    }
    
    final keyBytes = base64Decode(keyString);
    final key = encrypt_pkg.Key(keyBytes);
    _encrypter = encrypt_pkg.Encrypter(encrypt_pkg.AES(key));
    _iv = encrypt_pkg.IV.fromLength(16);
  }

  /// Encrypt data before storing
  String _encrypt(String data) {
    if (_encrypter == null || _iv == null) {
      throw Exception('Storage service not initialized');
    }
    final encrypted = _encrypter!.encrypt(data, iv: _iv!);
    return encrypted.base64;
  }

  /// Decrypt data after retrieving
  String _decrypt(String encryptedData) {
    if (_encrypter == null || _iv == null) {
      throw Exception('Storage service not initialized');
    }
    final encrypted = encrypt_pkg.Encrypted.fromBase64(encryptedData);
    return _encrypter!.decrypt(encrypted, iv: _iv!);
  }

  /// Save user data (encrypted)
  Future<void> saveUserData(UserData userData) async {
    final jsonString = jsonEncode(userData.toJson());
    final encrypted = _encrypt(jsonString);
    await _prefs.setString(_userDataKey, encrypted);
  }

  /// Get user data (decrypted)
  Future<UserData?> getUserData() async {
    final encrypted = _prefs.getString(_userDataKey);
    if (encrypted == null) return null;
    
    try {
      final decrypted = _decrypt(encrypted);
      final json = jsonDecode(decrypted) as Map<String, dynamic>;
      return UserData.fromJson(json);
    } catch (e) {
      // Decryption or parsing failed
      return null;
    }
  }

  /// Save opt-out request (encrypted)
  Future<void> saveRequest(OptOutRequest request) async {
    final requests = await getRequests();
    final index = requests.indexWhere((r) => r.id == request.id);
    
    if (index >= 0) {
      requests[index] = request;
    } else {
      requests.add(request);
    }
    
    final jsonString = jsonEncode(requests.map((r) => r.toJson()).toList());
    final encrypted = _encrypt(jsonString);
    await _prefs.setString(_requestsKey, encrypted);
  }

  /// Get all opt-out requests (decrypted)
  Future<List<OptOutRequest>> getRequests() async {
    final encrypted = _prefs.getString(_requestsKey);
    if (encrypted == null) return [];
    
    try {
      final decrypted = _decrypt(encrypted);
      final jsonList = jsonDecode(decrypted) as List<dynamic>;
      return jsonList
          .map((json) => OptOutRequest.fromJson(json as Map<String, dynamic>))
          .toList();
    } catch (e) {
      return [];
    }
  }

  /// Delete a request
  Future<void> deleteRequest(String requestId) async {
    final requests = await getRequests();
    requests.removeWhere((r) => r.id == requestId);
    
    final jsonString = jsonEncode(requests.map((r) => r.toJson()).toList());
    final encrypted = _encrypt(jsonString);
    await _prefs.setString(_requestsKey, encrypted);
  }

  /// Save a monitor entry (encrypted)
  Future<void> saveMonitorEntry(MonitorEntry entry) async {
    final entries = await getMonitorEntries();
    final index = entries.indexWhere((e) => e.id == entry.id);

    if (index >= 0) {
      entries[index] = entry;
    } else {
      entries.add(entry);
    }

    final jsonString = jsonEncode(entries.map((e) => e.toJson()).toList());
    final encrypted = _encrypt(jsonString);
    await _prefs.setString(_monitorEntriesKey, encrypted);
  }

  /// Get all monitor entries (decrypted)
  Future<List<MonitorEntry>> getMonitorEntries() async {
    final encrypted = _prefs.getString(_monitorEntriesKey);
    if (encrypted == null) return [];

    try {
      final decrypted = _decrypt(encrypted);
      final jsonList = jsonDecode(decrypted) as List<dynamic>;
      return jsonList
          .map((json) => MonitorEntry.fromJson(json as Map<String, dynamic>))
          .toList();
    } catch (e) {
      return [];
    }
  }

  /// Delete a monitor entry
  Future<void> deleteMonitorEntry(String entryId) async {
    final entries = await getMonitorEntries();
    entries.removeWhere((e) => e.id == entryId);

    final jsonString = jsonEncode(entries.map((e) => e.toJson()).toList());
    final encrypted = _encrypt(jsonString);
    await _prefs.setString(_monitorEntriesKey, encrypted);
  }

  /// Clear all data (use with caution!)
  Future<void> clearAllData() async {
    if (_initialized) {
      await _prefs.clear();
    }
    _initialized = false;
    _encrypter = null;
    _iv = null;
  }

  /// Export data as encrypted ZIP-compatible JSON
  Future<String> exportData() async {
    final userData = await getUserData();
    final requests = await getRequests();
    final monitorEntries = await getMonitorEntries();
    final credentialSnapshots = await getCredentialSnapshots();
    final riskAssessments = await getRiskAssessments();
    final remediationTasks = await getRemediationTasks();
    
    final exportData = {
      'version': '1.0',
      'exportedAt': DateTime.now().toIso8601String(),
      'userData': userData?.toJson(),
      'requests': requests.map((r) => r.toJson()).toList(),
      'monitorEntries': monitorEntries.map((e) => e.toJson()).toList(),
      'credentialSnapshots': credentialSnapshots
          .map((snapshot) => snapshot.toJson())
          .toList(),
      'riskAssessments': riskAssessments
          .map((assessment) => _riskAssessmentToJson(assessment))
          .toList(),
      'remediationTasks': remediationTasks
          .map((task) => task.toJson())
          .toList(),
    };
    
    final jsonString = jsonEncode(exportData);
    // Return encrypted data for export
    return _encrypt(jsonString);
  }

  /// Import data from encrypted export
  Future<void> importData(String encryptedData) async {
    try {
      final decrypted = _decrypt(encryptedData);
      final json = jsonDecode(decrypted) as Map<String, dynamic>;
      
      if (json['userData'] != null) {
        final userData = UserData.fromJson(json['userData'] as Map<String, dynamic>);
        await saveUserData(userData);
      }
      
      if (json['requests'] != null) {
        final requestsList = json['requests'] as List<dynamic>;
        for (var requestJson in requestsList) {
          final request = OptOutRequest.fromJson(requestJson as Map<String, dynamic>);
          await saveRequest(request);
        }
      }

      if (json['monitorEntries'] != null) {
        final entriesList = json['monitorEntries'] as List<dynamic>;
        for (var entryJson in entriesList) {
          final entry = MonitorEntry.fromJson(entryJson as Map<String, dynamic>);
          await saveMonitorEntry(entry);
        }
      }

      if (json['credentialSnapshots'] != null) {
        final snapshotsList = json['credentialSnapshots'] as List<dynamic>;
        for (var snapshotJson in snapshotsList) {
          final snapshot = CredentialSnapshot.fromJson(
            snapshotJson as Map<String, dynamic>,
          );
          await saveCredentialSnapshot(snapshot);
        }
      }

      if (json['riskAssessments'] != null) {
        final assessmentsList = json['riskAssessments'] as List<dynamic>;
        for (var assessmentJson in assessmentsList) {
          final assessment = _riskAssessmentFromJson(
            assessmentJson as Map<String, dynamic>,
          );
          await saveRiskAssessment(assessment);
        }
      }

      if (json['remediationTasks'] != null) {
        final tasksList = json['remediationTasks'] as List<dynamic>;
        for (var taskJson in tasksList) {
          final task = RemediationTask.fromJson(
            taskJson as Map<String, dynamic>,
          );
          await saveRemediationTask(task);
        }
      }
    } catch (error) {
      throw Exception('Failed to import data: $error');
    }
  }

  /// Save a credential snapshot (encrypted).
  Future<void> saveCredentialSnapshot(CredentialSnapshot snapshot) async {
    final snapshots = await getCredentialSnapshots();
    final index = snapshots.indexWhere((entry) => entry.id == snapshot.id);

    if (index >= 0) {
      snapshots[index] = snapshot;
    } else {
      snapshots.add(snapshot);
    }

    final jsonString =
        jsonEncode(snapshots.map((entry) => entry.toJson()).toList());
    final encrypted = _encrypt(jsonString);
    await _prefs.setString(_credentialSnapshotsKey, encrypted);
  }

  /// Get all credential snapshots (decrypted).
  Future<List<CredentialSnapshot>> getCredentialSnapshots() async {
    final encrypted = _prefs.getString(_credentialSnapshotsKey);
    if (encrypted == null) {
      return [];
    }

    try {
      final decrypted = _decrypt(encrypted);
      final jsonList = jsonDecode(decrypted) as List<dynamic>;
      return jsonList
          .map(
            (json) => CredentialSnapshot.fromJson(
              json as Map<String, dynamic>,
            ),
          )
          .toList();
    } catch (e) {
      return [];
    }
  }

  /// Delete a credential snapshot.
  Future<void> deleteCredentialSnapshot(String snapshotId) async {
    final snapshots = await getCredentialSnapshots();
    snapshots.removeWhere((entry) => entry.id == snapshotId);

    final jsonString =
        jsonEncode(snapshots.map((entry) => entry.toJson()).toList());
    final encrypted = _encrypt(jsonString);
    await _prefs.setString(_credentialSnapshotsKey, encrypted);
  }

  /// Save a risk assessment for unified triage.
  Future<void> saveRiskAssessment(RiskAssessment assessment) async {
    final assessments = await getRiskAssessments();
    final index = assessments.indexWhere((entry) => entry.id == assessment.id);

    if (index >= 0) {
      assessments[index] = assessment;
    } else {
      assessments.add(assessment);
    }

    final jsonString = jsonEncode(
      assessments.map(_riskAssessmentToJson).toList(),
    );
    final encrypted = _encrypt(jsonString);
    await _prefs.setString(_riskAssessmentsKey, encrypted);
  }

  /// Get all stored risk assessments.
  Future<List<RiskAssessment>> getRiskAssessments() async {
    final encrypted = _prefs.getString(_riskAssessmentsKey);
    if (encrypted == null) {
      return [];
    }

    try {
      final decrypted = _decrypt(encrypted);
      final jsonList = jsonDecode(decrypted) as List<dynamic>;
      return jsonList
          .map(
            (json) => _riskAssessmentFromJson(json as Map<String, dynamic>),
          )
          .toList();
    } catch (e) {
      return [];
    }
  }

  /// Delete a stored risk assessment.
  Future<void> deleteRiskAssessment(String assessmentId) async {
    final assessments = await getRiskAssessments();
    assessments.removeWhere((entry) => entry.id == assessmentId);

    final jsonString = jsonEncode(
      assessments.map(_riskAssessmentToJson).toList(),
    );
    final encrypted = _encrypt(jsonString);
    await _prefs.setString(_riskAssessmentsKey, encrypted);
  }

  /// Save a remediation task.
  Future<void> saveRemediationTask(RemediationTask task) async {
    final tasks = await getRemediationTasks();
    final index = tasks.indexWhere((entry) => entry.id == task.id);

    if (index >= 0) {
      tasks[index] = task;
    } else {
      tasks.add(task);
    }

    final jsonString = jsonEncode(tasks.map((entry) => entry.toJson()).toList());
    final encrypted = _encrypt(jsonString);
    await _prefs.setString(_remediationTasksKey, encrypted);
  }

  /// Get stored remediation tasks.
  Future<List<RemediationTask>> getRemediationTasks() async {
    final encrypted = _prefs.getString(_remediationTasksKey);
    if (encrypted == null) {
      return [];
    }

    try {
      final decrypted = _decrypt(encrypted);
      final jsonList = jsonDecode(decrypted) as List<dynamic>;
      return jsonList
          .map((json) => RemediationTask.fromJson(json as Map<String, dynamic>))
          .toList();
    } catch (e) {
      return [];
    }
  }

  /// Delete a remediation task.
  Future<void> deleteRemediationTask(String taskId) async {
    final tasks = await getRemediationTasks();
    tasks.removeWhere((entry) => entry.id == taskId);

    final jsonString = jsonEncode(tasks.map((entry) => entry.toJson()).toList());
    final encrypted = _encrypt(jsonString);
    await _prefs.setString(_remediationTasksKey, encrypted);
  }

  Map<String, dynamic> _riskAssessmentToJson(RiskAssessment assessment) {
    return {
      'id': assessment.id,
      'targetAsset': assessment.targetAsset,
      'severity': assessment.severity.name,
      'finalScore': assessment.finalScore,
      'localSignals': assessment.localSignals,
      'enrichmentSignals': assessment.enrichmentSignals,
      'assessedAt': assessment.assessedAt.toIso8601String(),
      'alerts': assessment.alerts.map(_securityAlertToJson).toList(),
      'recommendedActions':
          assessment.recommendedActions.map(_remediationActionToJson).toList(),
    };
  }

  RiskAssessment _riskAssessmentFromJson(Map<String, dynamic> json) {
    return RiskAssessment(
      id: json['id'] as String,
      targetAsset: json['targetAsset'] as String,
      severity: _severityFromName(json['severity'] as String),
      finalScore: (json['finalScore'] as num).toDouble(),
      localSignals: Map<String, double>.from(
        (json['localSignals'] as Map<dynamic, dynamic>).map(
          (key, value) => MapEntry(key as String, (value as num).toDouble()),
        ),
      ),
      enrichmentSignals: Map<String, String>.from(
        json['enrichmentSignals'] as Map<dynamic, dynamic>,
      ),
      assessedAt: DateTime.parse(json['assessedAt'] as String),
      alerts: (json['alerts'] as List<dynamic>)
          .map((alert) => _securityAlertFromJson(alert as Map<String, dynamic>))
          .toList(),
      recommendedActions: (json['recommendedActions'] as List<dynamic>)
          .map(
            (action) =>
                _remediationActionFromJson(action as Map<String, dynamic>),
          )
          .toList(),
    );
  }

  Map<String, dynamic> _securityAlertToJson(SecurityAlert alert) {
    return {
      'id': alert.id,
      'type': alert.type.name,
      'severity': alert.severity.name,
      'confidence': alert.confidence,
      'reasonCodes': alert.reasonCodes,
      'createdAt': alert.createdAt.toIso8601String(),
    };
  }

  SecurityAlert _securityAlertFromJson(Map<String, dynamic> json) {
    return SecurityAlert(
      id: json['id'] as String,
      type: AlertType.values.firstWhere(
        (type) => type.name == json['type'],
        orElse: () => AlertType.phishing,
      ),
      severity: _severityFromName(json['severity'] as String),
      confidence: (json['confidence'] as num).toDouble(),
      reasonCodes: (json['reasonCodes'] as List<dynamic>)
          .map((code) => code as String)
          .toList(),
      createdAt: DateTime.parse(json['createdAt'] as String),
    );
  }

  Map<String, dynamic> _remediationActionToJson(RemediationAction action) {
    return {
      'id': action.id,
      'title': action.title,
      'description': action.description,
      'urgency': action.urgency.name,
      'deepLink': action.deepLink,
    };
  }

  RemediationAction _remediationActionFromJson(Map<String, dynamic> json) {
    return RemediationAction(
      id: json['id'] as String,
      title: json['title'] as String,
      description: json['description'] as String,
      urgency: _severityFromName(json['urgency'] as String),
      deepLink: json['deepLink'] as String?,
    );
  }

  AlertSeverity _severityFromName(String name) {
    return AlertSeverity.values.firstWhere(
      (severity) => severity.name == name,
      orElse: () => AlertSeverity.low,
    );
  }
}
