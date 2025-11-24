import 'package:flutter/material.dart';
// Removed fl_chart; using CustomPainter implementations for charts.
import 'package:intl/intl.dart';
import 'dart:async';
import 'dart:collection';
import 'activity_service.dart';
import 'storage_service.dart';
import 'vscode_prompt_tracker.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Activity Tracker',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: const ActivityTrackerHome(),
      debugShowCheckedModeBanner: false,
    );
  }
}

class ActivityTrackerHome extends StatefulWidget {
  const ActivityTrackerHome({super.key});

  @override
  State<ActivityTrackerHome> createState() => _ActivityTrackerHomeState();
}

class _ActivityTrackerHomeState extends State<ActivityTrackerHome> {
  final ActivityService _activityService = ActivityService();
  final StorageService _storageService = StorageService();
  final VSCodePromptTracker _promptTracker = VSCodePromptTracker();

  StreamSubscription? _activitySubscription;
  StreamSubscription? _rateSubscription;
  StreamSubscription? _promptSubscription;

  int _currentKeyCount = 0;
  double _currentMouseDistance = 0.0;
  int _currentLeftClicks = 0;
  int _currentRightClicks = 0;
  double _currentScrollAmount = 0.0;

  final Queue<ActivityData> _activityHistory = Queue();
  final Queue<ActivityRate> _rateHistory = Queue();
  final int _windowSeconds = 120; // sliding window
  // Removed _tick (unused after simplifying pruning logic)

  Timer? _saveTimer;
  bool _isInitialized = false;

  // Recent chat refresh & discovery tracking
  static const int _recentChatRefreshIntervalSeconds = 5;
  int _recentChatCountdown = _recentChatRefreshIntervalSeconds;
  int _newChatsFoundLastRefresh = 0;
  Timer? _recentChatRefreshTimer;
  final Map<String, DateTime> _chatDiscoveryTimes = {}; // key -> discoveredAt

  @override
  void initState() {
    super.initState();
    _initializeTracker();
  }

  Future<void> _initializeTracker() async {
    final success = await _activityService.initialize();
    
    if (success) {
      // Load persisted daily stats before starting stream listeners
      final todaySummary = await _storageService.getTodaySummary();
      if (todaySummary != null) {
        _activityService.setInitialTotals(
          keys: todaySummary.totalKeys,
          mouseDistance: todaySummary.totalMouseDistance,
          leftClicks: todaySummary.totalLeftClicks,
          rightClicks: todaySummary.totalRightClicks,
          scrollSteps: todaySummary.totalScrollSteps,
          enterCount: todaySummary.totalEnterPresses,
        );
        _promptTracker.setInitialPromptTotals(
          vscode: todaySummary.totalVSCodePrompts,
          insiders: todaySummary.totalVSCodeInsidersPrompts,
          total: todaySummary.totalPrompts,
        );
      }
      setState(() {
        _isInitialized = true;
      });

      _activitySubscription = _activityService.activityStream.listen((data) {
        setState(() {
          _currentKeyCount = data.keyCount;
            _currentMouseDistance = data.mouseDistance;
            _currentLeftClicks = data.leftClicks;
            _currentRightClicks = data.rightClicks;
            _currentScrollAmount = data.scrollAmount;

          _activityHistory.add(data);
          // Prune history to last _windowSeconds entries (1 per second)
          while (_activityHistory.length > _windowSeconds) {
            _activityHistory.removeFirst();
          }
        });
      });

      _rateSubscription = _activityService.rateStream.listen((rate) {
        setState(() {
          _rateHistory.add(rate);
          while (_rateHistory.length > _windowSeconds) {
            _rateHistory.removeFirst();
          }
        });
      });

      // Initialize VS Code prompt tracking
      await _promptTracker.initialize();
      _promptSubscription = _promptTracker.promptStream.listen((event) {
        setState(() {
          // Update UI when new prompts are detected
        });
      });

      // Start countdown refresh timer for recent chat edits list
      _recentChatRefreshTimer = Timer.periodic(const Duration(seconds: 1), (_) {
        _recentChatCountdown--;
        if (_recentChatCountdown <= 0) {
          _handleRecentChatRefresh();
          _recentChatCountdown = _recentChatRefreshIntervalSeconds;
        } else {
          if (mounted) setState(() {}); // tick visual countdown
        }
      });

      // Save daily summary every 5 minutes
      _saveTimer = Timer.periodic(const Duration(minutes: 5), (_) {
        _saveDailySummary();
      });
    } else {
      // Show error dialog
      if (mounted) {
        showDialog(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Initialization Failed'),
            content: const Text(
              'Failed to initialize activity tracking. '
              'Make sure X11 libraries are installed and you have proper permissions.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('OK'),
              ),
            ],
          ),
        );
      }
    }
  }

  Future<void> _saveDailySummary() async {
    final summary = DailySummary(
      date: DateTime.now(),
      totalKeys: _activityService.totalKeysToday,
      totalMouseDistance: _activityService.totalMouseDistanceToday,
      totalLeftClicks: _activityService.totalLeftClicksToday,
      totalRightClicks: _activityService.totalRightClicksToday,
      totalScrollSteps: _activityService.totalScrollToday,
      totalEnterPresses: _activityService.totalEnterToday,
      totalPrompts: _promptTracker.totalPromptsToday,
      totalVSCodePrompts: _promptTracker.vscodePromptCount,
      totalVSCodeInsidersPrompts: _promptTracker.vscodeInsidersPromptCount,
    );
    await _storageService.saveDailySummary(summary);
  }

  @override
  void dispose() {
    _activitySubscription?.cancel();
    _rateSubscription?.cancel();
    _promptSubscription?.cancel();
    _saveTimer?.cancel();
    _recentChatRefreshTimer?.cancel();
    _saveDailySummary(); // Save on exit
    _activityService.dispose();
    _promptTracker.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Activity Tracker'),
        centerTitle: true,
        elevation: 0.5,
      ),
      body: _isInitialized
          ? Padding(
              padding: const EdgeInsets.all(10.0),
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Start with prompts and last prompt info
                    _buildPromptTinyRow(),
                    const SizedBox(height: 8),
                    _buildRecentChatsList(),
                    const SizedBox(height: 12),
                    _buildTinyStatsRow(),
                    const SizedBox(height: 10),
                    _buildCompactChartsRow(),
                    const SizedBox(height: 10),
                    _buildDailySummaryCompact(),
                  ],
                ),
              ),
            )
          : const Center(child: CircularProgressIndicator()),
    );
  }
  Widget _buildTinyStatsRow() {
    return Wrap(
      spacing: 8,
      runSpacing: 6,
      children: [
        _statChip(icon: Icons.keyboard_alt, label: 'Keystrokes', value: _currentKeyCount.toString(), color: Colors.blue),
        _statChip(icon: Icons.mouse, label: 'Mouse Distance (px)', value: _currentMouseDistance.toStringAsFixed(0), color: Colors.green),
        _statChip(icon: Icons.touch_app, label: 'Left Mouse Clicks', value: _currentLeftClicks.toString(), color: Colors.orange),
        _statChip(icon: Icons.mouse, label: 'Right Mouse Clicks', value: _currentRightClicks.toString(), color: Colors.deepOrange),
        _statChip(icon: Icons.swipe, label: 'Scroll Wheel Steps', value: _currentScrollAmount.toStringAsFixed(0), color: Colors.purple),
        _statChip(icon: Icons.keyboard_return, label: 'Enter Key Presses (Today)', value: _activityService.totalEnterToday.toString(), color: Colors.indigo),
      ],
    );
  }

  Widget _buildPromptTinyRow() {
    return Wrap(
      spacing: 8,
      runSpacing: 4,
      children: [
        _tinyChip('VS Code Prompts', _promptTracker.vscodePromptCount.toString(), Colors.blue),
        _tinyChip('VS Code Insiders Prompts', _promptTracker.vscodeInsidersPromptCount.toString(), Colors.purple),
        _tinyChip('Total Prompts Today', _promptTracker.totalPromptsToday.toString(), Colors.orange),
        _tinyChip('History Chat Edits', _promptTracker.historyChatEditCount.toString(), Colors.indigo),
        _tinyChip('History Insiders Chat Edits', _promptTracker.historyInsidersChatEditCount.toString(), Colors.deepPurple),
        if (_promptTracker.lastVSCodeLogPath != null)
          _tinyChip('VS Code Matched Lines', _promptTracker.lastVSCodeMatchedLines.toString(), Colors.teal),
      ],
    );
  }

  Widget _buildCompactChartsRow() {
    final slotWidth = MediaQuery.of(context).size.width / 3 - 16;
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        SizedBox(width: slotWidth, child: _buildKeysStack()),
        SizedBox(width: slotWidth, child: _buildMouseStack()),
        SizedBox(width: slotWidth, child: _buildClicksScrollGroup(slotWidth)),
      ],
    );
  }

  Widget _buildClicksScrollGroup(double fullWidth) {
    final halfWidth = (fullWidth - 8) / 2; // small gap allowance
    return Column(
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(width: halfWidth, child: _buildLeftClicksBarChart()),
            const SizedBox(width: 8),
            SizedBox(width: halfWidth, child: _buildRightClicksBarChart()),
          ],
        ),
        const SizedBox(height: 6),
        // Scroll chart now double wide (full width) and vertically centered bars
        SizedBox(
          width: fullWidth,
          child: Container(
            margin: const EdgeInsets.symmetric(vertical: 4),
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surface,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: Colors.grey.withValues(alpha: 0.2)),
              boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.03), blurRadius: 4, offset: const Offset(0,1))],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Scroll Wheel Steps per Second', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                const SizedBox(height: 4),
                SizedBox(
                  height: 60,
                  child: ActivityCenteredBarChart(
                    values: _rateHistory.map((r) => r.scrollUnitsPerSecond).toList(),
                    barColor: Colors.purple,
                    maxBars: _windowSeconds,
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildKeysStack() {
    final bar = _buildKeysBarChart();
    final cumulativeValues = _activityHistory.isEmpty
        ? <double>[]
        : _activityHistory.map((e) => e.keyCount.toDouble()).toList();
    final cumChart = _buildMiniCumulative('Total Keystrokes (Window)', cumulativeValues, Colors.blue);
    return Column(children: [bar, cumChart]);
  }

  Widget _buildMouseStack() {
    final bar = _buildMouseBarChart();
    final cumulativeValues = _activityHistory.isEmpty
        ? <double>[]
        : _activityHistory.map((e) => e.mouseDistance).toList();
    final cumChart = _buildMiniCumulative('Total Mouse Distance (Window, px)', cumulativeValues, Colors.green);
    return Column(children: [bar, cumChart]);
  }

  Widget _buildMiniCumulative(String title, List<double> fullValues, Color color) {
    // Ensure at least two points so the line chart renders immediately.
    if (fullValues.isEmpty) {
      fullValues = [0, 0];
    } else if (fullValues.length == 1) {
      fullValues = [fullValues.first, fullValues.first];
    }
    final startIndex = fullValues.length > _windowSeconds ? fullValues.length - _windowSeconds : 0;
    final values = fullValues.sublist(startIndex);
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 4),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.grey.withValues(alpha: 0.2)),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.03), blurRadius: 4, offset: const Offset(0,1))],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          SizedBox(height: 60, width: double.infinity, child: CumulativeLineChart(values: values, color: color)),
        ],
      ),
    );
  }

  // (Removed single last prompt card in favor of recent list)
  // Removed _buildLastPromptCard (unused single prompt view)

  Widget _buildRecentChatsList() {
    final entries = _promptTracker.recentHistoryEntries;
    if (entries.isEmpty) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.grey.withValues(alpha: 0.25)),
        ),
        child: const Text('No recent chat edits detected in last 24h.', style: TextStyle(fontSize: 12)),
      );
    }
    // Deduplicate by normalized body text (case-insensitive, trimmed).
    final seenBodies = <String>{};
    final deduped = <VSCodeHistoryEntry>[];
    for (final e in entries) {
      final idx = e.source.indexOf(':');
      final bodyRaw = idx != -1 ? e.source.substring(idx + 1).trim() : e.source.trim();
      final normalized = bodyRaw.toLowerCase();
      if (seenBodies.add(normalized)) {
        deduped.add(e);
      }
      if (deduped.length >= 10) break; // only show first 10 unique
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.withValues(alpha: 0.25)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.list, size: 18, color: Colors.blueGrey),
              const SizedBox(width: 6),
              const Text('Recent Chat Edits (24h)', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
              const SizedBox(width: 8),
              // Countdown until next refresh
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.blueGrey.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: Colors.blueGrey.withValues(alpha: 0.25)),
                ),
                child: Text('refresh in ${_recentChatCountdown}s', style: const TextStyle(fontSize: 10, color: Colors.blueGrey)),
              ),
              const SizedBox(width: 6),
              if (_newChatsFoundLastRefresh > 0)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: Colors.green.withValues(alpha: 0.10),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: Colors.green.withValues(alpha: 0.35)),
                  ),
                  child: Text('+$_newChatsFoundLastRefresh', style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: Colors.green)),
                ),
            ],
          ),
          const SizedBox(height: 6),
          for (final e in deduped) ...[
            _recentChatRow(e),
            const SizedBox(height: 4),
          ],
        ],
      ),
    );
  }

  Widget _recentChatRow(VSCodeHistoryEntry e) {
    final diff = DateTime.now().difference(e.timestamp);
    String ago;
    if (diff.inSeconds < 60) {
      ago = '${diff.inSeconds}s';
    } else if (diff.inMinutes < 60) {
      ago = '${diff.inMinutes}m';
    } else if (diff.inHours < 48) {
      ago = '${diff.inHours}h (${diff.inMinutes}m)';
    } else {
      ago = DateFormat('yyyy-MM-dd').format(e.timestamp);
    }
    final idx = e.source.indexOf(':');
    String body = idx != -1 ? e.source.substring(idx + 1).trim() : e.source.trim();
    if (body.length > 140) body = '${body.substring(0, 137)}…';
    // Highlight fade for newly discovered entries (1 minute linear fade)
    final key = '${e.timestamp.microsecondsSinceEpoch}|${e.source}';
    final discoveredAt = _chatDiscoveryTimes[key];
    double highlightOpacity = 0.0;
    if (discoveredAt != null) {
      final ageSec = DateTime.now().difference(discoveredAt).inSeconds;
      if (ageSec < 60) {
        highlightOpacity = (1 - ageSec / 60) * 0.6; // max 0.6 -> 0 over 60s
      }
    }
    final rowChild = Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Icon(Icons.chat, size: 14, color: Colors.blueGrey),
        const SizedBox(width: 6),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(body, style: const TextStyle(fontSize: 12)),
              if (e.resource != null)
                Text(e.resource!, style: const TextStyle(fontSize: 10, color: Colors.grey)),
            ],
          ),
        ),
        const SizedBox(width: 6),
        Text(ago, style: const TextStyle(fontSize: 10, color: Colors.grey)),
      ],
    );
    if (highlightOpacity > 0) {
      return AnimatedOpacity(
        duration: const Duration(milliseconds: 400),
        opacity: 1.0,
        child: Container(
          decoration: BoxDecoration(
            color: Colors.yellow.withValues(alpha: highlightOpacity),
            borderRadius: BorderRadius.circular(6),
          ),
          padding: const EdgeInsets.symmetric(vertical: 4, horizontal: 4),
          child: rowChild,
        ),
      );
    }
    return rowChild;
  }

  void _handleRecentChatRefresh() {
    final entries = _promptTracker.recentHistoryEntries;
    int newCount = 0;
    for (final e in entries) {
      final key = '${e.timestamp.microsecondsSinceEpoch}|${e.source}';
      if (!_chatDiscoveryTimes.containsKey(key)) {
        _chatDiscoveryTimes[key] = DateTime.now();
        newCount++;
      }
    }
    // Cap discovery map size to avoid unbounded growth (FIFO removal)
    if (_chatDiscoveryTimes.length > 500) {
      final sortedKeys = _chatDiscoveryTimes.entries.toList()
        ..sort((a,b) => a.value.compareTo(b.value));
      final excess = _chatDiscoveryTimes.length - 500;
      for (int i=0; i<excess; i++) {
        _chatDiscoveryTimes.remove(sortedKeys[i].key);
      }
    }
    _newChatsFoundLastRefresh = newCount;
    if (mounted) setState(() {});
  }

  // Removed _buildStatItem (legacy large stat card)

  // Split cumulative charts
  // Removed old cumulative chart methods (superseded by compact stack charts)

  // Removed legacy _cumulativeCard helper (unused)

  // New custom full-width bar chart wrapper.
  Widget _buildBarChart({required String title, required List<double> values, required Color color}) {
    final length = values.length;
    final startIndex = _rateHistory.length > _windowSeconds ? _rateHistory.length - _windowSeconds : 0;
    final subset = length >= 1 ? values.sublist(startIndex) : <double>[];
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 4),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.grey.withValues(alpha: 0.2)),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.03), blurRadius: 4, offset: const Offset(0,1))],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          SizedBox(height: 60, width: double.infinity, child: ActivityBarChart(values: subset, barColor: color, maxBars: _windowSeconds)),
        ],
      ),
    );
  }

  Widget _buildKeysBarChart() {
    final values = _rateHistory.map((r) => r.keysPerSecond.toDouble()).toList();
    return _buildBarChart(title: 'Keystrokes per Second', values: values, color: Colors.blue);
  }

  Widget _buildMouseBarChart() {
    final values = _rateHistory.map((r) => r.mouseDistancePerSecond).toList();
    return _buildBarChart(title: 'Mouse Distance per Second (px)', values: values, color: Colors.green);
  }

  Widget _buildLeftClicksBarChart() {
    final values = _rateHistory.map((r) => r.leftClicksPerSecond.toDouble()).toList();
    return _buildBarChart(title: 'Left Mouse Clicks per Second', values: values, color: Colors.orange);
  }

  Widget _buildRightClicksBarChart() {
    final values = _rateHistory.map((r) => r.rightClicksPerSecond.toDouble()).toList();
    return _buildBarChart(title: 'Right Mouse Clicks per Second', values: values, color: Colors.deepOrange);
  }

  // Removed _buildScrollBarChart (unused after dedicated group widget)

  // Removed old combined cumulative chart function.

  // Removed multi-line rate chart in favor of separate per-second bar charts.

  // Removed separate mouse rate chart in favor of multi-line compact chart.

  Widget _buildDailySummaryCompact() {
    return Wrap(
      spacing: 6,
      runSpacing: 4,
      children: [
        _tinyChip('Total Keystrokes Today', _activityService.totalKeysToday.toString(), Colors.blue),
        _tinyChip('Total Mouse Distance Today (px)', _activityService.totalMouseDistanceToday.toStringAsFixed(0), Colors.green),
        _tinyChip('Total Left Clicks Today', _activityService.totalLeftClicksToday.toString(), Colors.orange),
        _tinyChip('Total Right Clicks Today', _activityService.totalRightClicksToday.toString(), Colors.deepOrange),
        _tinyChip('Total Scroll Wheel Steps Today', _activityService.totalScrollToday.toStringAsFixed(0), Colors.purple),
        _tinyChip('Total Enter Presses Today', _activityService.totalEnterToday.toString(), Colors.indigo),
        _tinyChip('Total Prompts Today', _promptTracker.totalPromptsToday.toString(), Colors.teal),
        GestureDetector(
          onTap: () {
            setState(() {
              _activityService.resetDailyStats();
              _promptTracker.resetDailyStats();
            });
          },
          child: _tinyChip('Reset Today', '↺', Colors.redAccent),
        ),
      ],
    );
  }

  Widget _tinyChip(String label, String value, Color color) {
    return _statChip(icon: Icons.data_usage, label: label, value: value, color: color);
  }

  Widget _statChip({required IconData icon, required String label, required String value, required Color color}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.09),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withValues(alpha: 0.35), width: 0.9),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 18, color: color),
          const SizedBox(width: 6),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(label, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: color)),
              Text(value, style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: color)),
            ],
          ),
        ],
      ),
    );
  }
}

// -------------------------- Custom Charts ------------------------------

class ActivityBarChart extends StatelessWidget {
  final List<double> values;
  final Color barColor;
  final int maxBars;
  const ActivityBarChart({super.key, required this.values, required this.barColor, required this.maxBars});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, constraints) {
      return CustomPaint(
        painter: _BarChartPainter(values: values, color: barColor, maxBars: maxBars),
        size: Size(constraints.maxWidth, constraints.maxHeight),
      );
    });
  }
}

// Centered vertical variant: bars grow equally above/below a midline to avoid bleed and stay visually centered.
class ActivityCenteredBarChart extends StatelessWidget {
  final List<double> values;
  final Color barColor;
  final int maxBars;
  const ActivityCenteredBarChart({super.key, required this.values, required this.barColor, required this.maxBars});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, constraints) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: CustomPaint(
          painter: _CenteredBarChartPainter(values: values, color: barColor, maxBars: maxBars),
          size: Size(constraints.maxWidth, constraints.maxHeight),
        ),
      );
    });
  }
}

class _CenteredBarChartPainter extends CustomPainter {
  final List<double> values;
  final Color color;
  final int maxBars;
  _CenteredBarChartPainter({required this.values, required this.color, required this.maxBars});

  @override
  void paint(Canvas canvas, Size size) {
    final bgAxisPaint = Paint()..color = Colors.grey.withValues(alpha: 0.25)..strokeWidth = 1;
    final midY = size.height / 2;
    // Draw midline
    canvas.drawLine(Offset(0, midY), Offset(size.width, midY), bgAxisPaint);
    if (values.isEmpty) return;
    final maxValue = values.fold<double>(0, (p, c) => c > p ? c : p);
    final barCount = values.length.clamp(0, maxBars);
    final slotWidth = size.width / maxBars;
    final barWidth = slotWidth * 0.7;
    // Scale so largest value fills half height (above mid)
    final yScale = (size.height / 2 - 4) / (maxValue == 0 ? 1 : maxValue);
    final startX = size.width - slotWidth * barCount; // right align
    final paint = Paint()..color = color..style = PaintingStyle.fill;
    for (int i = 0; i < barCount; i++) {
      final raw = values[i];
      final mag = raw.abs();
      final h = mag * yScale; // positive height portion above/below mid
      final double clampedH = h.clamp(0, size.height / 2 - 4).toDouble();
      if (clampedH <= 0) continue;
      final x = startX + i * slotWidth + (slotWidth - barWidth) / 2;
      double top;
      double height;
      if (raw >= 0) {
        top = midY - clampedH;
        height = clampedH; // positive values draw above mid
      } else {
        top = midY;
        height = clampedH; // negative values draw below mid
      }
      // Ensure within bounds
      if (top < 0) {
        height -= -top;
        top = 0;
      }
      if (top + height > size.height) {
        height = size.height - top;
      }
      if (height <= 0) continue;
      final rect = RRect.fromRectAndRadius(
        Rect.fromLTWH(x, top, barWidth, height),
        const Radius.circular(3),
      );
      canvas.drawRRect(rect, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _CenteredBarChartPainter oldDelegate) => oldDelegate.values != values || oldDelegate.color != color;
}

class _BarChartPainter extends CustomPainter {
  final List<double> values;
  final Color color;
  final int maxBars;
  _BarChartPainter({required this.values, required this.color, required this.maxBars});

  @override
  void paint(Canvas canvas, Size size) {
    final axisPaint = Paint()..color = Colors.grey.withValues(alpha: 0.3)..strokeWidth = 1;
    canvas.drawLine(Offset(0, size.height - 1), Offset(size.width, size.height - 1), axisPaint);
    if (values.isEmpty) return;
    final maxValue = values.fold<double>(0, (p, c) => c > p ? c : p);
    final barCount = values.length.clamp(0, maxBars);
    final slotWidth = size.width / maxBars;
    final barWidth = slotWidth * 0.7;
    final yScale = (size.height - 4) / (maxValue == 0 ? 1 : maxValue);
    final startX = size.width - slotWidth * barCount; // right align
    final paint = Paint()..color = color..style = PaintingStyle.fill;
    for (int i = 0; i < barCount; i++) {
      final v = values[i];
      final h = v * yScale;
      final x = startX + i * slotWidth + (slotWidth - barWidth) / 2;
      final rect = RRect.fromRectAndRadius(Rect.fromLTWH(x, size.height - h, barWidth, h), const Radius.circular(3));
      canvas.drawRRect(rect, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _BarChartPainter oldDelegate) => oldDelegate.values != values || oldDelegate.color != color;
}

class CumulativeLineChart extends StatelessWidget {
  final List<double> values;
  final Color color;
  const CumulativeLineChart({super.key, required this.values, required this.color});
  @override
  Widget build(BuildContext context) => LayoutBuilder(builder: (context, constraints) => CustomPaint(
        painter: _CumulativeLinePainter(values: values, color: color),
        size: Size(constraints.maxWidth, constraints.maxHeight),
      ));
}

class _CumulativeLinePainter extends CustomPainter {
  final List<double> values;
  final Color color;
  _CumulativeLinePainter({required this.values, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final axisPaint = Paint()..color = Colors.grey.withValues(alpha: 0.3)..strokeWidth = 1;
    canvas.drawLine(Offset(0, size.height - 1), Offset(size.width, size.height - 1), axisPaint);
    if (values.length < 2) return;
    final maxValue = values.fold<double>(0, (p, c) => c > p ? c : p);
    final path = Path();
    for (int i = 0; i < values.length; i++) {
      final x = (i / (values.length - 1)) * size.width;
      final yRatio = maxValue == 0 ? 0 : values[i] / maxValue;
      final y = size.height - yRatio * (size.height - 4);
      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }
    final stroke = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2
      ..isAntiAlias = true;
    canvas.drawPath(path, stroke);
  }

  @override
  bool shouldRepaint(covariant _CumulativeLinePainter oldDelegate) => oldDelegate.values != values || oldDelegate.color != color;
}
