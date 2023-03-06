import 'general_endpoints.dart';

class LeaderboardEndpoints {
  LeaderboardEndpoints._();

  static const String globalLeaderboard = GeneralEndPoints.apiBaseUrl + "userscore/";

  static const String companyScoreboard = GeneralEndPoints.apiBaseUrl + "scoreboard/";
}
