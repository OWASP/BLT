import '../test_imports.dart';

void main() {
  testWidgets("Issue List Test", (WidgetTester tester) async {
    final mockIssueList = [
      Issue(
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
        isVerified: false,
      ),
      Issue(
        id: 2,
        url: 'http://test.com',
        title: 'Issue 2',
        created: DateTime.now(),
        description: '## Hello there',
        userAgent: 'Mozilla/5.0 (X11; Linux x86_64',
        domain: 1,
        screenshotsLink: [],
        isVerified: true,
        isOpen: false,
      ),
    ];

    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: ShowIssueList(isTesting: true, issueList: mockIssueList),
      ),
    ));

    await tester.pumpAndSettle();

    expect(find.byType(ListView), findsOneWidget);
    expect(find.byType(ListTile), findsNWidgets(mockIssueList.length));

    for (var issue in mockIssueList) {
      expect(find.text(issue.title), findsOneWidget);
    }
  });
}
