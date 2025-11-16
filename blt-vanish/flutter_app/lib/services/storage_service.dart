import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:encrypt/encrypt.dart' as encrypt_pkg;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/user_data.dart';
import '../models/opt_out_request.dart';

/// Service for encrypted local storage of sensitive data
/// All PII is encrypted with AES-256 and stored only on device
class StorageService {
  static const String _encryptionKeyKey = 'encryption_key';
  static const String _userDataKey = 'user_data';
  static const String _requestsKey = 'opt_out_requests';
  
  final FlutterSecureStorage _secureStorage = const FlutterSecureStorage();
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
    String? keyString = await _secureStorage.read(key: _encryptionKeyKey);
    
    if (keyString == null) {
      // Generate new key
      final key = encrypt_pkg.Key.fromSecureRandom(32); // 256-bit key
      keyString = base64Encode(key.bytes);
      await _secureStorage.write(key: _encryptionKeyKey, value: keyString);
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

  /// Clear all data (use with caution!)
  Future<void> clearAllData() async {
    await _prefs.clear();
    await _secureStorage.deleteAll();
    _initialized = false;
  }

  /// Export data as encrypted ZIP-compatible JSON
  Future<String> exportData() async {
    final userData = await getUserData();
    final requests = await getRequests();
    
    final exportData = {
      'version': '1.0',
      'exportedAt': DateTime.now().toIso8601String(),
      'userData': userData?.toJson(),
      'requests': requests.map((r) => r.toJson()).toList(),
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
    } catch (e) {
      throw Exception('Failed to import data: Invalid format or decryption failed');
    }
  }
}
