import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/task.dart';
import '../providers/task_provider.dart';

class TasksScreen extends StatefulWidget {
  const TasksScreen({super.key});

  @override
  State<TasksScreen> createState() => _TasksScreenState();
}

class _TasksScreenState extends State<TasksScreen> {
  TaskStatus? _filterStatus;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<TaskProvider>().loadTasks();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Column(
        children: [
          _buildFilterBar(),
          Expanded(child: _buildTaskList()),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _showAddTaskDialog,
        child: const Icon(Icons.add),
        tooltip: 'Add Task',
      ),
    );
  }

  Widget _buildFilterBar() {
    return Container(
      padding: const EdgeInsets.all(8),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: [
            const Text('Filter: '),
            const SizedBox(width: 8),
            _buildFilterChip('All', null),
            _buildFilterChip('Pending', TaskStatus.pending),
            _buildFilterChip('Queued', TaskStatus.queued),
            _buildFilterChip('Processing', TaskStatus.processing),
            _buildFilterChip('Completed', TaskStatus.completed),
            _buildFilterChip('Failed', TaskStatus.failed),
          ],
        ),
      ),
    );
  }

  Widget _buildFilterChip(String label, TaskStatus? status) {
    final isSelected = _filterStatus == status;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4),
      child: FilterChip(
        label: Text(label),
        selected: isSelected,
        onSelected: (selected) {
          setState(() {
            _filterStatus = selected ? status : null;
          });
          context.read<TaskProvider>().loadTasks(status: _filterStatus);
        },
      ),
    );
  }

  Widget _buildTaskList() {
    return Consumer<TaskProvider>(
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
                  onPressed: () => provider.loadTasks(status: _filterStatus),
                  child: const Text('Retry'),
                ),
              ],
            ),
          );
        }

        final tasks = provider.tasks;
        if (tasks.isEmpty) {
          return const Center(child: Text('No tasks found'));
        }

        return RefreshIndicator(
          onRefresh: () => provider.loadTasks(status: _filterStatus),
          child: ListView.builder(
            itemCount: tasks.length,
            itemBuilder: (context, index) {
              final task = tasks[index];
              return _buildTaskCard(task);
            },
          ),
        );
      },
    );
  }

  Widget _buildTaskCard(Task task) {
    Color statusColor;
    switch (task.status) {
      case TaskStatus.completed:
        statusColor = Colors.green;
        break;
      case TaskStatus.failed:
        statusColor = Colors.red;
        break;
      case TaskStatus.processing:
        statusColor = Colors.purple;
        break;
      case TaskStatus.queued:
        statusColor = Colors.blue;
        break;
      default:
        statusColor = Colors.orange;
    }

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: statusColor.withOpacity(0.2),
          child: Icon(Icons.task, color: statusColor),
        ),
        title: Text('${task.type} - ${task.target}'),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('ID: ${task.id}'),
            Text('Created: ${_formatDate(task.createdAt)}'),
            if (task.completedAt != null)
              Text('Completed: ${_formatDate(task.completedAt!)}'),
          ],
        ),
        trailing: Chip(
          label: Text(
            task.status.name.toUpperCase(),
            style: TextStyle(color: statusColor, fontSize: 10),
          ),
          backgroundColor: statusColor.withOpacity(0.1),
        ),
        isThreeLine: true,
      ),
    );
  }

  void _showAddTaskDialog() {
    final typeController = TextEditingController();
    final targetController = TextEditingController();
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Queue New Task'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: typeController,
                decoration: const InputDecoration(
                  labelText: 'Task Type',
                  hintText: 'web2Crawler, web3Monitor, etc.',
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: targetController,
                decoration: const InputDecoration(
                  labelText: 'Target URL',
                  hintText: 'https://example.com',
                ),
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
              final provider = context.read<TaskProvider>();
              await provider.queueTask(
                type: typeController.text,
                target: targetController.text,
                parameters: {},
              );
              if (context.mounted) {
                Navigator.pop(context);
              }
            },
            child: const Text('Queue'),
          ),
        ],
      ),
    );
  }

  String _formatDate(DateTime date) {
    return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')} ${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}';
  }
}