// Removed unused material import.
import 'package:shared_preferences/shared_preferences.dart';
import 'package:intl/intl.dart';
import 'dart:convert';

class DailySummary {
  final DateTime date;
  final int totalKeys;
  final double totalMouseDistance;
  final int totalLeftClicks;
  final int totalRightClicks;
  final double totalScrollSteps;
  final int totalEnterPresses;
  final int totalPrompts;
  final int totalVSCodePrompts;
  final int totalVSCodeInsidersPrompts;

  DailySummary({
    required this.date,
    required this.totalKeys,
    required this.totalMouseDistance,
    required this.totalLeftClicks,
    required this.totalRightClicks,
    required this.totalScrollSteps,
    required this.totalEnterPresses,
    required this.totalPrompts,
    required this.totalVSCodePrompts,
    required this.totalVSCodeInsidersPrompts,
  });

  Map<String, dynamic> toJson() => {
        'date': date.toIso8601String(),
        'totalKeys': totalKeys,
        'totalMouseDistance': totalMouseDistance,
        'totalLeftClicks': totalLeftClicks,
        'totalRightClicks': totalRightClicks,
        'totalScrollSteps': totalScrollSteps,
      'totalEnterPresses': totalEnterPresses,
        'totalPrompts': totalPrompts,
        'totalVSCodePrompts': totalVSCodePrompts,
        'totalVSCodeInsidersPrompts': totalVSCodeInsidersPrompts,
      };

  factory DailySummary.fromJson(Map<String, dynamic> json) => DailySummary(
        date: DateTime.parse(json['date']),
        totalKeys: json['totalKeys'] ?? 0,
        totalMouseDistance: (json['totalMouseDistance'] ?? 0).toDouble(),
        totalLeftClicks: json['totalLeftClicks'] ?? 0,
        totalRightClicks: json['totalRightClicks'] ?? 0,
        totalScrollSteps: (json['totalScrollSteps'] ?? 0).toDouble(),
      totalEnterPresses: json['totalEnterPresses'] ?? 0,
        totalPrompts: json['totalPrompts'] ?? 0,
        totalVSCodePrompts: json['totalVSCodePrompts'] ?? (json['totalPrompts'] ?? 0),
        totalVSCodeInsidersPrompts: json['totalVSCodeInsidersPrompts'] ?? 0,
      );
}

class StorageService {
  static const String _summariesKey = 'daily_summaries';

  Future<void> saveDailySummary(DailySummary summary) async {
    final prefs = await SharedPreferences.getInstance();
    final summaries = await getDailySummaries();
    
    // Remove existing summary for the same date if it exists
    summaries.removeWhere((s) => 
        DateFormat('yyyy-MM-dd').format(s.date) == 
        DateFormat('yyyy-MM-dd').format(summary.date));
    
    summaries.add(summary);
    
    // Keep only last 30 days
    if (summaries.length > 30) {
      summaries.sort((a, b) => b.date.compareTo(a.date));
      summaries.removeRange(30, summaries.length);
    }
    
    final jsonList = summaries.map((s) => s.toJson()).toList();
    await prefs.setString(_summariesKey, jsonEncode(jsonList));
  }

  Future<List<DailySummary>> getDailySummaries() async {
    final prefs = await SharedPreferences.getInstance();
    final jsonString = prefs.getString(_summariesKey);
    
    if (jsonString == null) return [];
    
    final jsonList = jsonDecode(jsonString) as List;
    return jsonList.map((json) => DailySummary.fromJson(json)).toList();
  }

  Future<DailySummary?> getTodaySummary() async {
    final summaries = await getDailySummaries();
    final today = DateFormat('yyyy-MM-dd').format(DateTime.now());
    
    try {
      return summaries.firstWhere((s) => 
          DateFormat('yyyy-MM-dd').format(s.date) == today);
    } catch (e) {
      return null;
    }
  }
}
