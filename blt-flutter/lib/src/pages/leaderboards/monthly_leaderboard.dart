import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../util/api/api.dart';

/// Page showing the top contributing users for the current month.
class MonthlyLeaderBoardPage extends StatefulWidget {
  const MonthlyLeaderBoardPage({Key? key}) : super(key: key);

  @override
  State<MonthlyLeaderBoardPage> createState() => _MonthlyLeaderBoardPageState();
}

class _MonthlyLeaderBoardPageState extends State<MonthlyLeaderBoardPage> {
  late Future _getObj;

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
              NetworkImage("https://bhfiles.storage.googleapis.com/" + partUrl),
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
    var paginatedUrl = 'https://www.bugheist.com/api/v1/userscore/';
    _getObj = ApiBackend().getLeaderData(paginatedUrl);
    super.initState();
  }

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
        title: Text("Monthly Leaderboard"),
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
                      'Monthly Leaderboards',
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
                      "These are the most active users on BugHeist this month.",
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
                      final list = snapshot.data as List;
                      return Padding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 0.0,
                          vertical: 20.0,
                        ),
                        child: Material(
                          color: Colors.transparent,
                          child: ListView.builder(
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
                                              bottomRight: Radius.circular(10),
                                            )
                                          : BorderRadius.only(
                                              topLeft: Radius.circular(0),
                                            ),
                                ),
                                tileColor: Color(0xFFECECEC).withOpacity(0.42),
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
                                  list[index].score.toString() + " points",
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
                        ),
                      );
                    }
                  }
                  return Center(
                    child: CircularProgressIndicator(),
                  );
                },
              ),
            )
          ],
        ),
      ),
    );
  }
}
