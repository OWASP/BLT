import '../test_imports.dart';

void main() {
  testWidgets("Company List Test", (WidgetTester tester) async {
    final mockcompanyList = [
      Company(
        1,
        "Company 1",
        "fhkldjshfklhasfk",
        "company@1234.com",
        "company1.com",
        "black",
        2,
        1,
        3,
        DateTime.now(),
        "kshdfkasl",
        "tester",
        "",
        "",
        true,
      ),
      Company(
        2,
        "Company 2",
        "sakldfklhasfk",
        "test@1234.com",
        "tses.com",
        "blue",
        1,
        5,
        6,
        DateTime.now(),
        "fdsdfsd",
        "test",
        "",
        "",
        true,
      )
    ];

    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: ShowCompanyList(
          isTest: true,
          companyList: mockcompanyList,
        ),
      ),
    ));
    await tester.pumpAndSettle();

    expect(find.byType(ListView), findsOneWidget);
    expect(find.byType(ListTile), findsNWidgets(mockcompanyList.length));

    for (var company in mockcompanyList) {
      expect(find.text(company.companyName), findsOneWidget);
    }
  });
}
