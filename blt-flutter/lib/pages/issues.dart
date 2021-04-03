import 'package:flutter/material.dart';
import '../pages/issue_detail.dart';

import '../services/api.dart';
import '../data/models.dart';
import 'login_signup.dart';

class PaginatedClass extends StatefulWidget {
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

  int _selectedIndex = 0;
  static const TextStyle optionStyle =
      TextStyle(fontSize: 30, fontWeight: FontWeight.bold);

  void _onItemTapped(int index) {
    setState(() {
      _selectedIndex = index;
    });
  }

  @override
  void initState() {
    paginatedUrl = 'https://www.bugheist.com/api/v1/issues/';
    _loading = false;

    animationController =
        AnimationController(duration: new Duration(seconds: 2), vsync: this);
    animationController.repeat();

    _getObj = ApiBackend().getApiData(paginatedUrl);

    _scrollController.addListener(() async {
      if (_scrollController.position.pixels ==
          _scrollController.position.maxScrollExtent) {
        if (!_loading && mounted) {
          setState(() {
            _loading = true;
          });
        }

        _getObj.then((value) async {
          if (value.next != 'null') {
            DataModel _paginatedData =
                await ApiBackend().getApiData(value.next);
            if (mounted) {
              setState(() {
                for (var i = 0; i < _paginatedData.results.length; i++) {
                  value.results.add(_paginatedData.results[i]);
                }
                value.next = _paginatedData.next;
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
    return SafeArea(
      child: Scaffold(
        appBar: AppBar(
          centerTitle: true,
          title: Image.asset(
            'assets/bugheist_logo.png',
            fit: BoxFit.cover,
            height: 30,
          ),
          actions: <Widget>[
            IconButton(
              icon: Icon(
                Icons.search,
                color: Colors.black,
              ),
              onPressed: () {
                // do something
              },
            ),
            IconButton(
              icon: Icon(
                Icons.portrait_rounded,
                color: Colors.black,
              ),
              onPressed: () {
                // do something
              },
            )
          ],
        ),
        drawer: Drawer(
          // Add a ListView to the drawer. This ensures the user can scroll
          // through the options in the drawer if there isn't enough vertical
          // space to fit everything.
          child: ListView(
            // Important: Remove any padding from the ListView.
            padding: EdgeInsets.zero,
            children: <Widget>[
              DrawerHeader(
                child: Text('Drawer Header'),
                decoration: BoxDecoration(
                  color: Color(0xFFDC4654),
                ),
              ),
              ListTile(
                title: Text('Login'),
                onTap: () {
                  // Update the state of the app
                  // ...
                  // Then close the drawer
                  Navigator.pushReplacement(
                    context,
                    MaterialPageRoute(
                      builder: (context) => LoginSignUp(),
                    ),
                  );
                },
              ),
              ListTile(
                title: Text('Item 2'),
                onTap: () {
                  // Update the state of the app
                  // ...
                  // Then close the drawer
                  Navigator.pop(context);
                },
              ),
            ],
          ),
        ),
        body: FutureBuilder(
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
                    itemCount: (snapshot.data! as DataModel).results.length + 1,
                    controller: _scrollController,
                    itemBuilder: (context, index) {
                      if (index == (snapshot.data! as DataModel).results.length)
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
                        return new GestureDetector(
                          onTap: () => {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (context) => ArticleOnePage(
                                  issue: (snapshot.data! as DataModel)
                                      .results[index],
                                ),
                              ),
                            )
                          },
                          child: Column(
                            children: [
                              Card(
                                margin: EdgeInsets.all(10),
                                elevation: 0,
                                clipBehavior: Clip.antiAlias,
                                shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.only(
                                        topRight: Radius.circular(15.0),
                                        bottomRight: Radius.circular(15.0))),
                                child: Container(
                                  height: 130,
                                  padding: const EdgeInsets.all(0),
                                  child: Row(
                                    children: <Widget>[
                                      Container(
                                        width: 200,
                                        height: 130,
                                        child: Hero(
                                          tag: (snapshot.data! as DataModel)
                                              .results[index]
                                              .screenshot,
                                          child: DecoratedBox(
                                            decoration: BoxDecoration(
                                              image: DecorationImage(
                                                image: NetworkImage(
                                                  (snapshot.data! as DataModel)
                                                      .results[index]
                                                      .screenshot,
                                                ),
                                                fit: BoxFit.cover,
                                              ),
                                            ),
                                          ),
                                        ),
                                      ),
                                      Flexible(
                                        child: Padding(
                                          padding: const EdgeInsets.symmetric(
                                            horizontal: 10,
                                          ),
                                          child: Column(
                                            children: <Widget>[
                                              Row(
                                                children: <Widget>[
                                                  Flexible(
                                                    child: Text(
                                                      (snapshot.data!
                                                              as DataModel)
                                                          .results[index]
                                                          .description,
                                                      overflow:
                                                          TextOverflow.fade,
                                                      softWrap: true,
                                                      style: TextStyle(
                                                          fontWeight:
                                                              FontWeight.w600,
                                                          fontSize: 12),
                                                    ),
                                                  ),
                                                ],
                                              ),
                                            ],
                                          ),
                                        ),
                                      )
                                    ],
                                  ),
                                ),
                              )
                            ],
                          ),
                        );
                    });
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
        bottomNavigationBar: BottomNavigationBar(
          type: BottomNavigationBarType.fixed,
          items: const <BottomNavigationBarItem>[
            BottomNavigationBarItem(
              icon: Icon(Icons.home),
              label: 'Home',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.bug_report),
              label: 'Report',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.list),
              label: 'Issues',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.leaderboard),
              label: 'Leaderboard',
            ),
          ],
          currentIndex: _selectedIndex,
          selectedItemColor: Color(0xFFDC4654),
          onTap: _onItemTapped,
        ),
      ),
    );
  }
}
