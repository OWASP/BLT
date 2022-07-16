import 'package:bugheist/util/api/issues_api.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../components/issue_intro_card.dart';
import 'package:flutter/material.dart';

import '../../models/issuedata_model.dart';
import '../../util/endpoints/issue_endpoints.dart';

class PaginatedClass extends StatefulWidget {
  const PaginatedClass({Key? key}) : super(key: key);

  @override
  PaginatedClassState createState() => PaginatedClassState();
}

ScrollController _scrollController = new ScrollController();

class PaginatedClassState extends State<PaginatedClass>
    with TickerProviderStateMixin {
  late AnimationController animationController;
  bool _loading = true;
  late Future _getObj;
  late String paginatedUrl;

  static const TextStyle optionStyle =
      TextStyle(fontSize: 30, fontWeight: FontWeight.bold);

  @override
  void initState() {
    paginatedUrl = IssueEndPoints.issues;
    _loading = false;

    animationController =
        AnimationController(duration: new Duration(seconds: 2), vsync: this);
    animationController.repeat();

    _getObj = IssueApiClient.getAllIssues(paginatedUrl);

    _scrollController.addListener(() async {
      if (_scrollController.position.pixels ==
          _scrollController.position.maxScrollExtent) {
        if (!_loading && mounted) {
          setState(() {
            _loading = true;
          });
        }

        _getObj.then((value) async {
          if (value.nextQuery != null) {
            IssueData? paginatedData =
                await IssueApiClient.getAllIssues(value.nextQuery);

            if (mounted) {
              setState(() {
                for (var i = 0; i < paginatedData!.issueList!.length; i++) {
                  value.issueList.add(paginatedData.issueList![i]);
                }
                value.nextQuery = paginatedData.nextQuery;
              });
            }
          } else {}
        });
        await Future.delayed(Duration(seconds: 1));
        if (mounted) {
          setState(() {
            _loading = false;
          });
        }
      }
    });
    super.initState();
  }

  @override
  void dispose() {
    animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final Size size = MediaQuery.of(context).size;

    return Scaffold(
      body: SingleChildScrollView(
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
              child: FutureBuilder(
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
                        itemCount:
                            (snapshot.data! as IssueData).issueList!.length + 1,
                        controller: _scrollController,
                        itemBuilder: (context, index) {
                          if (index ==
                              (snapshot.data! as IssueData).issueList!.length)
                            return Center(
                              child: Opacity(
                                opacity: _loading ? 1.0 : 0.0,
                                child: CircularProgressIndicator(
                                  valueColor: animationController.drive(
                                    ColorTween(
                                      begin: Colors.blueAccent,
                                      end: Colors.red,
                                    ),
                                  ),
                                ),
                              ),
                            );
                          else
                            return IssueCard(
                              issue: (snapshot.data! as IssueData)
                                  .issueList![index],
                            );
                        },
                      );
                    }
                  }
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
    );
  }
}
