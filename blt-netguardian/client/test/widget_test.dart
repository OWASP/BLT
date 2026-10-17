import 'package:flutter_test/flutter_test.dart';
import 'package:netguardian_client/main.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('app shell loads', (WidgetTester tester) async {
    await tester.pumpWidget(const NetGuardianClientApp());
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.text('NETGUARDIAN'), findsOneWidget);
    expect(find.text('CLAIM → SPIDER → INGEST → TRIAGE'), findsOneWidget);
  });
}
