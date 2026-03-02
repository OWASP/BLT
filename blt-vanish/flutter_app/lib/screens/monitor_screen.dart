import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:uuid/uuid.dart';
import 'package:intl/intl.dart';
import '../services/storage_service.dart';
import '../models/monitor_entry.dart';

class MonitorScreen extends StatefulWidget {
  const MonitorScreen({super.key});

  @override
  State<MonitorScreen> createState() => _MonitorScreenState();
}

class _MonitorScreenState extends State<MonitorScreen>
    with SingleTickerProviderStateMixin {
  final _uuid = const Uuid();
  List<MonitorEntry> _entries = [];
  bool _isLoading = true;
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _loadEntries();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadEntries() async {
    setState(() {
      _isLoading = true;
    });

    try {
      final storageService = context.read<StorageService>();
      final entries = await storageService.getMonitorEntries();

      setState(() {
        _entries = entries;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
      });
    }
  }

  List<MonitorEntry> _entriesByType(MonitorType type) {
    return _entries.where((e) => e.type == type).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Column(
        children: [
          TabBar(
            controller: _tabController,
            tabs: const [
              Tab(icon: Icon(Icons.search), text: 'Keywords'),
              Tab(icon: Icon(Icons.gavel), text: 'Takedowns'),
              Tab(icon: Icon(Icons.person_search), text: 'Personal Info'),
            ],
          ),
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : TabBarView(
                    controller: _tabController,
                    children: [
                      _buildEntriesList(MonitorType.keyword),
                      _buildEntriesList(MonitorType.takedown),
                      _buildEntriesList(MonitorType.personalInfo),
                    ],
                  ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _showAddEntryDialog,
        tooltip: 'Add Monitor',
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildEntriesList(MonitorType type) {
    final entries = _entriesByType(type);

    if (entries.isEmpty) {
      return _buildEmptyState(type);
    }

    return RefreshIndicator(
      onRefresh: _loadEntries,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: entries.length,
        itemBuilder: (context, index) {
          return _buildEntryCard(entries[index]);
        },
      ),
    );
  }

  Widget _buildEntryCard(MonitorEntry entry) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    entry.keyword,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                Switch(
                  value: entry.isActive,
                  onChanged: (value) => _toggleEntry(entry, value),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                _buildTypeChip(entry.type),
                const SizedBox(width: 8),
                if (entry.matchCount > 0)
                  Chip(
                    avatar: const Icon(Icons.warning_amber, size: 16),
                    label: Text('${entry.matchCount} match(es)'),
                    backgroundColor: Colors.orange[50],
                    side: BorderSide(color: Colors.orange[300]!),
                    padding: EdgeInsets.zero,
                    materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  ),
              ],
            ),
            if (entry.notes != null && entry.notes!.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                entry.notes!,
                style: TextStyle(fontSize: 12, color: Colors.grey[600]),
              ),
            ],
            const SizedBox(height: 8),
            Row(
              children: [
                Icon(Icons.schedule, size: 14, color: Colors.grey[500]),
                const SizedBox(width: 4),
                Text(
                  'Added ${DateFormat.yMMMd().format(entry.createdAt)}',
                  style: TextStyle(fontSize: 12, color: Colors.grey[500]),
                ),
                if (entry.lastCheckedAt != null) ...[
                  const SizedBox(width: 12),
                  Icon(Icons.check_circle_outline,
                      size: 14, color: Colors.grey[500]),
                  const SizedBox(width: 4),
                  Text(
                    'Checked ${DateFormat.yMMMd().format(entry.lastCheckedAt!)}',
                    style: TextStyle(fontSize: 12, color: Colors.grey[500]),
                  ),
                ],
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.delete_outline, size: 20),
                  color: Colors.red[400],
                  onPressed: () => _showDeleteConfirmation(entry),
                  tooltip: 'Delete',
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTypeChip(MonitorType type) {
    IconData icon;
    String label;
    Color color;

    switch (type) {
      case MonitorType.keyword:
        icon = Icons.search;
        label = 'Keyword';
        color = Colors.blue;
        break;
      case MonitorType.takedown:
        icon = Icons.gavel;
        label = 'Takedown';
        color = Colors.purple;
        break;
      case MonitorType.personalInfo:
        icon = Icons.person_search;
        label = 'Personal Info';
        color = Colors.teal;
        break;
    }

    return Chip(
      avatar: Icon(icon, size: 14, color: color),
      label: Text(
        label,
        style: TextStyle(fontSize: 11, color: color),
      ),
      backgroundColor: color.withOpacity(0.1),
      side: BorderSide(color: color.withOpacity(0.3)),
      padding: EdgeInsets.zero,
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
    );
  }

  Widget _buildEmptyState(MonitorType type) {
    String title;
    String subtitle;
    IconData icon;

    switch (type) {
      case MonitorType.keyword:
        title = 'No keywords monitored';
        subtitle = 'Add keywords to track mentions of your data online';
        icon = Icons.search_off;
        break;
      case MonitorType.takedown:
        title = 'No takedowns monitored';
        subtitle = 'Track the status of your takedown requests';
        icon = Icons.gavel;
        break;
      case MonitorType.personalInfo:
        title = 'No personal info monitored';
        subtitle = 'Monitor when your personal information appears online';
        icon = Icons.person_search;
        break;
    }

    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, size: 64, color: Colors.grey[400]),
          const SizedBox(height: 16),
          Text(
            title,
            style: TextStyle(fontSize: 18, color: Colors.grey[600]),
          ),
          const SizedBox(height: 8),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 32),
            child: Text(
              subtitle,
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 14, color: Colors.grey[500]),
            ),
          ),
          const SizedBox(height: 24),
          FilledButton.icon(
            onPressed: _showAddEntryDialog,
            icon: const Icon(Icons.add),
            label: const Text('Add Monitor'),
          ),
        ],
      ),
    );
  }

  void _showAddEntryDialog() {
    final keywordController = TextEditingController();
    final notesController = TextEditingController();
    MonitorType selectedType = MonitorType.values[_tabController.index];
    final formKey = GlobalKey<FormState>();

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Add Monitor'),
          content: SingleChildScrollView(
            child: Form(
              key: formKey,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TextFormField(
                    controller: keywordController,
                    decoration: const InputDecoration(
                      labelText: 'Keyword or Info *',
                      border: OutlineInputBorder(),
                      prefixIcon: Icon(Icons.search),
                      hintText: 'e.g. John Doe, john@email.com',
                    ),
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return 'Please enter a keyword or info to monitor';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Monitor Type',
                    style: Theme.of(context).textTheme.labelLarge,
                  ),
                  const SizedBox(height: 8),
                  ...MonitorType.values.map(
                    (type) => RadioListTile<MonitorType>(
                      title: Text(_typeLabel(type)),
                      subtitle: Text(_typeDescription(type)),
                      value: type,
                      groupValue: selectedType,
                      onChanged: (value) {
                        if (value != null) {
                          setDialogState(() {
                            selectedType = value;
                          });
                        }
                      },
                      contentPadding: EdgeInsets.zero,
                    ),
                  ),
                  const SizedBox(height: 8),
                  TextFormField(
                    controller: notesController,
                    decoration: const InputDecoration(
                      labelText: 'Notes (optional)',
                      border: OutlineInputBorder(),
                      prefixIcon: Icon(Icons.notes),
                    ),
                    maxLines: 2,
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () async {
                if (formKey.currentState!.validate()) {
                  Navigator.pop(context);
                  await _addEntry(
                    keyword: keywordController.text.trim(),
                    type: selectedType,
                    notes: notesController.text.trim().isEmpty
                        ? null
                        : notesController.text.trim(),
                  );
                }
              },
              child: const Text('Add'),
            ),
          ],
        ),
      ),
    );
  }

  String _typeLabel(MonitorType type) {
    switch (type) {
      case MonitorType.keyword:
        return 'Keyword';
      case MonitorType.takedown:
        return 'Takedown';
      case MonitorType.personalInfo:
        return 'Personal Info';
    }
  }

  String _typeDescription(MonitorType type) {
    switch (type) {
      case MonitorType.keyword:
        return 'Track mentions of a specific word or phrase';
      case MonitorType.takedown:
        return 'Monitor takedown request status';
      case MonitorType.personalInfo:
        return 'Watch for personal information online';
    }
  }

  Future<void> _addEntry({
    required String keyword,
    required MonitorType type,
    String? notes,
  }) async {
    try {
      final storageService = context.read<StorageService>();
      final now = DateTime.now();
      final entry = MonitorEntry(
        id: _uuid.v4(),
        keyword: keyword,
        type: type,
        isActive: true,
        createdAt: now,
        updatedAt: now,
        notes: notes,
      );

      await storageService.saveMonitorEntry(entry);
      await _loadEntries();

      if (!mounted) return;

      // Switch to the tab matching the added entry's type
      _tabController.animateTo(MonitorType.values.indexOf(type));

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Monitor added successfully'),
          backgroundColor: Colors.green,
        ),
      );
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to add monitor: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _toggleEntry(MonitorEntry entry, bool isActive) async {
    try {
      final storageService = context.read<StorageService>();
      final updated = entry.copyWith(
        isActive: isActive,
        updatedAt: DateTime.now(),
      );
      await storageService.saveMonitorEntry(updated);
      await _loadEntries();
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to update monitor: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  void _showDeleteConfirmation(MonitorEntry entry) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Monitor?'),
        content: Text(
          'Are you sure you want to stop monitoring "${entry.keyword}"?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () async {
              Navigator.pop(context);
              await _deleteEntry(entry);
            },
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  Future<void> _deleteEntry(MonitorEntry entry) async {
    try {
      final storageService = context.read<StorageService>();
      await storageService.deleteMonitorEntry(entry.id);
      await _loadEntries();

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Monitor deleted'),
          backgroundColor: Colors.green,
        ),
      );
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to delete monitor: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }
}
