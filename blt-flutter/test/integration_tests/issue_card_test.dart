import '../test_imports.dart';

void main() {
  testWidgets("Issue Card Test", (WidgetTester tester) async {
    final mockIssue = Issue(
      id: 1,
      url: 'http://bugheist.com',
      title: 'Issue 1',
      description: '',
      label: 0,
      userAgent: 'Mozilla/5.0 (X11; Linux x86_64',
      created: DateTime.now(),
      domain: 3,
      isOpen: true,
      screenshotsLink: [],
      likes: 0,
      isVerified: false,
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            height: 1900,
            width: 600,
            child: Padding(
              padding: const EdgeInsets.all(18.0).copyWith(bottom: 0),
              child: IssueCard(
                issue: mockIssue,
                isTesting: true,
              ),
            ),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.byType(Card), findsOneWidget);
    expect(find.byType(Image), findsOneWidget);
    // cant integrate this to the test because additional apis are being called using http here.
    // expect(find.byType(IssueLikeButton), findsOneWidget);
  });
}
