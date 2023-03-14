import 'package:blt/src/models/leader_model.dart';

/// Model class for the paginated data sent on requesting issues.
class LeaderData {
  final int count;
  String? nextQuery;
  String? previousQuery;
  List<Leaders>? leaderList;

  LeaderData({
    required this.count,
    this.nextQuery,
    this.previousQuery,
    this.leaderList,
  });

  factory LeaderData.fromJson(Map<String, dynamic> responseData) {
    return LeaderData(
      count: responseData["count"],
      nextQuery: responseData["next"],
      previousQuery: responseData["previous"],
      leaderList: responseData["results"],
    );
  }
}