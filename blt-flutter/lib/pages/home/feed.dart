import 'package:bugheist/global/variables.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
// import '../../providers/issuelist_provider.dart';

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
              'Goood Afternoon, \n${currentUser!.username}',
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
            "Check the latest happenings in the world of BugHeist!",
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
            "Latest Issues",
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
            "Bug Socials!",
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
            "Our Sponsors",
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
