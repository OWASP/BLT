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

  const IssueDetailPage({
    Key? key,
    required this.issue,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final Size size = MediaQuery.of(context).size;

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
      body: SingleChildScrollView(
        padding: EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Container(
              width: size.width,
              color: Theme.of(context).canvasColor,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
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
                ],
              ),
            ),
            Container(
              width: size.width,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(10),
              ),
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Image.network(
                issue.screenshotsLink![0],
                fit: BoxFit.fill,
              ),
            ),
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
            Container(
              height: 50,
              child: Markdown(
                        physics: const NeverScrollableScrollPhysics(),
                        data: issue.description,
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
                        )
                      )
            ),
          ],
        ),
      ),
    );
  }
}
