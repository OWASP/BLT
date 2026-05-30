import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/target.dart';
import '../providers/target_provider.dart';

class TargetsScreen extends StatefulWidget {
  const TargetsScreen({super.key});

  @override
  State<TargetsScreen> createState() => _TargetsScreenState();
}

class _TargetsScreenState extends State<TargetsScreen> {
  bool? _filterActive;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<TargetProvider>().loadTargets();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Column(
        children: [
          _buildFilterBar(),
          Expanded(child: _buildTargetList()),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _showAddTargetDialog,
        child: const Icon(Icons.add),
        tooltip: 'Register Target',
      ),
    );
  }

  Widget _buildFilterBar() {
    return Container(
      padding: const EdgeInsets.all(8),
      child: Row(
        children: [
          const Text('Filter: '),
          const SizedBox(width: 8),
          _buildFilterChip('All', null),
          _buildFilterChip('Active', true),
          _buildFilterChip('Inactive', false),
        ],
      ),
    );
  }

  Widget _buildFilterChip(String label, bool? isActive) {
    final isSelected = _filterActive == isActive;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4),
      child: FilterChip(
        label: Text(label),
        selected: isSelected,
        onSelected: (selected) {
          setState(() {
            _filterActive = selected ? isActive : null;
          });
          context.read<TargetProvider>().loadTargets(isActive: _filterActive);
        },
      ),
    );
  }

  Widget _buildTargetList() {
    return Consumer<TargetProvider>(
      builder: (context, provider, child) {
        if (provider.isLoading) {
          return const Center(child: CircularProgressIndicator());
        }

        if (provider.errorMessage != null) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text('Error: ${provider.errorMessage}'),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: () => provider.loadTargets(isActive: _filterActive),
                  child: const Text('Retry'),
                ),
              ],
            ),
          );
        }

        final targets = provider.targets;
        if (targets.isEmpty) {
          return const Center(child: Text('No targets found'));
        }

        return RefreshIndicator(
          onRefresh: () => provider.loadTargets(isActive: _filterActive),
          child: ListView.builder(
            itemCount: targets.length,
            itemBuilder: (context, index) {
              final target = targets[index];
              return _buildTargetCard(target);
            },
          ),
        );
      },
    );
  }

  Widget _buildTargetCard(Target target) {
    IconData icon;
    Color iconColor;
    
    switch (target.type) {
      case TargetType.website:
        icon = Icons.language;
        iconColor = Colors.blue;
        break;
      case TargetType.smartContract:
        icon = Icons.code;
        iconColor = Colors.purple;
        break;
      case TargetType.api:
        icon = Icons.api;
        iconColor = Colors.green;
        break;
      case TargetType.repository:
        icon = Icons.folder;
        iconColor = Colors.orange;
        break;
    }

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: iconColor.withOpacity(0.2),
          child: Icon(icon, color: iconColor),
        ),
        title: Text(target.url),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Type: ${target.type.name}'),
            Text('ID: ${target.id}'),
            Text('Registered: ${_formatDate(target.registeredAt)}'),
          ],
        ),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Chip(
              label: Text(
                target.isActive ? 'ACTIVE' : 'INACTIVE',
                style: TextStyle(
                  color: target.isActive ? Colors.green : Colors.grey,
                  fontSize: 10,
                ),
              ),
              backgroundColor: target.isActive 
                  ? Colors.green.withOpacity(0.1)
                  : Colors.grey.withOpacity(0.1),
            ),
            if (target.isActive)
              IconButton(
                icon: const Icon(Icons.stop, color: Colors.red),
                onPressed: () => _deactivateTarget(target.id),
                tooltip: 'Deactivate',
              ),
          ],
        ),
        isThreeLine: true,
      ),
    );
  }

  void _showAddTargetDialog() {
    final urlController = TextEditingController();
    TargetType selectedType = TargetType.website;
    
    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: const Text('Register New Target'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: urlController,
                  decoration: const InputDecoration(
                    labelText: 'Target URL',
                    hintText: 'https://example.com',
                  ),
                ),
                const SizedBox(height: 16),
                DropdownButtonFormField<TargetType>(
                  value: selectedType,
                  decoration: const InputDecoration(
                    labelText: 'Target Type',
                  ),
                  items: TargetType.values.map((type) {
                    return DropdownMenuItem(
                      value: type,
                      child: Text(type.name),
                    );
                  }).toList(),
                  onChanged: (value) {
                    if (value != null) {
                      setState(() {
                        selectedType = value;
                      });
                    }
                  },
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () async {
                final provider = context.read<TargetProvider>();
                await provider.registerTarget(
                  url: urlController.text,
                  type: selectedType,
                );
                if (context.mounted) {
                  Navigator.pop(context);
                }
              },
              child: const Text('Register'),
            ),
          ],
        ),
      ),
    );
  }

  void _deactivateTarget(String targetId) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Deactivate Target'),
        content: const Text('Are you sure you want to deactivate this target?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              final provider = context.read<TargetProvider>();
              await provider.deactivateTarget(targetId);
              if (context.mounted) {
                Navigator.pop(context);
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
            ),
            child: const Text('Deactivate'),
          ),
        ],
      ),
    );
  }

  String _formatDate(DateTime date) {
    return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')} ${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}';
  }
}