import 'package:blt/src/util/util_import.dart';
import 'package:http/http.dart' as http;

/// Class for accessing the issue client.
class IssueApiClient {
  IssueApiClient._();

  /// Get all the issues relating to the [paginatedUrl].
  static Future<IssueData?> getAllIssues(
      http.Client client, String paginatedUrl) async {
    http.Response? response;
    IssueData? issueData;
    List<Issue>? issueList;
    Map<String, String>? headers = (currentUser != guestUser)
        ? {
            "Authorization": "Token ${currentUser!.token!}",
          }
        : null;
    try {
      response = await client.get(
        Uri.parse(paginatedUrl),
        headers: headers,
      );
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
      print(e); //show error to user
    }
    return issueData;
  }

  /// Get an issue by its [id].
  static Future<Issue?> getIssueById(int id) async {
    http.Response? response;
    Issue? issue;
    try {
      // response = await http.get(Uri.parse(IssueEndPoints.issues + "$id/"));
      // if (response.statusCode == 200) {
      //   var decodedResponse = jsonDecode(utf8.decode(response.bodyBytes));
      //   issue = Issue.fromJson(decodedResponse);
      // }
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
      // String searchUrl = IssueEndPoints.issues + "?search=$query";
      // response = await http.get(Uri.parse(searchUrl));
      // if (response.statusCode == 200) {
      //   issueList = [];
      //   var decodedResponse = jsonDecode(utf8.decode(response.bodyBytes));
      //   decodedResponse["results"].forEach((element) {
      //     issueList!.add(Issue.fromJson(element));
      //   });
      //   issueData = IssueData(
      //     count: decodedResponse["count"],
      //     nextQuery: decodedResponse["next"],
      //     previousQuery: decodedResponse["previous"],
      //     issueList: issueList,
      //   );
      // }
    } catch (e) {
      print(e);
    }
    return issueData;
  }

  /// Send a new bug report to the BLT API (POST /bugs).
  /// [parentContext] is needed to show the snackbars.
  ///
  /// The API takes url and description (plus optional fields such as label
  /// and user_agent) as JSON. It has no screenshot upload yet, so screenshots
  /// stay on the device and the user is told so.
  static Future<void> postIssue(Issue issue, BuildContext parentContext) async {
    final ScaffoldMessengerState messenger = ScaffoldMessenger.of(parentContext);
    try {
      Map<String, dynamic> body = {
        "url": issue.url.trim(),
        "description": (issue.description ?? "").trim(),
      };
      if (issue.label != null) body["label"] = issue.label;
      if (issue.userAgent != null) body["user_agent"] = issue.userAgent;

      http.Response response = await http.post(
        Uri.parse(GeneralEndPoints.bugs),
        headers: GeneralEndPoints.bltApiHeaders,
        body: jsonEncode(body),
      );

      messenger.clearSnackBars();
      if (response.statusCode == 201 || response.statusCode == 200) {
        bool hadScreenshots = (issue.screenshotsLink ?? []).isNotEmpty;
        messenger.showSnackBar(
          SnackBar(
            duration: const Duration(seconds: 6),
            content: Text(
              "Thanks for reporting the issue!" +
                  (hadScreenshots
                      ? " Screenshots can't be uploaded yet, so they were not sent."
                      : ""),
            ),
          ),
        );
      } else {
        String reason = "error ${response.statusCode}";
        try {
          var decoded = jsonDecode(utf8.decode(response.bodyBytes));
          if (decoded is Map && decoded["message"] != null) {
            reason = decoded["message"].toString();
          }
        } catch (_) {}
        messenger.showSnackBar(
          SnackBar(
            content: Text("The bug report could not be sent: " + reason),
          ),
        );
      }
    } catch (e) {
      messenger.clearSnackBars();
      messenger.showSnackBar(
        SnackBar(
          content:
              Text("There was some error, please try again! " + e.toString()),
        ),
      );
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

  static Future<bool> toggleIssueLikes(int id) async {
    http.Response? response;
    bool toggleSuccess = false;
    try {
      response = await http.post(
        Uri.parse(IssueEndPoints.likeIssues + "$id/"),
        headers: {
          "Authorization": "Token ${currentUser!.token!}",
        },
      );
      print(response.statusCode);
      if (response.statusCode == 200) {
        toggleSuccess = true;
      }
    } catch (e) {
      print(e);
    }
    return toggleSuccess;
  }

  static Future<int?> getIssueFlag(int id) async {
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

  static Future<bool> toggleIssueFlag(int id) async {
    http.Response? response;
    bool toggleSuccess = false;
    try {
      response = await http.post(
        Uri.parse(IssueEndPoints.flagIssues + "$id/"),
        headers: {
          "Authorization": "Token ${currentUser!.token!}",
        },
      );
      print(response.statusCode);
      if (response.statusCode == 200) {
        toggleSuccess = true;
      }
    } catch (e) {
      print(e);
    }
    return toggleSuccess;
  }

  static Future getAllUserIssues() async {}

  static Future getUserIssueById() async {}

  static Future searchUserIssueByKeyWord() async {}

  /// Bugs with [status] from the BLT API. With a [url], bugs whose URL or
  /// description matches it (GET /bugs/search); otherwise the newest bugs
  /// (GET /bugs?status=...). The API pages differently from the old one, so
  /// only the first page is returned.
  static Future<IssueData?> getIssueByStatus(String status, String url) async {
    http.Response? response;
    IssueData? issueData;
    try {
      Uri uri = url.trim().isEmpty
          ? Uri.parse(GeneralEndPoints.bugs).replace(
              queryParameters: {"status": status, "per_page": "50"},
            )
          : Uri.parse(GeneralEndPoints.bugSearch).replace(
              queryParameters: {"q": url.trim(), "limit": "50"},
            );
      response = await http.get(uri, headers: GeneralEndPoints.bltApiHeaders);
      if (response.statusCode == 200) {
        var decodedResponse = jsonDecode(utf8.decode(response.bodyBytes));
        List<Issue> issueList = [];
        for (var element in (decodedResponse["data"] ?? [])) {
          if (element is Map<String, dynamic> &&
              (element["status"] ?? "open") == status) {
            issueList.add(Issue.fromBltApi(element));
          }
        }
        issueData = IssueData(
          count: issueList.length,
          nextQuery: null,
          previousQuery: null,
          issueList: issueList,
        );
      }
    } catch (e) {
      print(e);
    }
    return issueData;
  }
}
