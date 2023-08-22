import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../constants/monthname_constants.dart';
import '../../routes/routing.dart';
import '../../providers/leaderboards/globalleaderboard_povider.dart';
import '../../providers/leaderboards/monthlyleaderboard_provider.dart';
import '../../providers/leaderboards/companyscoreboard_provider.dart';

/// The Leaderboards dashboard page, contains the Global,
/// Monthly leaderboard, and Company Scoreboard.
class LeaderBoard extends ConsumerStatefulWidget {
  const LeaderBoard({Key? key}) : super(key: key);

  @override
  _LeaderBoardState createState() => _LeaderBoardState();
}

class _LeaderBoardState extends ConsumerState<LeaderBoard> {
  @override
  void initState() {
    super.initState();
  }

  @override
  void dispose() {
    super.dispose();
  }

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
          foregroundImage:
          CachedNetworkImageProvider("https://bhfiles.storage.googleapis.com/" + partUrl),
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

  CircleAvatar buildLogo(String partUrl) {
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
            "https://storage.googleapis.com/bhfiles/" + partUrl,
          ),
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
  Widget build(BuildContext context) {
    final Size size = MediaQuery.of(context).size;

    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      padding: EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: EdgeInsets.fromLTRB(0, 12, 0, 12),
            alignment: Alignment.centerLeft,
            child: Text(
              "Leaderboards",
              style: GoogleFonts.ubuntu(
                textStyle: TextStyle(color: Color(0xFF737373), fontSize: 30),
              ),
            ),
          ),
          Container(
            padding: EdgeInsets.fromLTRB(0, 0, 0, 16),
            child: Text(
              "Find out the users best at heisting those bugs and companies that are the most active!",
              style: GoogleFonts.aBeeZee(
                textStyle: TextStyle(
                  color: Color(0xFF737373),
                ),
              ),
            ),
          ),
          Container(
            padding: EdgeInsets.fromLTRB(0, 0, 0, 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                ListTile(
                  title: Text(
                    "Global Leaderboard",
                    style: GoogleFonts.ubuntu(
                      textStyle: TextStyle(
                        color: Color(0xFFDC4654),
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  trailing: IconButton(
                    icon: Icon(
                      Icons.arrow_forward_ios_rounded,
                      color: Color(0xFFDC4654),
                    ),
                    onPressed: () {
                      Navigator.pushNamed(
                        context,
                        RouteManager.globalLeaderboardPage,
                      );
                    },
                  ),
                ),
                Text(
                  "Find out the best of the best, the all time finest bug finders!",
                  style: GoogleFonts.aBeeZee(
                    textStyle: TextStyle(
                      color: Color(0xFF737373),
                    ),
                  ),
                ),
                Container(
                  height: 0.3 * size.height,
                  padding: const EdgeInsets.fromLTRB(0, 20, 0, 10),
                  child: Consumer(
                    builder: (context, ref, child) {
                      final globalLeaderboardList = ref.watch(
                        globalLeaderBoardProvider,
                      );
                      return globalLeaderboardList!.when(
                        data: (leaderList) {
                          return InkWell(
                            onTap: () {
                              Navigator.pushNamed(
                                context,
                                RouteManager.globalLeaderboardPage,
                              );
                            },
                            child: ListView.builder(
                              padding: EdgeInsets.zero,
                              itemCount: 3,
                              shrinkWrap: true,
                              itemBuilder: (context, index) {
                                return ListTile(
                                  shape: RoundedRectangleBorder(
                                    borderRadius: index == 0
                                        ? BorderRadius.only(
                                            topLeft: Radius.circular(10),
                                            topRight: Radius.circular(15),
                                          )
                                        : index == 2
                                            ? BorderRadius.only(
                                                bottomLeft: Radius.circular(10),
                                                bottomRight:
                                                    Radius.circular(10),
                                              )
                                            : BorderRadius.only(
                                                topLeft: Radius.circular(0),
                                              ),
                                  ),
                                  tileColor: index == 2
                                      ? Color(0xFFC9AE5D).withOpacity(0.42)
                                      : index == 1
                                          ? Color(0xFFADD8E6).withOpacity(0.42)
                                          : index == 0
                                              ? Color(0xFFFFD700)
                                                  .withOpacity(0.42)
                                              : Colors.white,
                                  leading:
                                      buildAvatar(leaderList![index].image),
                                  title: Text(
                                    leaderList[index].user,
                                    style: GoogleFonts.ubuntu(
                                      textStyle: TextStyle(
                                        color: Color(0xFFDC4654),
                                      ),
                                    ),
                                    maxLines: 6,
                                  ),
                                  subtitle: Text(
                                    leaderList[index].score.toString() +
                                        " points",
                                    style: GoogleFonts.aBeeZee(
                                      textStyle: TextStyle(
                                        color: Color(0xFF737373),
                                        fontSize: 12,
                                      ),
                                    ),
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
                          );
                        },
                        error: (error, stackTr) {
                          return Center(
                            child: Text(
                              'Something went wrong!',
                              style: TextStyle(fontSize: 18),
                            ),
                          );
                        },
                        loading: () {
                          return Center(
                            child: CircularProgressIndicator(),
                          );
                        },
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
          Container(
            padding: EdgeInsets.fromLTRB(0, 0, 0, 12),
            color: Theme.of(context).canvasColor,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                ListTile(
                  title: Text(
                    "Monthly Leaderboard",
                    style: GoogleFonts.ubuntu(
                      textStyle: TextStyle(
                        color: Color(0xFFDC4654),
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  trailing: IconButton(
                    icon: Icon(
                      Icons.arrow_forward_ios_rounded,
                      color: Color(0xFFDC4654),
                    ),
                    onPressed: () {
                      Navigator.pushNamed(
                        context,
                        RouteManager.monthlyLeaderboardPage,
                      );
                    },
                  ),
                ),
                Text(
                  "Check the best bug hunters in ${monthsInYear[DateTime.now().month]}.!",
                  style: GoogleFonts.aBeeZee(
                    textStyle: TextStyle(
                      color: Color(0xFF737373),
                    ),
                  ),
                ),
                Container(
                  height: 0.3 * size.height,
                  padding: const EdgeInsets.fromLTRB(0, 20, 0, 10),
                  child: Consumer(
                    builder: (context, ref, child) {
                      final monthlyLeaderboardList = ref.watch(
                        monthlyLeaderBoardProvider,
                      );
                      return monthlyLeaderboardList!.when(
                        data: (leaderList) {
                          return InkWell(
                            onTap: () {
                              Navigator.pushNamed(
                                context,
                                RouteManager.monthlyLeaderboardPage,
                              );
                            },
                            child: ListView.builder(
                              padding: EdgeInsets.zero,
                              itemCount: (leaderList!.length < 3 ? leaderList.length : 3),
                              shrinkWrap: true,
                              itemBuilder: (context, index) {
                                return ListTile(
                                  shape: RoundedRectangleBorder(
                                    borderRadius: index == 0
                                        ? BorderRadius.only(
                                            topLeft: Radius.circular(10),
                                            topRight: Radius.circular(15),
                                          )
                                        : index == 2
                                            ? BorderRadius.only(
                                                bottomLeft: Radius.circular(10),
                                                bottomRight:
                                                    Radius.circular(10),
                                              )
                                            : BorderRadius.only(
                                                topLeft: Radius.circular(0),
                                              ),
                                  ),
                                  tileColor: index == 2
                                      ? Color(0xFFC9AE5D).withOpacity(0.42)
                                      : index == 1
                                          ? Color(0xFFADD8E6).withOpacity(0.42)
                                          : index == 0
                                              ? Color(0xFFFFD700)
                                                  .withOpacity(0.42)
                                              : Colors.white,
                                  leading:
                                      buildAvatar(leaderList[index].image),
                                  title: Text(
                                    leaderList[index].user,
                                    style: GoogleFonts.ubuntu(
                                      textStyle: TextStyle(
                                        color: Color(0xFFDC4654),
                                      ),
                                    ),
                                    maxLines: 6,
                                  ),
                                  subtitle: Text(
                                    leaderList[index].score.toString() +
                                        " points",
                                    style: GoogleFonts.aBeeZee(
                                      textStyle: TextStyle(
                                        color: Color(0xFF737373),
                                        fontSize: 12,
                                      ),
                                    ),
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
                          );
                        },
                        error: (error, stackTr) {
                          return const Center(
                            child: Text(
                              'Something went wrong!',
                              style: TextStyle(fontSize: 18),
                            ),
                          );
                        },
                        loading: () {
                          return const Center(
                            child: CircularProgressIndicator(),
                          );
                        },
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
          Container(
            padding: EdgeInsets.fromLTRB(0, 0, 0, 12),
            color: Theme.of(context).canvasColor,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                ListTile(
                  title: Text(
                    "Company Scoreboard",
                    style: GoogleFonts.ubuntu(
                      textStyle: TextStyle(
                        color: Color(0xFFDC4654),
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  trailing: IconButton(
                    icon: Icon(
                      Icons.arrow_forward_ios_rounded,
                      color: Color(0xFFDC4654),
                    ),
                    onPressed: () {
                      Navigator.pushNamed(
                        context,
                        RouteManager.companyScoreboardPage,
                      );
                    },
                  ),
                ),
                Text(
                  "Take a look at the most active companies on BLT!",
                  style: GoogleFonts.aBeeZee(
                    textStyle: TextStyle(
                      color: Color(0xFF737373),
                    ),
                  ),
                ),
                Container(
                  height: 0.3 * size.height,
                  padding: const EdgeInsets.fromLTRB(0, 20, 0, 10),
                  child: Consumer(
                    builder: (context, ref, child) {
                      final companyList = ref.watch(companyScoreboardProvider);
                      return companyList!.when(
                        data: (companyData) {
                          return InkWell(
                            onTap: () {
                              Navigator.pushNamed(
                                context,
                                RouteManager.companyScoreboardPage,
                              );
                            },
                            child: Material(
                              color: Colors.transparent,
                              child: ListView.builder(
                                itemCount: 3,
                                itemBuilder: (context, index) {
                                  return ListTile(
                                    shape: RoundedRectangleBorder(
                                      borderRadius: index == 0
                                          ? BorderRadius.only(
                                              topLeft: Radius.circular(10),
                                              topRight: Radius.circular(15),
                                            )
                                          : index == 2
                                              ? BorderRadius.only(
                                                  bottomLeft:
                                                      Radius.circular(10),
                                                  bottomRight:
                                                      Radius.circular(10),
                                                )
                                              : BorderRadius.only(
                                                  topLeft: Radius.circular(0),
                                                ),
                                    ),
                                    tileColor: Color(0xFFE0E0E0),
                                    leading: buildLogo(
                                      companyData![index].logoLink,
                                    ),
                                    title: Text(
                                      companyData[index].companyName,
                                      style: GoogleFonts.ubuntu(
                                        textStyle: TextStyle(
                                          color: Color(0xFFDC4654),
                                        ),
                                      ),
                                      maxLines: 6,
                                    ),
                                    subtitle: Text(
                                      "Open: " +
                                          companyData[index]
                                              .openIssues
                                              .toString() +
                                          "| Closed: " +
                                          companyData[index]
                                              .closedIssues
                                              .toString(),
                                      style: GoogleFonts.aBeeZee(
                                        textStyle: TextStyle(
                                          color: Color(0xFF737373),
                                          fontSize: 12,
                                        ),
                                      ),
                                    ),
                                    trailing: Text(
                                      companyData[index].topTester.toString(),
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
                        },
                        error: (error, stackTr) {
                          return const Center(
                            child: Text(
                              'Something went wrong!',
                              style: TextStyle(fontSize: 18),
                            ),
                          );
                        },
                        loading: () {
                          return const Center(
                            child: CircularProgressIndicator(),
                          );
                        },
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
