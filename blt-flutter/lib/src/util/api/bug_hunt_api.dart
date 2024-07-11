import 'package:blt/src/models/bug_hunt_model.dart';
import 'package:blt/src/util/util_import.dart';
import 'package:http/http.dart' as http;

class BugHuntApiClient {
  BugHuntApiClient._();

  static Future<List<BugHunt>> getListOfActiveBugHunts(
      {http.Client? client}) async {
    String searchUrl = GeneralEndPoints.apiBaseUrl + "/hunt/?activeHunt=true";
    List<BugHunt> bugHuntList = [];
    try {
      var response = (client != null)
          ? await client.get(Uri.parse(searchUrl))
          : await http.get(Uri.parse(searchUrl));
      var decodedResponse = jsonDecode(utf8.decode(response.bodyBytes));
      bugHuntList = BugHunt.fromSnapshot(decodedResponse);
      List<BugHunt> upcomingHunts =
          await getListOfUpcomingBugHunts(client: client);
      bugHuntList.addAll(upcomingHunts);
    } catch (e) {
      print(e);
    }
    return bugHuntList;
  }

  static Future<List<BugHunt>> getListOfUpcomingBugHunts(
      {http.Client? client}) async {
    String searchUrl = GeneralEndPoints.apiBaseUrl + "/hunt/?upcomingHunt=true";
    List<BugHunt> bugHuntList = [];
    try {
      var response = (client != null)
          ? await client.get(Uri.parse(searchUrl))
          : await http.get(Uri.parse(searchUrl));
      var decodedResponse = jsonDecode(utf8.decode(response.bodyBytes));
      bugHuntList = BugHunt.fromSnapshot(decodedResponse);
    } catch (e) {
      print(e);
    }
    return bugHuntList;
  }

  static Future<List<BugHunt>> getListOfPreviousBugHunts(
      {http.Client? client}) async {
    String searchUrl = GeneralEndPoints.apiBaseUrl + "/hunt/?previousHunt=true";
    List<BugHunt> bugHuntList = [];
    try {
      var response = (client != null)
          ? await client.get(Uri.parse(searchUrl))
          : await http.get(Uri.parse(searchUrl));
      var decodedResponse = jsonDecode(utf8.decode(response.bodyBytes));
      bugHuntList = BugHunt.fromSnapshot(decodedResponse);
    } catch (e) {
      print(e);
    }
    return bugHuntList;
  }

  static Future<List<BugHunt>> searchBugHunts(
      {http.Client? client, String? search}) async {
    // String searchUrl = GeneralEndPoints.apiBaseUrl + "/hunt";
    String searchUrl =
        "http://192.168.56.1:8000/api/v1" + "/hunt/?search=$search";
    List<BugHunt> bugHuntList = [];
    try {
      var response = (client != null)
          ? await client.get(Uri.parse(searchUrl))
          : await http.get(Uri.parse(searchUrl));
      var decodedResponse = jsonDecode(utf8.decode(response.bodyBytes));
      bugHuntList = BugHunt.fromSnapshot(decodedResponse);
    } catch (e) {
      print(e);
    }
    return bugHuntList;
  }
}
