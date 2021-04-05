import 'package:bugheist/pages/feed.dart';
import 'package:bugheist/pages/issues.dart';
import 'package:bugheist/pages/leaderboard.dart';
import 'package:bugheist/pages/login_signup.dart';
import 'package:bugheist/pages/report_bug.dart';
import 'package:flutter/material.dart';

class Home extends StatefulWidget {
  @override
  _HomeState createState() => _HomeState();
}

class _HomeState extends State<Home> {
  int _selectedIndex = 0;
  final List<Widget> _children = [
    PaginatedClass(), ReportBug(), Feed(), LeaderBoard()
  ];
  void _onItemTapped(int index) {
    setState(() {
      _selectedIndex = index;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
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
      body: _children[_selectedIndex],
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
    );
  }
}
