import 'package:bugheist/services/api.dart';
import 'package:flutter/material.dart';
import 'dart:async';

class LeaderBoard extends StatefulWidget {
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

  @override
  Widget build(BuildContext context) {
    var r = TextStyle(color: Colors.purpleAccent, fontSize: 34);
    return Stack(
      children: <Widget>[
        Scaffold(
            body: Container(
          margin: EdgeInsets.only(top: 65.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Padding(
                padding: EdgeInsets.only(left: 15.0),
                child: Text(
                  'Global Leaderboard ',
                  style: TextStyle(fontWeight: FontWeight.bold),
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
                            return ListView.builder(
                                itemCount: list.length,
                                itemBuilder: (context, index) {
                                  return Padding(
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 5.0, vertical: 5.0),
                                    child: InkWell(
                                      child: Container(
                                        decoration: BoxDecoration(
                                            border: Border.all(
                                                color: i == 0
                                                    ? Colors.amber
                                                    : i == 1
                                                        ? Colors.grey
                                                        : i == 2
                                                            ? Colors.brown
                                                            : Colors.white,
                                                width: 3.0,
                                                style: BorderStyle.solid),
                                            borderRadius:
                                                BorderRadius.circular(5.0)),
                                        width:
                                            MediaQuery.of(context).size.width,
                                        child: Column(
                                          children: <Widget>[
                                            Row(
                                              children: <Widget>[
                                                Padding(
                                                  padding:
                                                      const EdgeInsets.only(
                                                          top: 10.0,
                                                          left: 15.0),
                                                  child: Row(
                                                    children: <Widget>[
                                                      CircleAvatar(
                                                        child: Container(
                                                          decoration:
                                                              BoxDecoration(
                                                            shape:
                                                                BoxShape.circle,
                                                            image: DecorationImage(
                                                                image: NetworkImage(
                                                                    "https://bhfiles.storage.googleapis.com/" +
                                                                        list[index]
                                                                            .image),
                                                                fit: BoxFit
                                                                    .fill),
                                                          ),
                                                        ),
                                                      ),
                                                    ],
                                                  ),
                                                ),
                                                Padding(
                                                  padding:
                                                      const EdgeInsets.only(
                                                          left: 20.0,
                                                          top: 10.0),
                                                  child: Column(
                                                    mainAxisAlignment:
                                                        MainAxisAlignment
                                                            .center,
                                                    crossAxisAlignment:
                                                        CrossAxisAlignment
                                                            .start,
                                                    children: <Widget>[
                                                      Container(
                                                        alignment: Alignment
                                                            .centerLeft,
                                                        child: Text(
                                                          list[index].user,
                                                          style: TextStyle(
                                                              color: Colors
                                                                  .deepPurple,
                                                              fontWeight:
                                                                  FontWeight
                                                                      .w500),
                                                          maxLines: 6,
                                                        ),
                                                      ),
                                                      Text("Points: " +
                                                          list[index]
                                                              .score
                                                              .toString()),
                                                    ],
                                                  ),
                                                ),
                                                Flexible(child: Container()),
                                                i == 0
                                                    ? Text("🥇", style: r)
                                                    : i == 1
                                                        ? Text(
                                                            "🥈",
                                                            style: r,
                                                          )
                                                        : i == 2
                                                            ? Text(
                                                                "🥉",
                                                                style: r,
                                                              )
                                                            : Text(''),
                                                Padding(
                                                  padding: EdgeInsets.only(
                                                      left: 20.0,
                                                      top: 13.0,
                                                      right: 20.0),
                                                ),
                                              ],
                                            ),
                                          ],
                                        ),
                                      ),
                                    ),
                                  );
                                });
                          }
                        }
                        return Center(
                          child: CircularProgressIndicator(),
                        );
                      }))
            ],
          ),
        )),
      ],
    );
  }
}
