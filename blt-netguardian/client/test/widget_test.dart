import 'package:flutter_test/flutter_test.dart';
import 'package:netguardian_client/main.dart';

void main() {
  testWidgets('app shell loads', (WidgetTester tester) async {
    await tester.pumpWidget(const NetGuardianClientApp());
    await tester.pump();
    expect(find.text('NETGUARDIAN'), findsOneWidget);
  });
}
