import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../util/api/issues_api.dart';
import '../models/issuedata_model.dart';
import '../components/issue_intro_card.dart';

/// The search bar of app for searching issues based on keyword.
class BLTSearchDelegate extends SearchDelegate {
  @override
  List<Widget>? buildActions(BuildContext context) {
    return [
      IconButton(
        onPressed: () {
          query != '' ? (query = '') : Navigator.of(context).pop();
        },
        icon: Icon(
          Icons.clear,
          color: Color(0xFFDC4654),
        ),
      ),
    ];
  }

  @override
  Widget? buildLeading(BuildContext context) {
    return IconButton(
      icon: Icon(
        Icons.arrow_back_ios_new_rounded,
        color: Color(0xFFDC4654),
      ),
      onPressed: () {
        Navigator.of(context).pop();
      },
    );
  }

  @override
  Widget buildResults(BuildContext context) {
    Future _getObj = IssueApiClient.searchIssueByKeyWord(query);

    ScrollController _scrollController = new ScrollController();

    return FutureBuilder(
      future: _getObj,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.done) {
          if (snapshot.hasError) {
            return Center(
              child: Text(
                'Something went wrong!',
                style: TextStyle(fontSize: 18),
              ),
            );
          } else if (snapshot.hasData) {
            return ListView.builder(
              padding: EdgeInsets.symmetric(horizontal: 20),
              itemCount: (snapshot.data! as IssueData).issueList!.length,
              controller: _scrollController,
              itemBuilder: (context, index) {
                return IssueCard(
                  issue: (snapshot.data! as IssueData).issueList![index],
                );
              },
            );
          }
        }
        return Center(
          child: CircularProgressIndicator(),
        );
      },
    );
  }

  @override
  Widget buildSuggestions(BuildContext context) {
    final Size size = MediaQuery.of(context).size;
    return Container(
      width: size.width,
      height: size.height,
      child: Center(
        child: Text(
          'Search an issue!',
          style: GoogleFonts.ubuntu(
            textStyle: TextStyle(
              color: Color(0xFF737373),
              fontSize: 20,
            ),
          ),
        ),
      ),
    );
  }
}
