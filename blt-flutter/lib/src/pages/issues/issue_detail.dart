import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

import '../../models/issue_model.dart';
import '../../components/issuechip.dart';
import '../../components/issueflag.dart';
import '../../components/issuelike.dart';

/// Popup page when an issue is clicked to be viewed.
class IssueDetailPage extends StatelessWidget {
  static final String path = "lib/src/pages/blog/article1.dart";
  final Issue issue;

  final List<int> validScreenshotIndexes = [];

  IssueDetailPage({
    Key? key,
    required this.issue,
  }) : super(key: key);

  String replaceImageTags(String text) {
    var rx = RegExp(r"\[\$img[0-9]+]");
    var found = rx.allMatches(text);

    while (found.isNotEmpty) {
      var match = found.first.group(0);
      var start = found.first.start;
      var end = found.first.end;
      var number = match!.split("[\$img")[1].split("]")[0];
      var intNumber = int.parse(number);

      if (intNumber >= 1 && intNumber <= issue.screenshotsLink!.length) {
        validScreenshotIndexes.removeWhere((element) => element == intNumber);
        text = text.substring(0, start) +
            "\n\n![$number](${issue.screenshotsLink![intNumber - 1]})\n\n" +
            text.substring(end);
      } else {
        text =
            text.substring(0, start) + "[\$img $number]" + text.substring(end);
      }
      found = rx.allMatches(text);
    }
    return text;
  }

  @override
  Widget build(BuildContext context) {
    validScreenshotIndexes.clear();
    for (var i = 1; i <= issue.screenshotsLink!.length; i++) {
      validScreenshotIndexes.add(i);
    }

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: Icon(
            Icons.arrow_back_ios_new_rounded,
          ),
          onPressed: () {
            Navigator.of(context).pop();
          },
        ),
        title: Text("Issue #${issue.id}"),
        actions: [
          IssueLikeButton(
            issue: issue,
            color: Colors.white,
          ),
          IssueFlagButton(
            issue: issue,
            color: Colors.white,
          ),
        ],
        backgroundColor: Color(0xFFDC4654),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: ListView(
          children: <Widget>[
            Container(
              child: Text(
                "Issue #${issue.id}",
                style: GoogleFonts.ubuntu(
                  textStyle: TextStyle(
                    color: Color(0xFF737373),
                    fontSize: 25,
                  ),
                ),
              ),
            ),
            Container(
              child: Row(
                children: [
                  Text(
                    "Created On ${issue.created_date}",
                    overflow: TextOverflow.ellipsis,
                    softWrap: true,
                    style: GoogleFonts.aBeeZee(
                      textStyle: TextStyle(
                        fontSize: 12,
                        color: Color(0xFFA3A3A3),
                      ),
                    ),
                  ),
                  SizedBox(
                    width: 10,
                  ),
                  IssueStatusChip(issue: issue),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(vertical: 12),
              child: Text(
                "Title",
                overflow: TextOverflow.ellipsis,
                softWrap: true,
                style: GoogleFonts.ubuntu(
                  textStyle: TextStyle(
                    color: Color(0xFFDC4654),
                    fontSize: 17.5,
                  ),
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            Markdown(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              data: replaceImageTags(issue.title),
              padding: EdgeInsets.all(0),
              selectable: true,
              styleSheet: MarkdownStyleSheet.fromTheme(
                ThemeData(
                  fontFamily: GoogleFonts.aBeeZee().fontFamily,
                  textTheme: TextTheme(
                    bodyMedium: GoogleFonts.aBeeZee(
                      textStyle: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w500,
                        color: Color(0xFF737373),
                      ),
                    ),
                  ),
                ),
              ),
            ),
            if (issue.description != "")
              Container(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Text(
                  "Description",
                  overflow: TextOverflow.ellipsis,
                  softWrap: true,
                  style: GoogleFonts.ubuntu(
                    textStyle: TextStyle(
                      color: Color(0xFFDC4654),
                      fontSize: 17.5,
                    ),
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            if (issue.description != "")
              Markdown(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                data: replaceImageTags('${issue.description}'),
                padding: EdgeInsets.all(0),
                selectable: true,
                styleSheet: MarkdownStyleSheet.fromTheme(
                  ThemeData(
                    fontFamily: GoogleFonts.aBeeZee().fontFamily,
                    textTheme: TextTheme(
                      bodyMedium: GoogleFonts.aBeeZee(
                        textStyle: TextStyle(
                          fontSize: 12,
                          color: Color(0xFF737373),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            Container(
              padding: const EdgeInsets.symmetric(vertical: 12),
              child: Text(
                "Screenshots",
                overflow: TextOverflow.ellipsis,
                softWrap: true,
                style: GoogleFonts.ubuntu(
                  textStyle: TextStyle(
                    color: Color(0xFFDC4654),
                    fontSize: 17.5,
                  ),
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            ListView.builder(
              shrinkWrap: true,
              physics: NeverScrollableScrollPhysics(),
              itemCount: validScreenshotIndexes.length,
              itemBuilder: (_, i) {
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8.0),
                  child: Container(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.all(
                        Radius.circular(8),
                      ),
                    ),
                    child: Image.network(
                      issue.screenshotsLink![validScreenshotIndexes[i] - 1],
                    ),
                  ),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}
