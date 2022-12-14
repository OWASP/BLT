import 'dart:convert';
import 'package:bugheist/src/global/variables.dart';
import 'package:bugheist/src/routes/routing.dart';
import 'package:bugheist/src/util/endpoints/issue_endpoints.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../../models/issuedata_model.dart';
import '../../models/issue_model.dart';

/// Class for accessing the issue client.
class IssueApiClient {
  IssueApiClient._();

  /// Get all the issues relating to the [paginatedUrl].
  static Future<IssueData?> getAllIssues(String paginatedUrl) async {
    http.Response? response;
    IssueData? issueData;
    List<Issue>? issueList;
    try {
      response = await http.get(Uri.parse(paginatedUrl));
      if (response.statusCode == 200) {
        issueList = [];
        var decodedResponse = jsonDecode(utf8.decode(response.bodyBytes));
        decodedResponse["results"].forEach((element) {
          issueList!.add(Issue.fromJson(element));
        });
        issueData = IssueData(
          count: decodedResponse["count"],
          nextQuery: decodedResponse["next"],
          previousQuery: decodedResponse["previous"],
          issueList: issueList,
        );
      }
    } catch (e) {
      print(e);
    }
    return issueData;
  }

  /// Get an issue by its [id].
  static Future<Issue?> getIssueById(int id) async {
    http.Response? response;
    Issue? issue;
    try {
      response = await http.get(Uri.parse(IssueEndPoints.issues + "$id/"));
      if (response.statusCode == 200) {
        var decodedResponse = jsonDecode(utf8.decode(response.bodyBytes));
        issue = Issue.fromJson(decodedResponse);
      }
    } catch (e) {
      print(e);
    }
    return issue;
  }

  /// Get issues with matching keyword.
  static Future<IssueData?> searchIssueByKeyWord(query) async {
    http.Response? response;
    IssueData? issueData;
    List<Issue>? issueList;
    try {
      String searchUrl = IssueEndPoints.issues + "?search=$query";
      response = await http.get(Uri.parse(searchUrl));
      if (response.statusCode == 200) {
        issueList = [];
        var decodedResponse = jsonDecode(utf8.decode(response.bodyBytes));
        decodedResponse["results"].forEach((element) {
          issueList!.add(Issue.fromJson(element));
        });
        issueData = IssueData(
          count: decodedResponse["count"],
          nextQuery: decodedResponse["next"],
          previousQuery: decodedResponse["previous"],
          issueList: issueList,
        );
      }
    } catch (e) {
      print(e);
    }
    return issueData;
  }

  /// Create a new issue, [parentContext] is needed to show the snackbars.
  static Future<void> postIssue(Issue issue, BuildContext parentContext) async {
    http.Response? response;
    try {
      var request = http.MultipartRequest(
        "POST",
        Uri.parse(IssueEndPoints.issues),
      );
      request.files.add(
        await http.MultipartFile.fromPath(
          "screenshot",
          issue.ocr,
        ),
      );
      var issueMap = issue.toJson();
      request.headers.addAll({
        "Content-Type": "multipart/form-data",
        "user_agent": issue.userAgent!
      });
      issue.toJson().forEach((key, value) {
        request.fields[key] = jsonEncode(value);
      });

      request.fields["url"] = issueMap["url"];
      request.fields["status"] = issueMap["status"];
      request.fields["description"] = issueMap["description"];

      var streamedresponse = await request.send();

      print(streamedresponse);
      response = await http.Response.fromStream(streamedresponse);

      print(response.body);

      if (streamedresponse.statusCode == 201) {
        var decodedResponse = jsonDecode(utf8.decode(response.bodyBytes));
        issue = Issue.fromJson(decodedResponse);

        SnackBar thankSnack = SnackBar(
          content: Text("Thanks for reporting the issue!"),
        );
        ScaffoldMessenger.of(parentContext).showSnackBar(thankSnack);

        Navigator.of(parentContext).pushNamed(
          RouteManager.issueDetailPage,
          arguments: issue,
        );
      } else {
        ScaffoldMessenger.of(parentContext).clearSnackBars();
        SnackBar errorSnack = SnackBar(
          content:
              Text("There was some error, please try again!" + response.body),
        );
        ScaffoldMessenger.of(parentContext).showSnackBar(errorSnack);
      }
    } catch (e) {
      ScaffoldMessenger.of(parentContext).clearSnackBars();
      SnackBar errorSnack = SnackBar(
        content: Text("There was some error, please try again!" + e.toString()),
      );
      ScaffoldMessenger.of(parentContext).showSnackBar(errorSnack);

      print(e);
    }
  }

  static Future<int?> getIssueLikes(int id) async {
    http.Response? response;
    int? likeCount;
    try {
      response = await http.get(
        Uri.parse(IssueEndPoints.likeIssues + "$id/"),
        headers: {
          "Authorization": "Token ${currentUser!.token!}",
        },
      );
      if (response.statusCode == 200) {
        var decodedResponse = jsonDecode(utf8.decode(response.bodyBytes));
        likeCount = decodedResponse["likes"];
      }
    } catch (e) {
      print(e);
    }
    return likeCount;
  }

  static Future<bool?> toggleIssueLikes(int id) async {
    http.Response? response;
    bool? liked;
    try {
      response = await http.post(
        Uri.parse(IssueEndPoints.likeIssues + "$id/"),
        headers: {
          "Authorization": "Token ${currentUser!.token!}",
        },
      );
      if (response.statusCode == 200) {
        var decodedResponse = jsonDecode(utf8.decode(response.bodyBytes));
        if (decodedResponse["issue"] == "liked") {
          liked = true;
        } else if (decodedResponse["issue"] == "unliked") {
          liked = false;
        }
      }
    } catch (e) {
      print(e);
    }
    return liked;
  }

  static Future getIssueFlag(int id) async {
    http.Response? response;
    int? flagCount;
    try {
      response = await http.get(
        Uri.parse(IssueEndPoints.flagIssues + "$id/"),
        headers: {
          "Authorization": "Token ${currentUser!.token!}",
        },
      );
      if (response.statusCode == 200) {
        var decodedResponse = jsonDecode(utf8.decode(response.bodyBytes));
        flagCount = decodedResponse["flags"];
      }
    } catch (e) {
      print("e");
    }
    return flagCount;
  }

  static Future toggleIssueFlag(int id) async {
    http.Response? response;
    bool? flagged;
    try {
      response = await http.post(
        Uri.parse(IssueEndPoints.flagIssues + "$id/"),
        headers: {
          "Authorization": "Token ${currentUser!.token!}",
        },
      );
      if (response.statusCode == 200) {
        var decodedResponse = jsonDecode(utf8.decode(response.bodyBytes));
        if (decodedResponse["issue"] == "liked") {
          flagged = true;
        } else if (decodedResponse["issue"] == "unliked") {
          flagged = false;
        }
      }
    } catch (e) {
      print(e);
    }
    return flagged;
  }

  static Future getAllUserIssues() async {}

  static Future getUserIssueById() async {}

  static Future searchUserIssueByKeyWord() async {}
}
