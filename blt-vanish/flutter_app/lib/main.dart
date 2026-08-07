import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'screens/home_screen.dart';
import 'services/broker_service.dart';
import 'services/credential_vault_service.dart';
import 'services/storage_service.dart';
import 'theme/blt_theme.dart';

/// App entry point that initializes local-first services before rendering.
void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize services
  final storageService = StorageService();
  await storageService.initialize();
  
  final brokerService = BrokerService();
  
  runApp(
    MultiProvider(
      providers: [
        Provider<StorageService>.value(value: storageService),
        Provider<BrokerService>.value(value: brokerService),
        Provider<CredentialVaultService>(
          create: (_) => CredentialVaultService(storageService: storageService),
        ),
      ],
      child: const SelfEraseApp(),
    ),
  );
}

/// Root application shell for SelfErase.
class SelfEraseApp extends StatelessWidget {
  /// Creates the SelfErase app shell.
  const SelfEraseApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'BLT Vanish',
      debugShowCheckedModeBanner: false,
      theme: BltTheme.light(),
      home: const HomeScreen(),
    );
  }
}
