import 'dart:async';
import 'dart:convert';
import 'dart:io';

class VSCodePromptTracker {
  Timer? _watchTimer;
  final _promptStreamController = StreamController<VSCodePromptEvent>.broadcast();
  Stream<VSCodePromptEvent> get promptStream => _promptStreamController.stream;

  int _vscodePromptCount = 0;
  int _vscodeInsidersPromptCount = 0;
  int _totalPromptsToday = 0;

  final Map<String, int> _lastLineCount = {};
  final Map<String, DateTime> _lastModified = {};
  final Map<String, String> _lastLogFilePath = {};
  final Map<String, int> _lastMatchedLines = {};
  final Map<String, int> _lastFileSize = {}; // track bytes processed for incremental reading
  String? _lastPromptLine; // store last matched prompt line
  DateTime? _lastPromptTimestamp;
  String? _lastPromptText; // extracted user-entered prompt content
  String? _pendingRole; // role context for upcoming text lines
  bool _sawUserMessageMarker = false; // track textual markers like "User message"

  // Latest VS Code history chat edit entry
  String? _lastHistorySource;
  String? _lastHistoryFile;
  DateTime? _lastHistoryTimestamp;
  int _historyChatEditCount = 0;
  int _historyInsidersChatEditCount = 0;
  final List<VSCodeHistoryEntry> _recentHistoryEntries = []; // newest first
  static const int _maxRecentHistory = 15;

  // Substring / regex patterns to detect user prompt lines
  final List<RegExp> _promptPatterns = [
    RegExp(r'sendChatRequest', caseSensitive: false),
    RegExp(r'chat request', caseSensitive: false),
    RegExp(r'User message', caseSensitive: false),
    RegExp(r'requestId', caseSensitive: false),
    RegExp(r'createChat', caseSensitive: false),
    RegExp(r'"role"\s*:\s*"user"', caseSensitive: false),
    RegExp(r'ChatResponse', caseSensitive: false),
    RegExp(r'copilot-chat', caseSensitive: false),
    // Added broader patterns for Copilot Chat log variability
    RegExp(r'"sender"\s*:\s*"user"', caseSensitive: false),
    RegExp(r'"prompt"\s*:', caseSensitive: false),
    RegExp(r'userMessage', caseSensitive: false),
    RegExp(r'ChatRequest', caseSensitive: false),
    RegExp(r'Requesting chat', caseSensitive: false),
    RegExp(r'Chat session', caseSensitive: false),
    RegExp(r'"text"\s*:\s*".*"', caseSensitive: false),
  ];

  int get vscodePromptCount => _vscodePromptCount;
  int get vscodeInsidersPromptCount => _vscodeInsidersPromptCount;
  int get totalPromptsToday => _totalPromptsToday;
  String? get lastVSCodeLogPath => _lastLogFilePath['vscode'];
  String? get lastInsidersLogPath => _lastLogFilePath['vscode-insiders'];
  int get lastVSCodeMatchedLines => _lastMatchedLines['vscode'] ?? 0;
  int get lastInsidersMatchedLines => _lastMatchedLines['vscode-insiders'] ?? 0;
  String? get lastPromptLine => _lastPromptLine;
  DateTime? get lastPromptTime => _lastPromptTimestamp;
  String? get lastPromptText => _lastPromptText;
  String? get lastHistorySource => _lastHistorySource;
  String? get lastHistoryFile => _lastHistoryFile;
  DateTime? get lastHistoryTimestamp => _lastHistoryTimestamp;
  int get historyChatEditCount => _historyChatEditCount;
  int get historyInsidersChatEditCount => _historyInsidersChatEditCount;
  List<VSCodeHistoryEntry> get recentHistoryEntries => List.unmodifiable(_recentHistoryEntries);

  Future<void> initialize() async {
    // Do an initial history scan
    await _checkVSCodeHistory();

    _watchTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      _checkVSCodeLogs();
      _checkVSCodeHistory();
    });
  }

  Future<void> _checkVSCodeLogs() async {
    final home = Platform.environment['HOME'] ?? '';
    if (home.isEmpty) return;

    // Check both VS Code and VS Code Insiders logs
    await _checkLogDirectory('$home/.config/Code/logs', 'vscode');
    await _checkLogDirectory('$home/.config/Code - Insiders/logs', 'vscode-insiders');
  }

  Future<void> _checkVSCodeHistory() async {
    try {
      final home = Platform.environment['HOME'] ?? '';
      if (home.isEmpty) return;

      final historyRoots = <Directory>[
        Directory('$home/.config/Code/User/History'),
        Directory('$home/.config/Code - Insiders/User/History'),
      ];

      final now = DateTime.now();
      final recentCutoff = now.subtract(const Duration(days: 1));

      VSCodeHistoryEntry? newestAny;
      VSCodeHistoryEntry? newestRecent;
      int chatEditCount = 0;
      int insidersCount = 0;
      final List<VSCodeHistoryEntry> collectedRecent = [];

      for (final historyRoot in historyRoots) {
        if (!await historyRoot.exists()) continue;
        await for (final entity in historyRoot.list(recursive: true, followLinks: false)) {
          if (entity is! File) continue;
          if (!entity.path.endsWith('entries.json')) continue;
          try {
            final text = await entity.readAsString();
            final decoded = jsonDecode(text);
            if (decoded is! Map<String, dynamic>) continue;
            final resource = decoded['resource'] as String?;
            final entries = decoded['entries'];
            if (entries is! List) continue;
            for (final e in entries) {
              if (e is! Map<String, dynamic>) continue;
              final source = e['source'] as String?;
              final ts = e['timestamp'];
              if (source == null || ts == null) continue;
              final lower = source.toLowerCase();
              final isChatLike = lower.contains('chat edit') ||
                  lower.contains('copilot chat') ||
                  lower.contains('chat insert') ||
                  lower.contains('chat replace') ||
                  lower.contains('chat diff') ||
                  (lower.contains('chat') && source.contains(':'));
              if (!isChatLike) continue;
              chatEditCount++;
              if (resource != null && resource.contains('Code - Insiders')) {
                insidersCount++;
              }
              final tsMs = ts is int ? ts : int.tryParse('$ts');
              if (tsMs == null) continue;
              final dt = DateTime.fromMillisecondsSinceEpoch(tsMs);
              final entry = VSCodeHistoryEntry(resource: resource, source: source, timestamp: dt);
              if (newestAny == null || dt.isAfter(newestAny.timestamp)) {
                newestAny = entry;
              }
              if (dt.isAfter(recentCutoff)) {
                if (newestRecent == null || dt.isAfter(newestRecent.timestamp)) {
                  newestRecent = entry;
                }
                collectedRecent.add(entry);
              }
            }
          } catch (_) {
            // ignore malformed file
          }
        }
      }

      collectedRecent.sort((a, b) => b.timestamp.compareTo(a.timestamp));
      _recentHistoryEntries
        ..clear()
        ..addAll(collectedRecent.take(_maxRecentHistory));

      final chosen = newestRecent ?? newestAny;
      if (chosen != null) {
        _lastHistorySource = chosen.source;
        _lastHistoryFile = chosen.resource;
        _lastHistoryTimestamp = chosen.timestamp;
      }

      _historyChatEditCount = chatEditCount;
      _historyInsidersChatEditCount = insidersCount;
    } catch (_) {
      // ignore scan errors
    }
  }

  Future<void> _checkLogDirectory(String basePath, String source) async {
    try {
      final logsDir = Directory(basePath);
      if (!await logsDir.exists()) {
        // ignore: avoid_print
        print('[PromptTracker] Logs directory not found for $source at $basePath');
        return;
      }

      // Find the most recent log directory
      final logDirs = await logsDir
          .list()
          .where((entity) => entity is Directory)
          .map((entity) => entity as Directory)
          .toList();

      if (logDirs.isEmpty) {
        // ignore: avoid_print
        print('[PromptTracker] No log subdirectories found for $source in $basePath');
        return;
      }

      // Sort by name (timestamp) and get the latest
      logDirs.sort((a, b) => b.path.compareTo(a.path));
      final latestLogDir = logDirs.first;

      // Find Copilot Chat log file
      File? found;
      await for (final entity in latestLogDir.list(recursive: true)) {
        if (entity is File && entity.path.contains('GitHub Copilot Chat.log')) {
          found = entity;
          break;
        }
      }
      if (found == null) {
        // ignore: avoid_print
        print('[PromptTracker] No GitHub Copilot Chat.log found for $source in ${latestLogDir.path}');
        return;
      }
      // ignore: avoid_print
      print('[PromptTracker] Using log file for $source: ${found.path}');
      await _checkLogFile(found.path, source);
    } catch (e) {
      // ignore: avoid_print
      print('[PromptTracker] Error while checking logs for $source: $e');
    }
  }

  Future<void> _checkLogFile(String filePath, String source) async {
    try {
      final file = File(filePath);
      if (!await file.exists()) return;

      final stat = await file.stat();
      final currentSize = stat.size;
      final lastSize = _lastFileSize[filePath] ?? 0;
      int newPrompts = 0;

      // If file truncated or first time, full scan establishes baseline without increment (unless first time)
      if (currentSize < lastSize) {
        _lastFileSize[filePath] = 0;
      }

      if (lastSize == 0) {
        // Initial full scan: count all existing prompts as baseline but don't treat as new
        final content = await file.readAsString(); // baseline full scan
        final lines = content.split('\n');
        int promptCount = 0;
        for (final rawLine in lines) {
          final line = rawLine.trim();
          if (line.isEmpty) continue;
          for (final pattern in _promptPatterns) {
            if (pattern.hasMatch(line)) {
              promptCount++;
              _lastPromptLine = line;
              _lastPromptTimestamp = stat.modified;
              // Try to extract text if present
              final textMatch = RegExp(r'"text"\s*:\s*"(.*?)"').firstMatch(line);
              if (textMatch != null) {
                _lastPromptText = _sanitizePrompt(textMatch.group(1));
              }
              break;
            }
          }
        }
        _lastLineCount[filePath] = promptCount;
        _lastMatchedLines[source] = promptCount;
        _lastFileSize[filePath] = currentSize;
        if (promptCount > 0) {
          // Debug baseline count
          // ignore: avoid_print
          print('[PromptTracker] Baseline for $source: $promptCount matched lines, last line: ${_lastPromptLine ?? ''}');
        } else {
          // ignore: avoid_print
          print('[PromptTracker] Baseline for $source: no prompt-like lines detected');
        }
      } else if (currentSize > lastSize) {
        // Incremental scan: read only new bytes
        final raf = await file.open();
        await raf.setPosition(lastSize);
        final newBytes = await raf.read(currentSize - lastSize);
        await raf.close();
        final newContent = String.fromCharCodes(newBytes);
        final lines = newContent.split('\n');
        for (final rawLine in lines) {
          final line = rawLine.trim();
          if (line.isEmpty) continue;
          // Role tracking
          final roleMatch = RegExp(r'"role"\s*:\s*"(user|assistant)"', caseSensitive: false).firstMatch(line);
          if (roleMatch != null) {
            _pendingRole = roleMatch.group(1);
          }
          // If log has clear "User message" marker, treat following text as prompt
          if (line.toLowerCase().contains('user message')) {
            _sawUserMessageMarker = true;
            continue;
          }
          // Text extraction only if user role active
          if (_pendingRole == 'user' || _sawUserMessageMarker) {
            final textMatch = RegExp(r'"text"\s*:\s*"(.*?)"').firstMatch(line) ??
                RegExp(r'"prompt"\s*:\s*"(.*?)"').firstMatch(line);
            if (textMatch != null) {
              _lastPromptText = _sanitizePrompt(textMatch.group(1));
              _lastPromptLine = line;
              _lastPromptTimestamp = DateTime.now();
              newPrompts++;
              _pendingRole = null; // reset after capture
              _sawUserMessageMarker = false;
              continue; // avoid counting again by generic patterns
            }
          }
          for (final pattern in _promptPatterns) {
            if (pattern.hasMatch(line)) {
              newPrompts++;
              _lastPromptLine = line;
              _lastPromptTimestamp = DateTime.now();
              // Try to extract some readable text even if we didn't match role/text earlier
              final textMatch = RegExp(r'"text"\s*:\s*"(.*?)"').firstMatch(line) ??
                  RegExp(r'"prompt"\s*:\s*"(.*?)"').firstMatch(line);
              if (textMatch != null) {
                _lastPromptText = _sanitizePrompt(textMatch.group(1));
              }
              break;
            }
          }
        }
        if (newPrompts > 0) {
          _lastLineCount[filePath] = (_lastLineCount[filePath] ?? 0) + newPrompts;
          _lastMatchedLines[source] = _lastLineCount[filePath]!;
          // ignore: avoid_print
          print('[PromptTracker] Incremental $source +$newPrompts (total ${_lastLineCount[filePath]})');
        }
        _lastFileSize[filePath] = currentSize;
      }

      if (newPrompts > 0) {

        if (source == 'vscode') {
          _vscodePromptCount += newPrompts;
        } else {
          _vscodeInsidersPromptCount += newPrompts;
        }

        _totalPromptsToday += newPrompts;

        _promptStreamController.add(VSCodePromptEvent(
          source: source,
          promptCount: newPrompts,
          timestamp: DateTime.now(),
          lastLine: _lastPromptLine,
          promptText: _lastPromptText,
        ));
      }
      _lastModified[filePath] = stat.modified;
      _lastLogFilePath[source] = filePath;
    } catch (e) {
      // Silently ignore errors
    }
  }

  void resetDailyStats() {
    _vscodePromptCount = 0;
    _vscodeInsidersPromptCount = 0;
    _totalPromptsToday = 0;
  }

  void setInitialPromptTotals({
    int vscode = 0,
    int insiders = 0,
    int total = 0,
  }) {
    _vscodePromptCount = vscode;
    _vscodeInsidersPromptCount = insiders;
    _totalPromptsToday = total;
  }

  void dispose() {
    _watchTimer?.cancel();
    _promptStreamController.close();
  }
}

class VSCodeHistoryEntry {
  final String? resource;
  final String source;
  final DateTime timestamp;

  VSCodeHistoryEntry({
    required this.resource,
    required this.source,
    required this.timestamp,
  });
}

class VSCodePromptEvent {
  final String source; // 'vscode' or 'vscode-insiders'
  final int promptCount;
  final DateTime timestamp;
  final String? lastLine;
  final String? promptText;

  VSCodePromptEvent({
    required this.source,
    required this.promptCount,
    required this.timestamp,
    this.lastLine,
    this.promptText,
  });
}

String _sanitizePrompt(String? raw) {
  if (raw == null) return '';
  // Unescape common sequences
  var cleaned = raw
      .replaceAll(r'\n', ' ')
      .replaceAll(r'\r', ' ')
      .replaceAll(r'\t', ' ')
      .replaceAll(RegExp(r'\"'), '"');
  cleaned = cleaned.replaceAll(RegExp(r'\s+'), ' ').trim();
  return cleaned;
}
