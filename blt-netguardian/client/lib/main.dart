import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:url_launcher/url_launcher.dart';

import 'config/sender_config.dart';
import 'detect/crawl.dart';
import 'detect/http_headers.dart';
import 'detect/normalize.dart';
import 'history/send_history.dart';
import 'ingest/envelope.dart';
import 'ingest/ingest_client.dart';
import 'ingest/payload_crypto.dart';
import 'ingest/redact.dart';
import 'queue/outbox.dart';
import 'theme/hud.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const NetGuardianClientApp());
}

class NetGuardianClientApp extends StatelessWidget {
  const NetGuardianClientApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'NETGUARDIAN',
      theme: Hud.theme(),
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
  final _payloadKey = TextEditingController();
  final _scanUrl = TextEditingController(text: 'https://example.com');

  final _client = IngestClient();
  final _outbox = OutboxStore();
  final _historyStore = SendHistoryStore();

  bool _loading = true;
  bool _busy = false;
  bool _redactBeforeSend = true;
  bool _encrypt = true;
  bool _continuousCrawl = true;
  bool? _apiLive;
  String? _status;
  List<DetectionFinding> _preview = [];
  List<String> _discoveredHosts = [];
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
      _payloadKey.text = cfg.payloadKeyB64;
      _encrypt = cfg.encrypt;
      _redactBeforeSend = cfg.redactBeforeSend;
      _queue = queue;
      _history = history;
      _loading = false;
    });
    _ping();
  }

  Future<void> _ping() async {
    final base = _baseUrl.text.trim();
    setState(() {
      _apiLive = null;
      _status = 'Pinging $base…';
    });
    final live = await _client.ping(base);
    if (!mounted) return;
    final msg = live
        ? 'API reachable at $base'
        : 'API DOWN — start serve.py and set base URL to http://127.0.0.1:8787';
    setState(() {
      _apiLive = live;
      _status = msg;
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(msg),
        backgroundColor: live ? Hud.low : Hud.accent,
        duration: const Duration(seconds: 4),
      ),
    );
  }

  SenderConfig _currentConfig() {
    return SenderConfig(
      baseUrl: _baseUrl.text.trim(),
      orgId: _orgId.text.trim(),
      senderId: _senderId.text.trim(),
      kid: _kid.text.trim(),
      secretHex: _secretHex.text.trim(),
      payloadKeyB64: _payloadKey.text.trim(),
      encrypt: _encrypt,
      redactBeforeSend: _redactBeforeSend,
    );
  }

  Future<void> _saveConfig() async {
    await _currentConfig().save();
    if (!mounted) return;
    setState(() => _status = 'Config saved.');
    _ping();
  }

  Future<void> _scan() async {
    setState(() {
      _busy = true;
      _status = null;
      _preview = [];
      _discoveredHosts = [];
      _selected.clear();
    });
    try {
      if (_continuousCrawl) {
        await _crawlScan();
      } else {
        final findings = await scanUrlHeaders(
          _scanUrl.text.trim(),
          apiBaseUrl: _baseUrl.text.trim(),
        );
        if (!mounted) return;
        setState(() {
          _preview = findings;
          _selected.addAll(findings.map((f) => f.fingerprint));
          _status = findings.isEmpty
              ? 'Scan complete — no header findings.'
              : 'Scan complete — ${findings.length} finding(s). Review, then queue or send.';
        });
      }
    } catch (e) {
      if (mounted) setState(() => _status = 'Scan error: $e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _crawlScan() async {
    final seed = _scanUrl.text.trim();
    final result = await crawlAndScan(
      seed,
      config: const CrawlConfig(
        maxPages: 20,
        maxNewHosts: 30,
        maxSameHostPaths: 6,
        delay: Duration(milliseconds: 350),
      ),
      onProgress: (p) {
        if (!mounted) return;
        setState(() {
          _status = p.done
              ? null
              : 'Crawling ${p.currentUrl} · pages ${p.scanned} · '
                  'queue ${p.queued} · hosts ${p.discoveredHosts} · '
                  'findings ${p.findingsSoFar}';
        });
      },
    );
    if (!mounted) return;
    setState(() {
      _preview = result.findings;
      _discoveredHosts = List.of(result.discoveredHosts);
      _selected
        ..clear()
        ..addAll(result.findings.map((f) => f.fingerprint));
      _status =
          'Crawl complete — ${result.pagesScanned} page(s), '
          '${result.discoveredHosts.length} new host(s), '
          '${result.findings.length} finding(s). Review, then queue or send.';
    });
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
    final cfg = _currentConfig();
    return _client.sendFinding(
      baseUrl: cfg.baseUrl,
      orgId: cfg.orgId,
      senderId: cfg.senderId,
      kid: cfg.kid,
      secret: secretFromHex(cfg.secretHex),
      payload: payload,
      encrypt: cfg.encrypt,
      payloadKey: cfg.encrypt && cfg.payloadKeyB64.isNotEmpty
          ? payloadKeyFromB64(cfg.payloadKeyB64)
          : null,
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
            _status = 'Ingest ${result.statusCode}: ${result.message}';
          }
        } catch (e) {
          fail++;
          await _outbox.enqueue([payload]);
          _status = 'Send error: $e';
        }
      }
      final queue = await _outbox.load();
      final history = await _historyStore.load();
      if (!mounted) return;
      setState(() {
        _queue = queue;
        _history = history;
        _status =
            'Send finished — ok=$ok failed=$fail (failures queued for retry). ${_status ?? ''}';
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
            item.lastError = '${result.statusCode} ${result.message}';
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
      _status = ok ? 'Opened triage: $uri' : 'Could not open triage URL: $uri';
    });
  }

  @override
  void dispose() {
    _baseUrl.dispose();
    _orgId.dispose();
    _senderId.dispose();
    _kid.dispose();
    _secretHex.dispose();
    _payloadKey.dispose();
    _scanUrl.dispose();
    _client.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    final cfg = _currentConfig();
    return Scaffold(
      appBar: AppBar(
        title: const Text('NETGUARDIAN'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Center(
              child: Text(
                _apiLive == null
                    ? 'API · …'
                    : (_apiLive! ? 'API · LIVE' : 'API · DOWN'),
                style: TextStyle(
                  color: _apiLive == true ? Hud.low : Hud.accent,
                  fontSize: 11,
                  letterSpacing: 1.6,
                ),
              ),
            ),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'DETECT → SIGN → INGEST → TRIAGE',
            style: GoogleFonts.orbitron(
              color: Hud.gold,
              fontSize: 12,
              letterSpacing: 2,
            ),
          ),
          const SizedBox(height: 6),
          const Text(
            'Client-side crawl discovers domains from page source, header-scans '
            'each target, AES-256-GCM encrypts, HMAC ztr-finding-1 ingest, '
            'outbox retry, triage deep-link. Worker never spiders third parties.',
            style: TextStyle(color: Hud.muted, fontSize: 12),
          ),
          if (!cfg.isLoopback) ...[
            const SizedBox(height: 10),
            const Text(
              'Remote base URL — demo secrets must not be used. '
              'Provide org HMAC + payload key issued for this environment.',
              style: TextStyle(color: Hud.high, fontSize: 12),
            ),
          ],
          const SizedBox(height: 16),
          HudPanel(title: 'Sender config', children: [
            _field(_baseUrl, 'API base URL'),
            _field(_orgId, 'org_id'),
            _field(_senderId, 'sender_id'),
            _field(_kid, 'kid'),
            _field(_secretHex, 'HMAC secret (hex)', obscure: true),
            _field(_payloadKey, 'AES-256 payload key (base64)', obscure: true),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Encrypt payload (AES-256-GCM)'),
              subtitle: const Text(
                'Required off-loopback. AAD = org_id. Server decrypts on authorized view.',
              ),
              value: _encrypt,
              onChanged: _busy
                  ? null
                  : (v) => setState(() => _encrypt = v),
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Redact secrets before send'),
              subtitle: const Text(
                'Strips password/token/api_key/… (server also redacts on read)',
              ),
              value: _redactBeforeSend,
              onChanged: _busy
                  ? null
                  : (v) => setState(() => _redactBeforeSend = v),
            ),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                OutlinedButton(
                  onPressed: _busy ? null : _saveConfig,
                  child: const Text('Save config'),
                ),
                OutlinedButton(
                  onPressed: _busy ? null : _ping,
                  child: const Text('Ping API'),
                ),
                OutlinedButton.icon(
                  onPressed: _busy ? null : () => _openTriage(),
                  icon: const Icon(Icons.open_in_new, size: 16),
                  label: const Text('Open triage'),
                ),
              ],
            ),
          ]),
          const SizedBox(height: 12),
          HudPanel(title: 'Detect (HTTP headers + crawl)', children: [
            _field(_scanUrl, 'Seed URL'),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Continuous crawl (discover domains)'),
              subtitle: const Text(
                'Fetch HTML, extract href/src hosts, enqueue + header-scan. '
                'Runs on this machine only.',
              ),
              value: _continuousCrawl,
              onChanged: _busy
                  ? null
                  : (v) => setState(() => _continuousCrawl = v),
            ),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilledButton.icon(
                  onPressed: _busy ? null : _scan,
                  icon: const Icon(Icons.search, size: 16),
                  label: Text(
                    _continuousCrawl ? 'Crawl & scan' : 'Scan headers',
                  ),
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
            if (_discoveredHosts.isNotEmpty) ...[
              const SizedBox(height: 10),
              Text(
                'Discovered hosts (${_discoveredHosts.length}): '
                '${_discoveredHosts.take(12).join(', ')}'
                '${_discoveredHosts.length > 12 ? '…' : ''}',
                style: const TextStyle(color: Hud.gold, fontSize: 11),
              ),
            ],
            if (_preview.isEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  _busy
                      ? (_continuousCrawl ? 'Crawling…' : 'Scanning…')
                      : 'Crawl/scan first — Sign & send enables after findings appear.',
                  style: const TextStyle(color: Hud.muted, fontSize: 11),
                ),
              ),
            if (_preview.isNotEmpty) ...[
              const SizedBox(height: 12),
              ..._preview.map(_findingTile),
            ],
          ]),
          const SizedBox(height: 12),
          HudPanel(title: 'Outbox (offline queue)', children: [
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilledButton.icon(
                  onPressed: _busy || _queue.isEmpty ? null : _retryQueue,
                  icon: const Icon(Icons.refresh, size: 16),
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
              const Text('Queue empty.', style: TextStyle(color: Hud.muted))
            else
              ..._queue.map((item) {
                return ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  title: Text(
                    '${item.status.name} · ${item.payload['rule_id']} · ${item.payload['target']}',
                  ),
                  subtitle: Text(
                    item.lastError ??
                        (item.findingId != null
                            ? 'finding_id=${item.findingId}'
                            : 'attempts=${item.attempts}'),
                    style: const TextStyle(color: Hud.muted, fontSize: 11),
                  ),
                  trailing: item.findingId == null
                      ? null
                      : IconButton(
                          tooltip: 'Open triage',
                          icon: const Icon(Icons.open_in_new, color: Hud.gold),
                          onPressed: _busy
                              ? null
                              : () => _openTriage(findingId: item.findingId),
                        ),
                );
              }),
          ]),
          const SizedBox(height: 12),
          HudPanel(title: 'Send history', children: [
            Align(
              alignment: Alignment.centerLeft,
              child: OutlinedButton(
                onPressed: _busy || _history.isEmpty ? null : _clearHistory,
                child: const Text('Clear history'),
              ),
            ),
            const SizedBox(height: 8),
            if (_history.isEmpty)
              const Text('No sends recorded yet.', style: TextStyle(color: Hud.muted))
            else
              ..._history.take(30).map((item) {
                final when = DateTime.fromMillisecondsSinceEpoch(
                  item.sentAtMs,
                  isUtc: true,
                ).toLocal();
                return ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  leading: SeverityChip(item.severity),
                  title: Text('${item.ruleId} · ${item.target}'),
                  subtitle: Text(
                    '${when.toIso8601String()} · '
                    '${item.findingId ?? 'no finding_id'}'
                    '${item.redacted ? ' · redacted' : ''}',
                    style: const TextStyle(color: Hud.muted, fontSize: 11),
                  ),
                  trailing: item.findingId == null
                      ? null
                      : IconButton(
                          tooltip: 'Open triage',
                          icon: const Icon(Icons.open_in_new, color: Hud.gold),
                          onPressed: _busy
                              ? null
                              : () => _openTriage(findingId: item.findingId),
                        ),
                );
              }),
          ]),
          if (_status != null) ...[
            const SizedBox(height: 16),
            SelectableText(
              _status!,
              style: const TextStyle(color: Hud.gold, fontSize: 13),
            ),
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
      contentPadding: EdgeInsets.zero,
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
      title: Row(
        children: [
          SeverityChip(f.severity),
          const SizedBox(width: 8),
          Expanded(child: Text(f.ruleId)),
        ],
      ),
      subtitle: Text(
        '${f.title}\n${f.fingerprint}',
        style: const TextStyle(color: Hud.muted, fontSize: 11),
      ),
      isThreeLine: true,
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
        style: const TextStyle(fontSize: 13),
        decoration: InputDecoration(labelText: label),
      ),
    );
  }
}
