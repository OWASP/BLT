import 'package:blt/src/pages/leaderboards/leaderboards_imports.dart';
import 'package:flutter/material.dart';

/// Page showing the top contributing users for the current month.
class MonthlyLeaderBoardPage extends ConsumerStatefulWidget {
  const MonthlyLeaderBoardPage({Key? key}) : super(key: key);

  @override
  _MonthlyLeaderBoardPageState createState() => _MonthlyLeaderBoardPageState();
}

ScrollController _scrollController = new ScrollController();

class _MonthlyLeaderBoardPageState
    extends ConsumerState<MonthlyLeaderBoardPage> {
  late String? paginatedUrl;
  late int monthActive;
  CircleAvatar buildAvatar(String partUrl) {
    try {
      if (partUrl == "")
        return CircleAvatar(
          foregroundColor: Colors.transparent,
          radius: 20,
          child: Icon(
            Icons.account_circle_outlined,
            color: Color(0xFFDC4654),
            size: 40,
          ),
        );
      else
        return CircleAvatar(
          foregroundImage: CachedNetworkImageProvider(
              "https://bhfiles.storage.googleapis.com/" + partUrl),
          radius: 20,
        );
    } on Exception {
      return CircleAvatar(
        foregroundColor: Colors.transparent,
        backgroundColor: Colors.transparent,
        child: Icon(
          Icons.account_circle_outlined,
          color: Colors.white,
          size: 20,
        ),
      );
    }
  }

  @override
  void initState() {
    _scrollController.addListener(() async {
      if (_scrollController.position.pixels ==
          _scrollController.position.maxScrollExtent) {
        loadMoreLeaders();
      }
    });
    monthActive = DateTime.now().month;
    super.initState();
  }

  void loadMoreLeaders() {
    paginatedUrl = ref.watch(monthlyLeaderBoardProvider.notifier).nextUrl;
    if (paginatedUrl!.isNotEmpty) {
      ref.watch(monthlyLeaderBoardProvider.notifier).getMoreMontlyLeaders();
    }
  }

  @override
  Widget build(BuildContext context) {
    final Size size = MediaQuery.of(context).size;
    final monthlyLeadersState = ref.watch(monthlyLeaderBoardProvider);
    return PopScope(
        onPopInvokedWithResult: (__, _) async {
          ref
              .watch(monthlyLeaderBoardProvider.notifier)
              .refreshMonthlyLeaderList(
                  DateTime.now().year, DateTime.now().month);
        },
        child: Scaffold(
          appBar: AppBar(
            leading: IconButton(
              icon: Icon(
                Icons.arrow_back_ios_new_rounded,
              ),
              onPressed: () {
                Navigator.of(context).pop();
              },
            ),
            title: Text(AppLocalizations.of(context)!.monthlyLeaderboard),
            backgroundColor: Color(0xFFDC4654),
          ),
          body: SingleChildScrollView(
            child: Column(
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
                          AppLocalizations.of(context)!.monthlyLeaderboard,
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
                        child: Column(children: [
                          Text(
                            AppLocalizations.of(context)!
                                .theseAreMostActiveUsers,
                            style: GoogleFonts.aBeeZee(
                              textStyle: TextStyle(
                                color: Color(0xFF737373),
                              ),
                            ),
                          ),
                          TextButton.icon(
                            onPressed: () {
                              showModalBottomSheet(
                                context: context,
                                isScrollControlled: true,
                                constraints: BoxConstraints(
                                  maxHeight: 250,
                                ),
                                shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.only(
                                  topLeft: Radius.circular(10),
                                  topRight: Radius.circular(10),
                                )),
                                builder: (BuildContext context) {
                                  return Container(
                                      height: 250,
                                      alignment: Alignment.bottomCenter,
                                      child: ListView.builder(
                                        itemCount: DateTime.now().month,
                                        itemBuilder: (context, index) {
                                          return ListTile(
                                              onTap: () {
                                                ref
                                                    .watch(
                                                        monthlyLeaderBoardProvider
                                                            .notifier)
                                                    .refreshMonthlyLeaderList(
                                                        DateTime.now().year,
                                                        index + 1);
                                                setState(() {
                                                  monthActive = index + 1;
                                                });
                                                Navigator.pop(context);
                                              },
                                              tileColor: Color(0xFFECECEC)
                                                  .withOpacity(0.42),
                                              title: Text(
                                                "${monthsInYear[index + 1]}",
                                                style: GoogleFonts.ubuntu(
                                                  textStyle: TextStyle(
                                                    color: Color(0xFF737373),
                                                  ),
                                                ),
                                              ));
                                        },
                                      ));
                                },
                              );
                            },
                            icon: Icon(
                              Icons.calendar_month,
                              color: Colors.white,
                            ),
                            label: Text(
                              "${monthsInYear[monthActive]}",
                              style: GoogleFonts.aBeeZee(
                                textStyle: TextStyle(
                                  color: Colors.white,
                                  fontSize: 15,
                                ),
                              ),
                            ),
                            style: ButtonStyle(
                              backgroundColor:
                                  WidgetStateProperty.all(Color(0xFFDC4654)),
                            ),
                          ),
                        ]),
                      )
                    ],
                  ),
                ),
                Container(
                    height: size.height * 0.8,
                    padding: EdgeInsets.symmetric(horizontal: 20),
                    child: monthlyLeadersState!.when(
                        data: (List<Leaders>? leaderList) {
                      if (leaderList!.isEmpty) {
                        return Center(
                          child: Text(
                            AppLocalizations.of(context)!.noActivity,
                            textAlign: TextAlign.center,
                          ),
                        );
                      } else {
                        final list = leaderList;
                        return Padding(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 0.0,
                            vertical: 20.0,
                          ),
                          child: Material(
                            color: Colors.transparent,
                            child: ListView.builder(
                              controller: _scrollController,
                              itemCount: list.length,
                              itemBuilder: (context, index) {
                                return ListTile(
                                  onTap: () {},
                                  shape: RoundedRectangleBorder(
                                    borderRadius: index == 0
                                        ? BorderRadius.only(
                                            topLeft: Radius.circular(10),
                                            topRight: Radius.circular(15),
                                          )
                                        : index == list.length - 1
                                            ? BorderRadius.only(
                                                bottomLeft: Radius.circular(10),
                                                bottomRight:
                                                    Radius.circular(10),
                                              )
                                            : BorderRadius.only(
                                                topLeft: Radius.circular(0),
                                              ),
                                  ),
                                  tileColor:
                                      Color(0xFFECECEC).withOpacity(0.42),
                                  leading: buildAvatar(list[index].image),
                                  title: Text(
                                    list[index].user,
                                    style: GoogleFonts.ubuntu(
                                      textStyle: TextStyle(
                                        color: Color(0xFFDC4654),
                                      ),
                                    ),
                                    maxLines: 6,
                                  ),
                                  subtitle: Text(
                                    list[index].score.toString() +
                                        AppLocalizations.of(context)!.points,
                                    style: GoogleFonts.aBeeZee(
                                      textStyle: TextStyle(
                                        color: Color(0xFF737373),
                                        fontSize: 12,
                                      ),
                                    ),
                                    maxLines: 6,
                                  ),
                                  trailing: Text(
                                    "# " + (index + 1).toString(),
                                    style: GoogleFonts.ubuntu(
                                      textStyle: TextStyle(
                                        color: Color(0xFF737373),
                                        fontSize: 15,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ),
                                );
                              },
                            ),
                          ),
                        );
                      }
                    }, error: (Object error, StackTrace? stackTrace) {
                      return Center(
                        child: Text(
                          AppLocalizations.of(context)!.somethingWentWrong,
                          style: TextStyle(fontSize: 18),
                        ),
                      );
                    }, loading: () {
                      return Center(
                        child: CircularProgressIndicator(),
                      );
                    }))
              ],
            ),
          ),
        ));
  }
}
