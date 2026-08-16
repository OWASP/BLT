import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import 'config/sender_config.dart';
import 'detect/http_headers.dart';
import 'detect/normalize.dart';
import 'history/send_history.dart';
import 'ingest/envelope.dart';
import 'ingest/ingest_client.dart';
import 'ingest/redact.dart';
import 'queue/outbox.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const NetGuardianClientApp());
}

class NetGuardianClientApp extends StatelessWidget {
  const NetGuardianClientApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'NetGuardian Client',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFFB45309),
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final _baseUrl = TextEditingController();
  final _orgId = TextEditingController();
  final _senderId = TextEditingController();
  final _kid = TextEditingController();
  final _secretHex = TextEditingController();
  final _scanUrl = TextEditingController(text: 'https://example.com');

  final _client = IngestClient();
  final _outbox = OutboxStore();
  final _historyStore = SendHistoryStore();

  bool _loading = true;
  bool _busy = false;
  bool _redactBeforeSend = true;
  String? _status;
  List<DetectionFinding> _preview = [];
  List<OutboxItem> _queue = [];
  List<HistoryItem> _history = [];
  final Set<String> _selected = {};

  @override
  void initState() {
    super.initState();
    _bootstrap();
  }

  Future<void> _bootstrap() async {
    final cfg = await SenderConfig.load();
    final queue = await _outbox.load();
    final history = await _historyStore.load();
    if (!mounted) return;
    setState(() {
      _baseUrl.text = cfg.baseUrl;
      _orgId.text = cfg.orgId;
      _senderId.text = cfg.senderId;
      _kid.text = cfg.kid;
      _secretHex.text = cfg.secretHex;
      _queue = queue;
      _history = history;
      _loading = false;
    });
  }

  Future<void> _saveConfig() async {
    final cfg = SenderConfig(
      baseUrl: _baseUrl.text.trim(),
      orgId: _orgId.text.trim(),
      senderId: _senderId.text.trim(),
      kid: _kid.text.trim(),
      secretHex: _secretHex.text.trim(),
    );
    await cfg.save();
    if (!mounted) return;
    setState(() => _status = 'Config saved.');
  }

  Future<void> _scan() async {
    setState(() {
      _busy = true;
      _status = null;
      _preview = [];
      _selected.clear();
    });
    try {
      final findings = await scanUrlHeaders(_scanUrl.text.trim());
      if (!mounted) return;
      setState(() {
        _preview = findings;
        _selected.addAll(findings.map((f) => f.fingerprint));
        _status = findings.isEmpty
            ? 'Scan complete — no header findings.'
            : 'Scan complete — ${findings.length} finding(s). Review, then queue or send.';
      });
    } catch (e) {
      if (mounted) setState(() => _status = 'Scan error: $e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  List<Map<String, Object?>> _selectedPayloads() {
    return _preview
        .where((f) => _selected.contains(f.fingerprint))
        .map((f) {
          final payload = f.toPayload();
          return _redactBeforeSend ? redactPayload(payload) : payload;
        })
        .toList();
  }

  Future<void> _enqueueSelected() async {
    final payloads = _selectedPayloads();
    if (payloads.isEmpty) {
      setState(() => _status = 'Nothing selected to queue.');
      return;
    }
    await _outbox.enqueue(payloads);
    final queue = await _outbox.load();
    if (!mounted) return;
    setState(() {
      _queue = queue;
      _status =
          'Queued ${payloads.length} finding(s)${_redactBeforeSend ? ' (redacted)' : ''}.';
    });
  }

  Future<IngestResult> _sendOne(Map<String, Object?> payload) {
    return _client.sendFinding(
      baseUrl: _baseUrl.text.trim(),
      orgId: _orgId.text.trim(),
      senderId: _senderId.text.trim(),
      kid: _kid.text.trim(),
      secret: secretFromHex(_secretHex.text.trim()),
      payload: payload,
    );
  }

  Future<void> _recordSuccess(Map<String, Object?> payload, String? findingId) {
    return _historyStore.record(
      payload: payload,
      findingId: findingId,
      redacted: _redactBeforeSend,
    );
  }

  Future<void> _sendSelectedNow() async {
    await _saveConfig();
    if (!mounted) return;
    final payloads = _selectedPayloads();
    if (payloads.isEmpty) {
      setState(() => _status = 'Nothing selected to send.');
      return;
    }
    setState(() {
      _busy = true;
      _status = 'Sending ${payloads.length} finding(s)…';
    });
    var ok = 0;
    var fail = 0;
    try {
      for (final payload in payloads) {
        try {
          final result = await _sendOne(payload);
          if (result.ok) {
            ok++;
            await _recordSuccess(payload, result.findingId);
          } else {
            fail++;
            await _outbox.enqueue([payload]);
          }
        } catch (_) {
          fail++;
          await _outbox.enqueue([payload]);
        }
      }
      final queue = await _outbox.load();
      final history = await _historyStore.load();
      if (!mounted) return;
      setState(() {
        _queue = queue;
        _history = history;
        _status =
            'Send finished — ok=$ok failed=$fail (failures queued for retry).';
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _retryQueue() async {
    await _saveConfig();
    if (!mounted) return;
    setState(() {
      _busy = true;
      _status = 'Retrying outbox…';
    });
    try {
      final items = await _outbox.load();
      for (final item in items) {
        if (item.status == OutboxStatus.sent) continue;
        item.attempts += 1;
        try {
          final result = await _sendOne(item.payload);
          if (result.ok) {
            item.status = OutboxStatus.sent;
            item.findingId = result.findingId;
            item.lastError = null;
            await _recordSuccess(item.payload, result.findingId);
          } else {
            item.status = OutboxStatus.failed;
            item.lastError = '${result.statusCode} ${result.body}';
          }
        } catch (e) {
          item.status = OutboxStatus.failed;
          item.lastError = e.toString();
        }
      }
      await _outbox.save(items);
      final history = await _historyStore.load();
      if (!mounted) return;
      final pending =
          items.where((i) => i.status != OutboxStatus.sent).length;
      final sent = items.where((i) => i.status == OutboxStatus.sent).length;
      setState(() {
        _queue = items;
        _history = history;
        _status = 'Outbox retry done — sent=$sent still_pending=$pending';
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _clearSent() async {
    final items =
        (await _outbox.load()).where((i) => i.status != OutboxStatus.sent).toList();
    await _outbox.save(items);
    if (!mounted) return;
    setState(() {
      _queue = items;
      _status = 'Cleared sent outbox items.';
    });
  }

  Future<void> _clearHistory() async {
    await _historyStore.clear();
    if (!mounted) return;
    setState(() {
      _history = [];
      _status = 'Cleared send history.';
    });
  }

  Uri _triageUri({String? findingId}) {
    final base = _baseUrl.text.trim().replaceAll(RegExp(r'/+$'), '');
    final uri = Uri.parse('$base/triage.html');
    if (findingId == null || findingId.isEmpty) return uri;
    return uri.replace(queryParameters: {'finding': findingId});
  }

  Future<void> _openTriage({String? findingId}) async {
    final uri = _triageUri(findingId: findingId);
    final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (!mounted) return;
    setState(() {
      _status = ok
          ? 'Opened triage: $uri'
          : 'Could not open triage URL: $uri';
    });
  }

  @override
  void dispose() {
    _baseUrl.dispose();
    _orgId.dispose();
    _senderId.dispose();
    _kid.dispose();
    _secretHex.dispose();
    _scanUrl.dispose();
    _client.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    return Scaffold(
      appBar: AppBar(title: const Text('NetGuardian Client')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            'Find → preview → sign → POST /api/ingest (with offline queue)',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Text(
            'C3: header scan, redaction toggle, outbox retry, local send history, '
            'and triage deep-link. Demo sender defaults are loopback-only.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 20),
          _section('Sender config', [
            _field(_baseUrl, 'API base URL'),
            _field(_orgId, 'org_id'),
            _field(_senderId, 'sender_id'),
            _field(_kid, 'kid'),
            _field(_secretHex, 'HMAC secret (hex)', obscure: true),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Redact secrets before send'),
              subtitle: const Text(
                'Strips password/token/api_key/… from evidence (server also redacts on read)',
              ),
              value: _redactBeforeSend,
              onChanged: _busy
                  ? null
                  : (v) => setState(() => _redactBeforeSend = v),
            ),
            Wrap(
              spacing: 8,
              children: [
                OutlinedButton(
                  onPressed: _busy ? null : _saveConfig,
                  child: const Text('Save config'),
                ),
                OutlinedButton.icon(
                  onPressed: _busy ? null : () => _openTriage(),
                  icon: const Icon(Icons.open_in_new),
                  label: const Text('Open triage'),
                ),
              ],
            ),
          ]),
          const SizedBox(height: 16),
          _section('Detect (HTTP headers)', [
            _field(_scanUrl, 'Target URL'),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilledButton.icon(
                  onPressed: _busy ? null : _scan,
                  icon: const Icon(Icons.search),
                  label: const Text('Scan headers'),
                ),
                OutlinedButton(
                  onPressed: _busy || _preview.isEmpty ? null : _enqueueSelected,
                  child: const Text('Queue selected'),
                ),
                FilledButton(
                  onPressed: _busy || _preview.isEmpty ? null : _sendSelectedNow,
                  child: const Text('Sign & send selected'),
                ),
              ],
            ),
            if (_preview.isNotEmpty) ...[
              const SizedBox(height: 12),
              ..._preview.map(_findingTile),
            ],
          ]),
          const SizedBox(height: 16),
          _section('Outbox (offline queue)', [
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilledButton.icon(
                  onPressed: _busy || _queue.isEmpty ? null : _retryQueue,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Retry pending/failed'),
                ),
                OutlinedButton(
                  onPressed: _busy ? null : _clearSent,
                  child: const Text('Clear sent'),
                ),
              ],
            ),
            const SizedBox(height: 8),
            if (_queue.isEmpty)
              const Text('Queue empty.')
            else
              ..._queue.map((item) {
                return ListTile(
                  dense: true,
                  title: Text(
                    '${item.status.name} · ${item.payload['rule_id']} · ${item.payload['target']}',
                  ),
                  subtitle: Text(
                    item.lastError ??
                        (item.findingId != null
                            ? 'finding_id=${item.findingId}'
                            : 'attempts=${item.attempts}'),
                  ),
                  trailing: item.findingId == null
                      ? null
                      : IconButton(
                          tooltip: 'Open triage',
                          icon: const Icon(Icons.open_in_new),
                          onPressed: _busy
                              ? null
                              : () => _openTriage(findingId: item.findingId),
                        ),
                );
              }),
          ]),
          const SizedBox(height: 16),
          _section('Send history', [
            Align(
              alignment: Alignment.centerLeft,
              child: OutlinedButton(
                onPressed: _busy || _history.isEmpty ? null : _clearHistory,
                child: const Text('Clear history'),
              ),
            ),
            const SizedBox(height: 8),
            if (_history.isEmpty)
              const Text('No sends recorded yet.')
            else
              ..._history.take(30).map((item) {
                final when = DateTime.fromMillisecondsSinceEpoch(
                  item.sentAtMs,
                  isUtc: true,
                ).toLocal();
                return ListTile(
                  dense: true,
                  title: Text(
                    '${item.severity.toUpperCase()} · ${item.ruleId} · ${item.target}',
                  ),
                  subtitle: Text(
                    '${when.toIso8601String()} · '
                    '${item.findingId ?? 'no finding_id'}'
                    '${item.redacted ? ' · redacted' : ''}',
                  ),
                  trailing: item.findingId == null
                      ? null
                      : IconButton(
                          tooltip: 'Open triage',
                          icon: const Icon(Icons.open_in_new),
                          onPressed: _busy
                              ? null
                              : () => _openTriage(findingId: item.findingId),
                        ),
                );
              }),
          ]),
          if (_status != null) ...[
            const SizedBox(height: 16),
            SelectableText(_status!, style: Theme.of(context).textTheme.bodyLarge),
          ],
        ],
      ),
    );
  }

  Widget _findingTile(DetectionFinding f) {
    final selected = _selected.contains(f.fingerprint);
    return CheckboxListTile(
      value: selected,
      dense: true,
      onChanged: _busy
          ? null
          : (v) {
              setState(() {
                if (v == true) {
                  _selected.add(f.fingerprint);
                } else {
                  _selected.remove(f.fingerprint);
                }
              });
            },
      title: Text('${f.severity.toUpperCase()} · ${f.ruleId}'),
      subtitle: Text('${f.title}\n${f.fingerprint}'),
      isThreeLine: true,
    );
  }

  Widget _section(String title, List<Widget> children) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(title, style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 12),
            ...children,
          ],
        ),
      ),
    );
  }

  Widget _field(
    TextEditingController controller,
    String label, {
    bool obscure = false,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: TextField(
        controller: controller,
        obscureText: obscure,
        decoration: InputDecoration(
          labelText: label,
          border: const OutlineInputBorder(),
          isDense: true,
        ),
      ),
    );
  }
}
