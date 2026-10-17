import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'package:http/http.dart' as http;
import '../models/security/exposure_event.dart';

/// Abstract adapter interface for external breach/exposure services.
abstract class ExposureAdapter {
  String get providerName;

  /// Checks if a given email is present in the exposure dataset.
  Future<List<ExposureEvent>> checkEmailExposure(String email, String accountHash);

  /// Checks if a given password is present in the exposure dataset.
  Future<List<ExposureEvent>> checkPasswordExposure(String password, String accountHash);
}

/// Have I Been Pwned (HIBP) implementation.
class HibpExposureAdapter implements ExposureAdapter {
  final String _userAgent = 'BLT-Vanish-App';
  // Note: For a production app, the API key should be injected securely.
  final String? _apiKey;

  HibpExposureAdapter({String? apiKey}) : _apiKey = apiKey;

  @override
  String get providerName => 'HIBP';

  @override
  Future<List<ExposureEvent>> checkEmailExposure(String email, String accountHash) async {
    // HIBP Breached Accounts endpoint
    // Requires API key and user-agent.
    if (_apiKey == null || _apiKey!.isEmpty) {
      return []; // Fast fail if no API key is provided
    }

    final encodedEmail = Uri.encodeComponent(email.trim().toLowerCase());
    final url = Uri.parse('https://haveibeenpwned.com/api/v3/breachedaccount/$encodedEmail');

    try {
      final response = await http.get(
        url,
        headers: {
          'hibp-api-key': _apiKey!,
          'user-agent': _userAgent,
        },
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        return data.map((json) => _parseHibpBreach(json, accountHash)).toList();
      } else if (response.statusCode == 404) {
        // 404 means no breaches found
        return [];
      } else {
        // e.g., 429 Too Many Requests
        print('HIBP email check failed with status: ${response.statusCode}');
        return [];
      }
    } catch (e) {
      print('HIBP email check error: $e');
      return [];
    }
  }

  @override
  Future<List<ExposureEvent>> checkPasswordExposure(String password, String accountHash) async {
    // k-anonymity: SHA-1 hash the password, send first 5 chars
    final bytes = utf8.encode(password);
    final digest = sha1.convert(bytes);
    final hash = digest.toString().toUpperCase();
    final prefix = hash.substring(0, 5);
    final suffix = hash.substring(5);

    final url = Uri.parse('https://api.pwnedpasswords.com/range/$prefix');

    try {
      final response = await http.get(url, headers: {'user-agent': _userAgent});

      if (response.statusCode == 200) {
        final lines = response.body.split('\n');
        for (var line in lines) {
          final parts = line.split(':');
          if (parts.length == 2 && parts[0].trim() == suffix) {
            // Password found in breaches
            return [
              ExposureEvent(
                source: providerName,
                occurredAt: DateTime.now(), // Real breach date unknown for pwnedpasswords
                urgency: 'critical',
                confidence: 1.0,
                accountHash: accountHash,
              )
            ];
          }
        }
      }
      return [];
    } catch (e) {
      print('HIBP password check error: $e');
      return [];
    }
  }

  /// Parses a standard HIBP breach JSON payload into our normalized ExposureEvent.
  ExposureEvent _parseHibpBreach(Map<String, dynamic> json, String accountHash) {
    // Default to medium urgency, boost to high if sensitive data is involved
    String urgency = 'medium';
    if (json['DataClasses'] != null) {
      final dataClasses = List<String>.from(json['DataClasses']);
      if (dataClasses.contains('Passwords') || dataClasses.contains('SSN')) {
        urgency = 'high';
      }
    }

    DateTime date;
    try {
      date = DateTime.parse(json['BreachDate'] ?? json['AddedDate'] ?? DateTime.now().toIso8601String());
    } catch (_) {
      date = DateTime.now();
    }

    return ExposureEvent(
      source: 'HIBP: ${json['Name'] ?? 'Unknown'}',
      occurredAt: date,
      urgency: urgency,
      confidence: 1.0, // HIBP data is generally high confidence
      accountHash: accountHash,
    );
  }
}
