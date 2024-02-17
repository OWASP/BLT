import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';

import '../../global/variables.dart';

/// Page for showing social activity of BLT, new issues,
/// top premium subscribers.
class Feed extends ConsumerStatefulWidget {
  const Feed({Key? key}) : super(key: key);

  @override
  _FeedState createState() => _FeedState();
}

class _FeedState extends ConsumerState<Feed> {
  @override
  Widget build(BuildContext context) {
    // final Size size = MediaQuery.of(context).size;
    // final issueState = ref.watch(issueListProvider);

    return Scaffold(
        body: SingleChildScrollView(
      padding: EdgeInsets.symmetric(horizontal: 20, vertical: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          FittedBox(
            child: Text(
              '${AppLocalizations.of(context)!.goodAfternoon}, \n${currentUser!.username}',
              style: GoogleFonts.ubuntu(
                textStyle: TextStyle(
                  color: Color(0xFFDC4654),
                  fontSize: 30,
                ),
              ),
            ),
          ),
          SizedBox(
            height: 10,
          ),
          Text(
            AppLocalizations.of(context)!.checkLatestHappenings,
            style: GoogleFonts.aBeeZee(
              textStyle: TextStyle(
                color: Color(0xFF737373),
              ),
            ),
          ),
          SizedBox(
            height: 10,
          ),
          Text(
            AppLocalizations.of(context)!.latestIssues,
            style: GoogleFonts.ubuntu(
              textStyle: TextStyle(
                color: Color(0xFFDC4654),
                fontSize: 20,
              ),
              fontWeight: FontWeight.bold,
            ),
          ),
          SizedBox(
            height: 10,
          ),
          // Container(
          //   height: 0.4 * size.height,
          //   child: issueState!.when(
          //     data: (List<Issue>? issueList) {
          //       if (issueList!.isEmpty) {
          //         return Center(
          //           child: Text(
          //             "Looks like you don't have any todos :) \n Yay!",
          //             textAlign: TextAlign.center,
          //           ),
          //         );
          //       } else {
          //         return ListView.builder(
          //           scrollDirection: Axis.horizontal,
          //           itemCount: issueList.length,
          //           itemBuilder: (context, index) {
          //             return IssueCard(
          //               issue: issueList[index],
          //             );
          //           },
          //         );
          //       }
          //     },
          //     error: (Object error, StackTrace? stackTrace) {
          //       return Center(
          //         child: Text(
          //           'Something went wrong!',
          //           style: TextStyle(fontSize: 18),
          //         ),
          //       );
          //     },
          //     loading: () {
          //       return Center(
          //         child: CircularProgressIndicator(),
          //       );
          //     },
          //   ),
          // ),
          Text(
            AppLocalizations.of(context)!.bugSocials,
            style: GoogleFonts.ubuntu(
              textStyle: TextStyle(
                color: Color(0xFFDC4654),
                fontSize: 20,
              ),
              fontWeight: FontWeight.bold,
            ),
          ),
          SizedBox(
            height: 10,
          ),
          Text(
            AppLocalizations.of(context)!.ourSponsors,
            style: GoogleFonts.ubuntu(
              textStyle: TextStyle(
                color: Color(0xFFDC4654),
                fontSize: 20,
              ),
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    ));
  }
}
