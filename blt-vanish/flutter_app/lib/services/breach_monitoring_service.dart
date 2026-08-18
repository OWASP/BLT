import 'dart:async';
import 'package:flutter/foundation.dart';
import 'exposure_adapter.dart';
import 'exposure_identity_service.dart';
import '../models/security/exposure_event.dart';

/// Service responsible for orchestrating background monitoring of exposure events.
/// Provides hooks for app launch sync, periodic daily tasks, and manual checks.
class BreachMonitoringService {
  final List<ExposureAdapter> _adapters;
  final ExposureIdentityService _identityService;

  // In a real app, this would be backed by a local database.
  final List<ExposureEvent> _cachedEvents = [];

  BreachMonitoringService({
    required List<ExposureAdapter> adapters,
    required ExposureIdentityService identityService,
  })  : _adapters = adapters,
        _identityService = identityService;

  /// Triggers a sync on app launch. Runs asynchronously.
  void onAppLaunch(List<String> emailsToMonitor) {
    debugPrint('BreachMonitoringService: Triggering app launch sync...');
    _performSync(emailsToMonitor);
  }

  /// Entry point for a background task runner (e.g., via Workmanager).
  Future<void> onBackgroundPeriodicTask(List<String> emailsToMonitor) async {
    debugPrint('BreachMonitoringService: Triggering daily background sync...');
    await _performSync(emailsToMonitor);
  }

  /// Triggers a manual check requested by the user.
  Future<void> manualCheck(List<String> emailsToMonitor) async {
    debugPrint('BreachMonitoringService: Triggering manual check...');
    await _performSync(emailsToMonitor);
  }

  Future<void> _performSync(List<String> emails) async {
    for (var email in emails) {
      final accountHash = _identityService.generateAccountHash(email);
      for (var adapter in _adapters) {
        try {
          final newEvents = await adapter.checkEmailExposure(email, accountHash);
          _processNewEvents(newEvents);
        } catch (e) {
          debugPrint('BreachMonitoringService: Error syncing with ${adapter.providerName}: $e');
        }
      }
    }
  }

  void _processNewEvents(List<ExposureEvent> events) {
    for (var event in events) {
      // Deduplication: Only process if we haven't seen this specific event before
      if (!_cachedEvents.contains(event)) {
        _cachedEvents.add(event);
        
        if (event.urgency == 'critical' || event.urgency == 'high') {
          _triggerPushNotification(event);
        }
      }
    }
  }

  void _triggerPushNotification(ExposureEvent event) {
    // Scaffold for triggering a local push notification
    // In production, this would use flutter_local_notifications
    debugPrint('================================================');
    debugPrint('⚠️ PUSH NOTIFICATION TRIGGERED');
    debugPrint('⚠️ High-Severity Exposure Detected!');
    debugPrint('⚠️ Source: ${event.source}');
    debugPrint('================================================');
  }
}
