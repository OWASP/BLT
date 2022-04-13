import 'package:bugheist/services/api.dart';
import 'package:flutter/material.dart';
import 'dart:async';

class LeaderBoard extends StatefulWidget {
  const LeaderBoard({Key? key}) : super(key: key);

  @override
  _LeaderBoardState createState() => _LeaderBoardState();
}

class _LeaderBoardState extends State<LeaderBoard> {
  int i = 0;
  Color my = Colors.brown;
  late Future _getObj;

  @override
  void initState() {
    var paginatedUrl = 'https://www.bugheist.com/api/v1/userscore/';
    _getObj = ApiBackend().getLeaderData(paginatedUrl);
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
          // backgroundColor: Colors.transparent,
          radius: 20,
          child: Icon(
            Icons.account_circle_outlined,
            color: Colors.green,
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
  Widget build(BuildContext context) {
    var r = TextStyle(fontSize: 34);
    return Stack(
      children: <Widget>[
        Scaffold(
          body: Container(
            margin: EdgeInsets.only(top: 10.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: <Widget>[
                Padding(
                  padding: EdgeInsets.symmetric(horizontal: 8),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Padding(
                        padding: const EdgeInsets.all(8.0),
                        child: Icon(
                          Icons.public,
                          color: Colors.green,
                        ),
                      ),
                      Text(
                        'Global Leaderboard ',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 25,
                          color: Colors.green,
                        ),
                      ),
                    ],
                  ),
                ),
                Flexible(
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
                          i = 0;
                          return Padding(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 0.0,
                              vertical: 10.0,
                            ),
                            child: ListView.builder(
                              itemCount: list.length,
                              itemBuilder: (context, index) {
                                int title = list[index].title;
                                return Padding(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 10.0, vertical: 0.0),
                                  child: ListTile(
                                    onTap: () {},
                                    shape: RoundedRectangleBorder(
                                      borderRadius: index == 0
                                          ? BorderRadius.only(
                                              topLeft: Radius.circular(10),
                                              topRight: Radius.circular(15),
                                            )
                                          : index == list.length - 1
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
                                    tileColor: title == 1
                                        ? Colors.brown.withOpacity(0.2)
                                        : title == 2
                                            ? Colors.grey.withOpacity(0.2)
                                            : title == 3
                                                ? Colors.yellow.withOpacity(0.2)
                                                : Colors.white,
                                    leading: buildAvatar(list[index].image),
                                    title: Text(
                                      list[index].user,
                                      style: TextStyle(
                                          color: Colors.deepPurple,
                                          fontWeight: FontWeight.w500),
                                      maxLines: 6,
                                    ),
                                    subtitle: Text(
                                      "Points: " + list[index].score.toString(),
                                    ),
                                    trailing: title == 3
                                        ? Text(
                                            "🥇",
                                            style: r,
                                          )
                                        : title == 2
                                            ? Text(
                                                "🥈",
                                                style: r,
                                              )
                                            : title == 1
                                                ? Text(
                                                    "🥉",
                                                    style: r,
                                                  )
                                                : Text(''),
                                  ),
                                );
                              },
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
        ),
      ],
    );
  }
}
