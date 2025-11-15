import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/broker.dart';

/// Service for fetching broker data from Cloudflare Workers or local fallback
/// NO USER PII IS EVER TRANSMITTED
class BrokerService {
  // Cloudflare Workers endpoint (when deployed)
  static const String _workersBaseUrl = 'https://selferase.workers.dev';
  
  // Fallback to local/GitHub data
  static const String _fallbackUrl = 'https://raw.githubusercontent.com/OWASP-BLT/SelfErase/main/data/brokers/brokers.json';
  
  // Cache for offline support
  List<Broker>? _cachedBrokers;
  DateTime? _lastFetch;
  static const Duration _cacheExpiry = Duration(hours: 24);

  /// Fetch list of brokers (public data only, no PII)
  Future<List<Broker>> getBrokers({bool forceRefresh = false}) async {
    // Return cached data if available and not expired
    if (!forceRefresh && 
        _cachedBrokers != null && 
        _lastFetch != null &&
        DateTime.now().difference(_lastFetch!) < _cacheExpiry) {
      return _cachedBrokers!;
    }

    try {
      // Try Cloudflare Workers first
      final response = await http.get(
        Uri.parse('$_workersBaseUrl/api/brokers'),
        headers: {'Accept': 'application/json'},
      ).timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        final jsonList = jsonDecode(response.body) as List<dynamic>;
        _cachedBrokers = jsonList
            .map((json) => Broker.fromJson(json as Map<String, dynamic>))
            .toList();
        _lastFetch = DateTime.now();
        return _cachedBrokers!;
      }
    } catch (e) {
      // Workers unavailable, try fallback
    }

    try {
      // Fallback to GitHub/local
      final response = await http.get(
        Uri.parse(_fallbackUrl),
        headers: {'Accept': 'application/json'},
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final jsonList = jsonDecode(response.body) as List<dynamic>;
        _cachedBrokers = jsonList
            .map((json) => Broker.fromJson(json as Map<String, dynamic>))
            .toList();
        _lastFetch = DateTime.now();
        return _cachedBrokers!;
      }
    } catch (e) {
      // Both failed
    }

    // Return cached data even if expired, or empty list
    return _cachedBrokers ?? _getDefaultBrokers();
  }

  /// Get broker by ID
  Future<Broker?> getBrokerById(String id) async {
    final brokers = await getBrokers();
    try {
      return brokers.firstWhere((b) => b.id == id);
    } catch (e) {
      return null;
    }
  }

  /// Search brokers by name or category
  Future<List<Broker>> searchBrokers(String query) async {
    final brokers = await getBrokers();
    final lowerQuery = query.toLowerCase();
    
    return brokers.where((broker) {
      return broker.name.toLowerCase().contains(lowerQuery) ||
             broker.description.toLowerCase().contains(lowerQuery) ||
             broker.category.toLowerCase().contains(lowerQuery);
    }).toList();
  }

  /// Get brokers by category
  Future<List<Broker>> getBrokersByCategory(String category) async {
    final brokers = await getBrokers();
    return brokers.where((b) => b.category == category).toList();
  }

  /// Get all categories
  Future<List<String>> getCategories() async {
    final brokers = await getBrokers();
    final categories = brokers.map((b) => b.category).toSet().toList();
    categories.sort();
    return categories;
  }

  /// Check broker health status (from Workers)
  Future<Map<String, dynamic>> getBrokerHealth(String brokerId) async {
    try {
      final response = await http.get(
        Uri.parse('$_workersBaseUrl/api/health/$brokerId'),
        headers: {'Accept': 'application/json'},
      ).timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      // Health check unavailable
    }

    return {'status': 'unknown', 'message': 'Health check unavailable'};
  }

  /// Get opt-out template
  Future<String> getOptOutTemplate(String templateId) async {
    try {
      final response = await http.get(
        Uri.parse('$_workersBaseUrl/api/templates/$templateId'),
        headers: {'Accept': 'text/plain'},
      ).timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        return response.body;
      }
    } catch (e) {
      // Template unavailable
    }

    return _getDefaultTemplate();
  }

  /// Default brokers for offline/fallback use
  List<Broker> _getDefaultBrokers() {
    // Minimal default broker list for offline functionality
    return [
      Broker(
        id: 'example-broker-1',
        name: 'Example Data Broker',
        description: 'A sample data broker for demonstration',
        website: 'https://example.com',
        optOutUrl: 'https://example.com/opt-out',
        category: 'People Search',
        dataTypes: ['name', 'address', 'phone', 'email'],
        optOutMethod: OptOutMethod(
          type: 'online_form',
          instructions: 'Visit the opt-out page and fill out the form',
          steps: [
            'Go to opt-out page',
            'Enter your information',
            'Submit the form',
            'Check your email for confirmation',
          ],
        ),
        requiredFields: ['firstName', 'lastName', 'email'],
        estimatedResponseDays: 30,
        notes: 'This is a placeholder broker for demonstration',
      ),
    ];
  }

  /// Default opt-out template
  String _getDefaultTemplate() {
    return '''Dear [Broker Name],

I am writing to request the removal of my personal information from your database under my rights pursuant to GDPR, CCPA, and other applicable privacy laws.

Personal Information to Remove:
Name: [Full Name]
Email: [Email Address]
Phone: [Phone Number]
Address: [Street Address], [City], [State] [Zip Code]

Please confirm receipt of this request and provide information about when my data will be removed.

Thank you,
[Full Name]
''';
  }

  /// Clear cache
  void clearCache() {
    _cachedBrokers = null;
    _lastFetch = null;
  }
}
