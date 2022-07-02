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
  final bool isOpen;
  final DateTime createdOn;
  Results({
    required this.id,
    required this.description,
    required this.screenshot,
    required this.isOpen,
    required this.createdOn,
  });

  factory Results.fromJson(Map<String, dynamic> parsedJson) {
    return Results(
      id: parsedJson['id'].toString(),
      description: parsedJson['description'],
      screenshot: parsedJson['screenshot'],
      isOpen: (parsedJson["status"] == "open") ? true : false,
      createdOn: DateTime.parse(parsedJson["created"]),
    );
  }
}

class Leaders {
  final String id;
  final int rank;
  final String user;
  final int score;
  final String image;
  final int title;

  Leaders({
    required this.id,
    required this.rank,
    required this.user,
    required this.score,
    required this.image,
    required this.title,
  });

  factory Leaders.fromJson(Map<String, dynamic> parsedJson) {
    return Leaders(
      id: parsedJson['id'].toString(),
      rank: parsedJson['rank'] ?? 0,
      user: parsedJson['User'] ?? "",
      score: parsedJson['score']['total_score'] ?? 0,
      image: parsedJson['image']['user_avatar'] ?? "",
      title: parsedJson['title_type']['title'] ?? 0,
    );
  }
}
