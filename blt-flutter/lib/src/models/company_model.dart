import 'dart:ui';

/// Model class for a company/domain on BLT
class Company {
  int? id;
  final String companyName;
  String? email;
  String? url;
  String? hexcolor;
  String? twitter;
  String? facebook;
  int? openIssues;
  int? closedIssues;
  int? issueCount;
  final DateTime lastModified;
  final String logoLink;
  final String topTester;
  bool? isActive;

  Company(
    this.id,
    this.companyName,
    this.email,
    this.url,
    this.hexcolor,
    this.openIssues,
    this.closedIssues,
    this.issueCount,
    this.lastModified,
    this.logoLink,
    this.topTester,
    this.twitter,
    this.facebook,
    this.isActive,
  );

  Color? get valueColor {
    Color? color;
    try {
      String val = "0xFF" + this.hexcolor!.toUpperCase();
      int colorInt = int.parse(val);
      color = Color(colorInt);
    } catch (e) {
      print(e);
    }
    return color;
  }

  factory Company.fromJson(Map<String, dynamic> parsedJson) {
    return Company(
      parsedJson["id"] ?? null,
      parsedJson["name"],
      parsedJson["email"] ?? null,
      parsedJson["url"] ?? null,
      parsedJson["color"] ?? null,
      parsedJson["open"] ?? 0,
      parsedJson["closed"] ?? 0,
      parsedJson["issue_count"] ?? 0,
      DateTime.parse(parsedJson["modified"]),
      parsedJson["logo"].toString(),
      parsedJson["top"] ?? "",
      parsedJson["twitter"],
      parsedJson["facebook"],
      parsedJson["isActive"],
    );
  }

  static List<Company> fromSnapshot(List<dynamic> json) {
    return json.map((data) => Company.fromJson(data)).toList();
  }

  void setMoreInfo(
    int id,
    String mail,
    String link,
    String color,
  ) {
    this.id = id;
    this.email = mail;
    this.url = link;
    this.hexcolor = color.substring(1);
  }
}
