import 'package:bugheist/src/providers/issuelist_provider.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../components/issue_intro_card.dart';
import 'package:flutter/material.dart';

import '../../models/issue_model.dart';
import '../../util/endpoints/issue_endpoints.dart';

/// Issues page for viewing all the issues posted via the website and app.
class IssuesPage extends ConsumerStatefulWidget {
  const IssuesPage({Key? key}) : super(key: key);

  @override
  IssuesPageState createState() => IssuesPageState();
}

ScrollController _scrollController = new ScrollController();

class IssuesPageState extends ConsumerState<IssuesPage>
    with TickerProviderStateMixin {
  late AnimationController animationController;
  late String paginatedUrl;

  static const TextStyle optionStyle =
      TextStyle(fontSize: 30, fontWeight: FontWeight.bold);

  @override
  void initState() {
    paginatedUrl = IssueEndPoints.issues;

    animationController =
        AnimationController(duration: new Duration(seconds: 2), vsync: this);
    animationController.repeat();

    _scrollController.addListener(() async {
      if (_scrollController.position.pixels ==
          _scrollController.position.maxScrollExtent) {
        loadMoreIssues();
      }
    });
    super.initState();
  }

  @override
  void dispose() {
    animationController.dispose();
    super.dispose();
  }

  void loadMoreIssues() {
    paginatedUrl = ref.watch(issueListProvider.notifier).nxtUrl!;
    ref.watch(issueListProvider.notifier).getMoreIssues(paginatedUrl);
  }

  @override
  Widget build(BuildContext context) {
    final Size size = MediaQuery.of(context).size;
    final issueState = ref.watch(issueListProvider);

    return Scaffold(
      body: RefreshIndicator(
        onRefresh: () async {
          ref.refresh(issueListProvider);
        },
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: EdgeInsets.symmetric(horizontal: 20),
                width: size.width,
                color: Theme.of(context).canvasColor,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: EdgeInsets.fromLTRB(0, 12, 0, 12),
                      child: Text(
                        'Issues',
                        style: GoogleFonts.ubuntu(
                          textStyle: TextStyle(
                            color: Color(0xFF737373),
                            fontSize: 25,
                          ),
                        ),
                      ),
                    ),
                    Container(
                      padding: EdgeInsets.fromLTRB(0, 0, 0, 16),
                      child: Text(
                        "Check out the latest issues found and reported, maybe find a fix too?",
                        style: GoogleFonts.aBeeZee(
                          textStyle: TextStyle(
                            color: Color(0xFF737373),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                height: size.height * 0.8,
                padding: EdgeInsets.symmetric(horizontal: 20),
                child: issueState!.when(
                  data: (List<Issue>? issueList) {
                    if (issueList!.isEmpty) {
                      return Center(
                        child: Text(
                          "Looks like you don't have any todos :) \n Yay!",
                          textAlign: TextAlign.center,
                        ),
                      );
                    } else {
                      return ListView.builder(
                        controller: _scrollController,
                        itemCount: issueList.length,
                        itemBuilder: (context, index) {
                          return IssueCard(
                            issue: issueList[index],
                          );
                        },
                      );
                    }
                  },
                  error: (Object error, StackTrace? stackTrace) {
                    return Center(
                      child: Text(
                        'Something went wrong!',
                        style: TextStyle(fontSize: 18),
                      ),
                    );
                  },
                  loading: () {
                    return Center(
                      child: CircularProgressIndicator(
                        valueColor: animationController.drive(
                          ColorTween(
                            begin: Colors.blueAccent,
                            end: Colors.red,
                          ),
                        ),
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
