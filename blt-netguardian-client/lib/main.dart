import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'providers/app_provider.dart';
import 'providers/task_provider.dart';
import 'providers/target_provider.dart';
import 'providers/result_provider.dart';
import 'screens/home_screen.dart';

void main() {
  runApp(const NetGuardianApp());
}

class NetGuardianApp extends StatelessWidget {
  const NetGuardianApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AppProvider()),
        ChangeNotifierProxyProvider<AppProvider, TaskProvider>(
          create: (context) => TaskProvider(
            taskManager: context.read<AppProvider>().taskManager,
          ),
          update: (context, appProvider, previous) =>
              previous ?? TaskProvider(taskManager: appProvider.taskManager),
        ),
        ChangeNotifierProxyProvider<AppProvider, TargetProvider>(
          create: (context) => TargetProvider(
            targetManager: context.read<AppProvider>().targetManager,
          ),
          update: (context, appProvider, previous) =>
              previous ?? TargetProvider(targetManager: appProvider.targetManager),
        ),
        ChangeNotifierProxyProvider<AppProvider, ResultProvider>(
          create: (context) => ResultProvider(
            resultManager: context.read<AppProvider>().resultManager,
          ),
          update: (context, appProvider, previous) =>
              previous ?? ResultProvider(resultManager: appProvider.resultManager),
        ),
      ],
      child: MaterialApp(
        title: 'BLT NetGuardian Client',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: Colors.blue,
            brightness: Brightness.light,
          ),
          useMaterial3: true,
        ),
        darkTheme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: Colors.blue,
            brightness: Brightness.dark,
          ),
          useMaterial3: true,
        ),
        themeMode: ThemeMode.system,
        home: const HomeScreen(),
      ),
    );
  }
}