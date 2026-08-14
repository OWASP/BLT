import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/security/credential_snapshot.dart';
import '../services/credential_vault_service.dart';

/// Local-only credential hygiene screen for manual password analysis.
class CredentialHygieneScreen extends StatefulWidget {
  /// Creates the credential hygiene screen.
  const CredentialHygieneScreen({super.key});

  @override
  State<CredentialHygieneScreen> createState() => _CredentialHygieneScreenState();
}

class _CredentialHygieneScreenState extends State<CredentialHygieneScreen> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final TextEditingController _accountLabelController = TextEditingController();
  final TextEditingController _usernameController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();

  bool _isLoading = true;
  bool _isAnalyzing = false;
  bool _knownBreached = false;
  bool _obscurePassword = true;
  List<CredentialSnapshot> _snapshots = const <CredentialSnapshot>[];
  CredentialSnapshot? _latestAnalysis;

  @override
  void initState() {
    super.initState();
    _loadSnapshots();
  }

  @override
  void dispose() {
    _accountLabelController.dispose();
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _loadSnapshots() async {
    final vault = context.read<CredentialVaultService>();
    final snapshots = await vault.getSnapshots();

    if (!mounted) {
      return;
    }

    setState(() {
      _snapshots = snapshots;
      _isLoading = false;
    });
  }

  Future<void> _analyzeCredential() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _isAnalyzing = true;
    });

    final vault = context.read<CredentialVaultService>();
    final analysis = await vault.analyzeCredential(
      accountLabel: _accountLabelController.text.trim(),
      username: _usernameController.text.trim(),
      password: _passwordController.text,
      knownBreached: _knownBreached,
    );

    if (!mounted) {
      return;
    }

    setState(() {
      _latestAnalysis = analysis;
      _isAnalyzing = false;
    });
  }

  Future<void> _saveAnalysis() async {
    final analysis = _latestAnalysis;
    if (analysis == null) {
      return;
    }

    final vault = context.read<CredentialVaultService>();
    await vault.saveSnapshot(analysis);
    await _loadSnapshots();

    if (!mounted) {
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Credential snapshot saved securely on this device.'),
      ),
    );

    _passwordController.clear();
  }

  Future<void> _deleteSnapshot(String snapshotId) async {
    final vault = context.read<CredentialVaultService>();
    await vault.deleteSnapshot(snapshotId);
    await _loadSnapshots();
  }

  Color _severityColor(String severity) {
    switch (severity) {
      case 'critical':
        return const Color(0xFFD32F2F);
      case 'high':
        return const Color(0xFFF57C00);
      case 'medium':
        return const Color(0xFFFBC02D);
      default:
        return const Color(0xFF388E3C);
    }
  }

  Widget _buildAnalysisCard(CredentialSnapshot analysis) {
    final strengthPercent = (analysis.strengthScore * 100).toStringAsFixed(0);
    final riskPercent = (analysis.finalScore * 100).toStringAsFixed(0);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  analysis.severity.name.toUpperCase(),
                  style: TextStyle(
                    color: _severityColor(analysis.severity.name),
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  'Risk $riskPercent%',
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              '${analysis.accountLabel} · ${analysis.username}',
              style: TextStyle(color: Colors.grey[700]),
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: analysis.reasonCodes
                  .map((code) => Chip(label: Text(code)))
                  .toList(),
            ),
            const SizedBox(height: 16),
            Text('Strength score: $strengthPercent%'),
            const SizedBox(height: 6),
            LinearProgressIndicator(value: analysis.strengthScore),
            const SizedBox(height: 16),
            Text(analysis.rotationGuidance ?? ''),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: _saveAnalysis,
              icon: const Icon(Icons.save_outlined),
              label: const Text('Save Snapshot'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSnapshotList() {
    if (_snapshots.isEmpty) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Text(
            'No credential snapshots saved yet. Analyze a password to start building a local hygiene timeline.',
            style: TextStyle(color: Colors.grey[700]),
          ),
        ),
      );
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Saved Snapshots',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            ..._snapshots.map(
              (snapshot) => ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(snapshot.accountLabel),
                subtitle: Text(
                  '${snapshot.username} · ${snapshot.severity.name.toUpperCase()}',
                ),
                trailing: IconButton(
                  icon: const Icon(Icons.delete_outline),
                  onPressed: () => _deleteSnapshot(snapshot.id),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Credential Hygiene'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Analyze a password locally',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Only encrypted, hash-only snapshots are persisted. Raw passwords are never stored.',
                      style: TextStyle(color: Colors.grey[700]),
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _accountLabelController,
                      decoration: const InputDecoration(
                        labelText: 'Service or account label',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.shield_outlined),
                      ),
                      validator: (value) {
                        if (value == null || value.trim().isEmpty) {
                          return 'Enter a service or account label';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _usernameController,
                      decoration: const InputDecoration(
                        labelText: 'Username or email',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.person_outline),
                      ),
                      validator: (value) {
                        if (value == null || value.trim().isEmpty) {
                          return 'Enter the account identifier';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _passwordController,
                      obscureText: _obscurePassword,
                      decoration: InputDecoration(
                        labelText: 'Password',
                        border: const OutlineInputBorder(),
                        prefixIcon: const Icon(Icons.key_outlined),
                        suffixIcon: IconButton(
                          icon: Icon(
                            _obscurePassword
                                ? Icons.visibility_outlined
                                : Icons.visibility_off_outlined,
                          ),
                          onPressed: () {
                            setState(() {
                              _obscurePassword = !_obscurePassword;
                            });
                          },
                        ),
                      ),
                      validator: (value) {
                        if (value == null || value.isEmpty) {
                          return 'Enter a password to analyze';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 12),
                    CheckboxListTile(
                      value: _knownBreached,
                      contentPadding: EdgeInsets.zero,
                      onChanged: (value) {
                        setState(() {
                          _knownBreached = value ?? false;
                        });
                      },
                      title: const Text('Treat this credential as known-breached'),
                      subtitle: const Text(
                        'Useful for rehearsing response flows without calling an external breach service.',
                      ),
                    ),
                    const SizedBox(height: 8),
                    FilledButton.icon(
                      onPressed: _isAnalyzing ? null : _analyzeCredential,
                      icon: _isAnalyzing
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.analytics_outlined),
                      label: Text(
                        _isAnalyzing ? 'Analyzing...' : 'Analyze Credential',
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
          if (_latestAnalysis != null) ...[
            const SizedBox(height: 16),
            _buildAnalysisCard(_latestAnalysis!),
          ],
          const SizedBox(height: 16),
          _buildSnapshotList(),
        ],
      ),
    );
  }
}
