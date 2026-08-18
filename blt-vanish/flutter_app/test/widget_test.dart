import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:selferase/main.dart';
import 'package:selferase/services/broker_service.dart';
import 'package:selferase/services/credential_vault_service.dart';
import 'package:selferase/services/storage_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('BLT Vanish app renders dashboard shell', (tester) async {
    SharedPreferences.setMockInitialValues({});

    final storageService = StorageService();
    await storageService.initialize();

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          Provider<StorageService>.value(value: storageService),
          Provider<BrokerService>.value(value: BrokerService()),
          Provider<CredentialVaultService>(
            create: (_) => CredentialVaultService(
              storageService: storageService,
            ),
          ),
        ],
        child: const SelfEraseApp(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('BLT Vanish'), findsOneWidget);
    expect(find.textContaining('data vanish'), findsOneWidget);
  });
}
