import 'package:flutter/material.dart';

import 'config/sender_config.dart';
import 'ingest/envelope.dart';
import 'ingest/ingest_client.dart';

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
  final _target = TextEditingController(text: 'https://example.com');
  final _ruleId = TextEditingController(text: 'http.missing-hsts');
  final _title = TextEditingController(text: 'Missing HSTS (client demo)');
  final _severity = TextEditingController(text: 'high');

  final _client = IngestClient();
  bool _loading = true;
  bool _sending = false;
  String? _status;

  @override
  void initState() {
    super.initState();
    _loadConfig();
  }

  Future<void> _loadConfig() async {
    final cfg = await SenderConfig.load();
    if (!mounted) return;
    setState(() {
      _baseUrl.text = cfg.baseUrl;
      _orgId.text = cfg.orgId;
      _senderId.text = cfg.senderId;
      _kid.text = cfg.kid;
      _secretHex.text = cfg.secretHex;
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

  Future<void> _send() async {
    setState(() {
      _sending = true;
      _status = null;
    });
    try {
      await _saveConfig();
      if (!mounted) return;
      final stamp = DateTime.now().toUtc().millisecondsSinceEpoch;
      final payload = <String, Object?>{
        'rule_id': _ruleId.text.trim(),
        'severity': _severity.text.trim(),
        'title': _title.text.trim(),
        'target': _target.text.trim(),
        'fingerprint': 'fp-flutter-$stamp',
      };
      final result = await _client.sendFinding(
        baseUrl: _baseUrl.text.trim(),
        orgId: _orgId.text.trim(),
        senderId: _senderId.text.trim(),
        kid: _kid.text.trim(),
        secret: secretFromHex(_secretHex.text.trim()),
        payload: payload,
      );
      if (!mounted) return;
      setState(() {
        if (result.ok) {
          _status =
              'OK ${result.statusCode} — finding_id=${result.findingId ?? result.body}';
        } else {
          _status = 'ERROR ${result.statusCode} — ${result.body}';
        }
      });
    } catch (e) {
      if (mounted) {
        setState(() => _status = 'ERROR $e');
      }
    } finally {
      if (mounted) {
        setState(() => _sending = false);
      }
    }
  }

  @override
  void dispose() {
    _baseUrl.dispose();
    _orgId.dispose();
    _senderId.dispose();
    _kid.dispose();
    _secretHex.dispose();
    _target.dispose();
    _ruleId.dispose();
    _title.dispose();
    _severity.dispose();
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
            'Desktop producer for ztr-finding-1 → POST /api/ingest',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Text(
            'Configure sender credentials, fill a finding, and send a signed envelope. '
            'Demo defaults match local_dev/send_finding.py (loopback only).',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 20),
          _section('Sender config', [
            _field(_baseUrl, 'API base URL'),
            _field(_orgId, 'org_id'),
            _field(_senderId, 'sender_id'),
            _field(_kid, 'kid'),
            _field(_secretHex, 'HMAC secret (hex)', obscure: true),
            Align(
              alignment: Alignment.centerLeft,
              child: OutlinedButton(
                onPressed: _sending ? null : _saveConfig,
                child: const Text('Save config'),
              ),
            ),
          ]),
          const SizedBox(height: 16),
          _section('Finding (plaintext preview)', [
            _field(_target, 'target'),
            _field(_ruleId, 'rule_id'),
            _field(_title, 'title'),
            _field(_severity, 'severity'),
          ]),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _sending ? null : _send,
            icon: _sending
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.send),
            label: Text(_sending ? 'Sending…' : 'Sign & POST /api/ingest'),
          ),
          if (_status != null) ...[
            const SizedBox(height: 16),
            SelectableText(_status!, style: Theme.of(context).textTheme.bodyLarge),
          ],
        ],
      ),
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
