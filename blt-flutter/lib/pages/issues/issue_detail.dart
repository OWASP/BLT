import 'package:bugheist/components/issuechip.dart';
import 'package:bugheist/models/issue_model.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

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
        backgroundColor: Color(0xFFDC4654),
      ),
      body: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Container(
              padding: EdgeInsets.symmetric(horizontal: 20),
              width: size.width,
              color: Theme.of(context).canvasColor,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: EdgeInsets.fromLTRB(0, 12, 0, 0),
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
              height: 0.334 * size.height,
              width: size.width,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(10),
              ),
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: InteractiveViewer(
                constrained: false,
                minScale: 0.05,
                child: Image.network(
                  issue.screenshotLink!,
                  fit: BoxFit.fill,
                ),
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
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
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Text(
                issue.description,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
