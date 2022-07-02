class Company {
  final String companyName;
  final int openIssues;
  final int closedIssues;
  final DateTime lastModified;
  final String logoLink;
  final String topTester;

  Company(
    this.companyName,
    this.openIssues,
    this.closedIssues,
    this.lastModified,
    this.logoLink,
    this.topTester,
  );

  factory Company.fromJson(Map<String, dynamic> parsedJson) {
    return Company(
      parsedJson["name"],
      parsedJson["open"],
      parsedJson["closed"],
      DateTime.parse(parsedJson["modified"]),
      parsedJson["logo"].toString(),
      parsedJson["top"],
    );
  }
}
