import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../providers/task_provider.dart';
import '../providers/target_provider.dart';
import '../providers/result_provider.dart';
import 'tasks_screen.dart';
import 'targets_screen.dart';
import 'results_screen.dart';
import 'dashboard_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _selectedIndex = 0;

  final List<Widget> _screens = [
    const DashboardScreen(),
    const TasksScreen(),
    const TargetsScreen(),
    const ResultsScreen(),
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _checkInitialization();
    });
  }

  void _checkInitialization() {
    final appProvider = context.read<AppProvider>();
    if (!appProvider.isInitialized) {
      _showConfigurationDialog();
    }
  }

  void _showConfigurationDialog() {
    final TextEditingController urlController = TextEditingController(
      text: 'https://api.netguardian.example.com',
    );

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        title: const Text('Configure API Endpoint'),
        content: TextField(
          controller: urlController,
          decoration: const InputDecoration(
            labelText: 'API Base URL',
            hintText: 'https://api.netguardian.example.com',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () {
              final appProvider = context.read<AppProvider>();
              appProvider.initialize(urlController.text);
              
              // Initialize providers
              final taskProvider = context.read<TaskProvider>();
              final targetProvider = context.read<TargetProvider>();
              final resultProvider = context.read<ResultProvider>();
              
              taskProvider.loadTasks();
              targetProvider.loadTargets();
              resultProvider.loadResults();
              
              Navigator.pop(context);
            },
            child: const Text('Connect'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('BLT NetGuardian Client'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: _showConfigurationDialog,
            tooltip: 'Settings',
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              context.read<TaskProvider>().refresh();
              context.read<TargetProvider>().refresh();
              context.read<ResultProvider>().refresh();
            },
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: _screens[_selectedIndex],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) {
          setState(() {
            _selectedIndex = index;
          });
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.dashboard),
            label: 'Dashboard',
          ),
          NavigationDestination(
            icon: Icon(Icons.task),
            label: 'Tasks',
          ),
          NavigationDestination(
            icon: Icon(Icons.target),
            label: 'Targets',
          ),
          NavigationDestination(
            icon: Icon(Icons.bug_report),
            label: 'Results',
          ),
        ],
      ),
    );
  }
}