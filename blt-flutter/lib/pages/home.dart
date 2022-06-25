import 'package:bugheist/pages/feed.dart';
import 'package:bugheist/pages/issues.dart';
import 'package:bugheist/pages/leaderboard.dart';
import 'package:bugheist/pages/report_bug.dart';
import 'package:bugheist/routes/routing.dart';
import 'package:flutter/material.dart';

import 'components/appbar.dart';

class Home extends StatefulWidget {
  final int? startingIndex;
  const Home({
    Key? key,
    this.startingIndex,
  }) : super(key: key);

  @override
  _HomeState createState() => _HomeState();
}

class _HomeState extends State<Home> {
  late int _selectedIndex;
  late PageController _pageController;

  final List<Widget> _children = [
    PaginatedClass(),
    ReportBug(),
    Feed(),
    LeaderBoard()
  ];
  void _onItemTapped(int index) {
    setState(
      () {
        _selectedIndex = index;
        _pageController.animateToPage(
          index,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOut,
        );
      },
    );
  }

  @override
  void initState() {
    _selectedIndex = widget.startingIndex ?? 0;
    _pageController = PageController(
      initialPage: _selectedIndex,
      keepPage: true,
    );
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: buildAppBar(context: context),
      drawer: Drawer(
        // Add a ListView to the drawer. This ensures the user can scroll
        // through the options in the drawer if there isn't enough vertical
        // space to fit everything.
        child: ListView(
          // Important: Remove any padding from the ListView.
          padding: EdgeInsets.zero,
          children: <Widget>[
            UserAccountsDrawerHeader(
              onDetailsPressed: () {
                RouteManager.navigateToProfile(context);
              },
              decoration: BoxDecoration(
                color: Color(0xFFDC4654),
              ),
              accountName: Text(
                "anonymous",
                style: TextStyle(
                  color: Colors.white,
                ),
              ),
              accountEmail: Text(
                "anonymous@gmail.com",
                style: TextStyle(
                  color: Colors.white,
                ),
              ),
              currentAccountPicture: CircleAvatar(
                backgroundColor: Colors.white,
                child: Text(
                  "AN",
                  style: TextStyle(fontSize: 40.0),
                ),
                foregroundColor: Color(0xFFDC4654),
              ),
            ),
            ListTile(
              title: Text('Login'),
              onTap: () {
                // Update trhe state of the app
                // ...
                // Then close the drawer
                Navigator.pushReplacementNamed(
                  context,
                  RouteManager.loginSignupPage,
                );
              },
            ),
            ListTile(
              title: Text('Social'),
              onTap: () {
                // Update the state of the app
                // ...
                // Then close the drawer
                Navigator.pop(context);
              },
            ),
            ListTile(
              title: Text('Stats'),
              onTap: () {
                // Update the state of the app
                // ...
                // Then close the drawer
                Navigator.pop(context);
              },
            ),
            ListTile(
              title: Text('Terms of Service'),
              onTap: () {
                Navigator.pushNamed(
                  context,
                  RouteManager.legalPage,
                );

                // Update the state of the app
                // ...
                // Then close the drawer
              },
            ),
            ListTile(
              title: Text('About Us'),
              onTap: () {
                Navigator.pushNamed(
                  context,
                  RouteManager.aboutPage,
                );

                // Update the state of the app
                // ...
                // Then close the drawer
              },
            ),
          ],
        ),
      ),
      body: PageView(
          controller: _pageController,
          onPageChanged: (index) {
            setState(() => _selectedIndex = index);
          },
          children: _children),
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

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }
}
