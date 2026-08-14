import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/opt_out_request.dart';
import '../models/user_data.dart';
import '../services/storage_service.dart';
import '../theme/blt_theme.dart';
import 'brokers_screen.dart';
import 'credential_hygiene_screen.dart';
import 'monitor_screen.dart';
import 'profile_screen.dart';
import 'requests_screen.dart';
import 'security_center_screen.dart';
import 'unified_triage_screen.dart';

/// Main authenticated home shell with dashboard and app navigation.
class HomeScreen extends StatefulWidget {
  /// Creates the home screen.
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _selectedIndex = 0;
  UserData? _userData;
  List<OptOutRequest> _requests = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    final storageService = context.read<StorageService>();
    
    setState(() {
      _isLoading = true;
    });

    try {
      final userData = await storageService.getUserData();
      final requests = await storageService.getRequests();

      setState(() {
        _userData = userData;
        _requests = requests;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
      });
    }
  }

  void _onItemTapped(int index) {
    setState(() {
      _selectedIndex = index;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        titleSpacing: 20,
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 34,
              height: 34,
              decoration: BoxDecoration(
                color: BltColors.red,
                borderRadius: BorderRadius.circular(10),
                boxShadow: [
                  BoxShadow(
                    color: BltColors.red.withValues(alpha: 0.22),
                    blurRadius: 24,
                    offset: const Offset(0, 10),
                  ),
                ],
              ),
              child: const Icon(
                Icons.visibility_off_rounded,
                color: Colors.white,
                size: 18,
              ),
            ),
            const SizedBox(width: 10),
            const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text('BLT Vanish'),
                Text(
                  'Privacy Tool',
                  style: TextStyle(
                    color: BltColors.muted,
                    fontSize: 10,
                    fontWeight: FontWeight.w500,
                    height: 1,
                  ),
                ),
              ],
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.info_outline),
            onPressed: () => _showAboutDialog(context),
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _buildSelectedScreen(),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: _onItemTapped,
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.dashboard_outlined),
            selectedIcon: Icon(Icons.dashboard),
            label: 'Dashboard',
          ),
          NavigationDestination(
            icon: Icon(Icons.business_outlined),
            selectedIcon: Icon(Icons.business),
            label: 'Brokers',
          ),
          NavigationDestination(
            icon: Icon(Icons.assignment_outlined),
            selectedIcon: Icon(Icons.assignment),
            label: 'Requests',
          ),
          NavigationDestination(
            icon: Icon(Icons.monitor_outlined),
            selectedIcon: Icon(Icons.monitor),
            label: 'Monitor',
          ),
          NavigationDestination(
            icon: Icon(Icons.timeline_outlined),
            selectedIcon: Icon(Icons.timeline),
            label: 'Triage',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person),
            label: 'Profile',
          ),
        ],
      ),
    );
  }

  Widget _buildSelectedScreen() {
    switch (_selectedIndex) {
      case 0:
        return _buildDashboard();
      case 1:
        return const BrokersScreen();
      case 2:
        return const RequestsScreen();
      case 3:
        return const MonitorScreen();
      case 4:
        return const UnifiedTriageScreen();
      case 5:
        return ProfileScreen(onProfileUpdated: _loadData);
      default:
        return _buildDashboard();
    }
  }

  Widget _buildDashboard() {
    return RefreshIndicator(
      onRefresh: _loadData,
      child: BltPageShell(
        padding: EdgeInsets.zero,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 28, 16, 24),
          children: [
            _buildHeroCard(),
            const SizedBox(height: 18),
            _buildStatsCard(),
            const SizedBox(height: 18),
            _buildQuickActionsCard(),
            const SizedBox(height: 18),
            _buildPrivacyTipsCard(),
          ],
        ),
      ),
    );
  }

  Widget _buildHeroCard() {
    final name = _userData?.firstName;
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 22, 20, 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const BltKicker('Open source'),
            const SizedBox(height: 18),
            Text.rich(
              TextSpan(
                children: [
                  TextSpan(text: name != null ? 'Welcome back,\n' : 'Make your\n'),
                  TextSpan(
                    text: name != null ? '$name.' : 'data vanish.',
                    style: const TextStyle(color: BltColors.red),
                  ),
                ],
              ),
              style: Theme.of(context).textTheme.displayLarge?.copyWith(
                    fontSize: 48,
                  ),
            ),
            const SizedBox(height: 16),
            Text(
              'Remove personal data from brokers, monitor privacy exposure, and keep the workflow encrypted on this device.',
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: 20),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                FilledButton.icon(
                  onPressed: () {
                    setState(() {
                      _selectedIndex = _userData == null ? 5 : 1;
                    });
                  },
                  icon: const Icon(Icons.person_outline),
                  label: Text(_userData == null ? 'Create Profile' : 'Find Brokers'),
                ),
                OutlinedButton.icon(
                  onPressed: () {
                    Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (_) => const SecurityCenterScreen(),
                      ),
                    );
                  },
                  icon: const Icon(Icons.security_outlined),
                  label: const Text('Launch Security Center'),
                ),
              ],
            ),
            const SizedBox(height: 18),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: BltColors.redTint,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: const Color(0xFFFECACA)),
              ),
              child: const Row(
                children: [
                  BltIconBox(Icons.lock_outline, size: 34),
                  SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'Local-first. No server. Your data never leaves your device.',
                      style: TextStyle(
                        color: BltColors.ink,
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        height: 1.35,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatsCard() {
    final totalRequests = _requests.length;
    final completedRequests =
        _requests.where((r) => r.status == RequestStatus.completed).length;
    final pendingRequests =
        _requests.where((r) => r.status == RequestStatus.pending ||
                               r.status == RequestStatus.submitted).length;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Your Privacy Progress',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 6),
            Text(
              'Broker removal progress, tracked locally.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 20),
            Row(
              children: [
                Expanded(
                  child: _buildStatItem(
                    'Total Requests',
                    totalRequests.toString(),
                    Icons.assignment_outlined,
                    BltColors.red,
                  ),
                ),
                Expanded(
                  child: _buildStatItem(
                    'Completed',
                    completedRequests.toString(),
                    Icons.check_circle_outline,
                    const Color(0xFF059669),
                  ),
                ),
                Expanded(
                  child: _buildStatItem(
                    'Pending',
                    pendingRequests.toString(),
                    Icons.hourglass_empty,
                    const Color(0xFFD97706),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatItem(String label, String value, IconData icon, Color color) {
    return Column(
      children: [
        Icon(icon, color: color, size: 32),
        const SizedBox(height: 8),
        Text(
          value,
          style: TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey[600],
          ),
        ),
      ],
    );
  }

  Widget _buildQuickActionsCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Quick Actions',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 6),
            Text(
              'Same workflow modules as the web client, shaped for native use.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 16),
            if (_userData == null)
              _buildQuickActionButton(
                'Set Up Profile',
                'Add your information to get started',
                Icons.person_add,
                BltColors.red,
                () {
                  setState(() {
                    _selectedIndex = 5;
                  });
                },
              )
            else ...[
              _buildQuickActionButton(
                'Scan Suspicious Link',
                'Open the Security Center phishing workflow',
                Icons.security,
                BltColors.red,
                () {
                  Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => const SecurityCenterScreen(),
                    ),
                  );
                },
              ),
              const SizedBox(height: 12),
              _buildQuickActionButton(
                'Find Brokers',
                'Search for data brokers',
                Icons.search,
                BltColors.red,
                () {
                  setState(() {
                    _selectedIndex = 1;
                  });
                },
              ),
              const SizedBox(height: 12),
              _buildQuickActionButton(
                'Check Credentials',
                'Analyze password strength and reuse locally',
                Icons.password_outlined,
                BltColors.red,
                () {
                  Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => const CredentialHygieneScreen(),
                    ),
                  );
                },
              ),
              const SizedBox(height: 12),
              _buildQuickActionButton(
                'Open Triage Queue',
                'Rank scans, credential findings, and remediation tasks',
                Icons.timeline,
                BltColors.red,
                () {
                  setState(() {
                    _selectedIndex = 4;
                  });
                },
              ),
              const SizedBox(height: 12),
              _buildQuickActionButton(
                'View Requests',
                'Check your opt-out requests',
                Icons.assignment,
                BltColors.red,
                () {
                  setState(() {
                    _selectedIndex = 2;
                  });
                },
              ),
              const SizedBox(height: 12),
              _buildQuickActionButton(
                'Manage Monitors',
                'Track keywords and personal info',
                Icons.monitor,
                BltColors.red,
                () {
                  setState(() {
                    _selectedIndex = 3;
                  });
                },
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildQuickActionButton(
    String title,
    String subtitle,
    IconData icon,
    Color color,
    VoidCallback onTap,
  ) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(color: BltColors.border),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(11),
              decoration: BoxDecoration(
                color: BltColors.redTint,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: BltColors.border),
              ),
              child: Icon(icon, color: BltColors.red),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    subtitle,
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.grey[600],
                    ),
                  ),
                ],
              ),
            ),
            Icon(Icons.chevron_right, color: Colors.grey[400]),
          ],
        ),
      ),
    );
  }

  Widget _buildPrivacyTipsCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const BltIconBox(Icons.lightbulb_outline, size: 36),
                const SizedBox(width: 8),
                Text(
                  'Privacy Tip',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              'Your data never leaves this device. SelfErase uses end-to-end encryption to keep your personal information secure.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }

  void _showAboutDialog(BuildContext context) {
    showAboutDialog(
      context: context,
      applicationName: 'BLT Vanish',
      applicationVersion: '1.0.0',
      applicationIcon: const Icon(Icons.visibility_off, size: 48, color: BltColors.red),
      applicationLegalese: '© 2025 OWASP BLT Project\n\nLicensed under AGPL-3.0',
      children: [
        const SizedBox(height: 16),
        const Text(
          'A privacy-first toolkit for managing and deleting your personal data online.',
        ),
        const SizedBox(height: 12),
        const Text(
          '🔒 All data encrypted locally\n'
          '🚫 No data sent to servers\n'
          '✅ Open-source and verifiable\n'
          '💪 You own and control everything',
          style: TextStyle(fontSize: 12),
        ),
      ],
    );
  }
}
