import 'package:flutter/material.dart';
import 'package:blt/src/components/components_import.dart';

/// The card used to display issues in the list of issues on the Issue Page.
class IssueCard extends StatelessWidget {
  final Issue issue;

  const IssueCard({Key? key, required this.issue}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final Size size = MediaQuery.of(context).size;
    return Card(
      margin: EdgeInsets.all(10),
      elevation: 0,
      clipBehavior: Clip.antiAlias,
      color: Color(0xFF737373).withOpacity(0.15),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
      ),
      child: InkWell(
        onTap: () {
          Navigator.pushNamed(
            context,
            RouteManager.issueDetailPage,
            arguments: issue,
          );
        },
        child: Container(
          height: 0.334 * size.height,
          child: Column(
            children: <Widget>[
              Container(
                width: size.width,
                height: 0.214 * size.height,
                child: AspectRatio(
                  aspectRatio: size.width / 0.214 * size.height,
                  child: (issue.screenshotsLink!.isNotEmpty)
                      ? CachedNetworkImage(
                          imageUrl: issue.screenshotsLink![0],
                          fit: BoxFit.cover,
                        )
                      : Image.asset(
                          "assets/image-not-found.png",
                          fit: BoxFit.cover,
                        ),
                ),
              ),
              Container(
                width: size.width,
                height: 0.12 * size.height,
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 12,
                ),
                child: ListTile(
                  // contentPadding: EdgeInsets.zero,
                  isThreeLine: true,
                  title: Text(
                    "Issue #${issue.id}",
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
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.only(top: 8, bottom: 12),
                        child: Text(
                          issue.title.replaceAll("\n", " "),
                          overflow: TextOverflow.ellipsis,
                          softWrap: true,
                          style: GoogleFonts.aBeeZee(
                            textStyle: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                              color: Color(0xFF737373),
                            ),
                          ),
                        ),
                      ),
                      Text(
                        issue.created_date,
                        overflow: TextOverflow.ellipsis,
                        softWrap: true,
                        style: GoogleFonts.aBeeZee(
                          textStyle: TextStyle(
                            fontSize: 10,
                            color: Color(0xFFA3A3A3),
                          ),
                        ),
                      ),
                    ],
                  ),
                  trailing: IssueLikeButton(
                    issue: issue,
                  ),
                ),
                // child: Column(
                //   crossAxisAlignment: CrossAxisAlignment.start,
                //   children: <Widget>[
                //     Container(
                //       padding: const EdgeInsets.only(top: 12),
                //       child: Text(
                //         "Issue #${issue.id}",
                //         overflow: TextOverflow.ellipsis,
                //         softWrap: true,
                //         style: GoogleFonts.ubuntu(
                //           textStyle: TextStyle(
                //             color: Color(0xFFDC4654),
                //             fontSize: 17.5,
                //           ),
                //           fontWeight: FontWeight.bold,
                //         ),
                //       ),
                //     ),
                //     Container(
                //       padding: const EdgeInsets.only(top: 8, bottom: 12),
                //       child: Text(
                //         issue.description.replaceAll("\n", " "),
                //         overflow: TextOverflow.ellipsis,
                //         softWrap: true,
                //         style: GoogleFonts.aBeeZee(
                //           textStyle: TextStyle(
                //             fontSize: 12,
                //             color: Color(0xFF737373),
                //           ),
                //         ),
                //       ),
                //     ),
                //     Row(
                //       children: [
                //         Container(
                //           padding: const EdgeInsets.only(bottom: 12),
                //           child: Text(
                //             issue.created_date,
                //             overflow: TextOverflow.ellipsis,
                //             softWrap: true,
                //             style: GoogleFonts.aBeeZee(
                //               textStyle: TextStyle(
                //                 fontSize: 10,
                //                 color: Color(0xFFA3A3A3),
                //               ),
                //             ),
                //           ),
                //         ),
                //       ],
                //     ),
                //   ],
                // ),
              )
            ],
          ),
        ),
      ),
    );
  }
}
