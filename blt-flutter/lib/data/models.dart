class DataModel {
  final String count;
  String next;
  final String previous;
  final List<Results> results;

  DataModel(
      {required this.count,
      required this.next,
      required this.previous,
      required this.results});

  factory DataModel.fromJson(Map<String, dynamic> parsedJson) {
    return DataModel(
        count: parsedJson['count'].toString(),
        next: parsedJson['next'].toString(),
        previous: parsedJson['previous'].toString(),
        results: parseResults(parsedJson));
  }
  static List<Results> parseResults(parsedJson) {
    var list = parsedJson['results'] as List;
    List<Results> resultsList =
        list.map((data) => Results.fromJson(data)).toList();
    return resultsList;
  }
}

class Results {
  final String id;
  final String description;
  final String screenshot;
  Results(
      {required this.id, required this.description, required this.screenshot});

  factory Results.fromJson(Map<String, dynamic> parsedJson) {
    return Results(
        id: parsedJson['id'].toString(),
        description: parsedJson['description'],
        screenshot: parsedJson['screenshot']);
  }
}
