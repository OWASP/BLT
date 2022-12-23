import 'package:bugheist/src/global/variables.dart';
// import 'package:bugheist/src/pages/home/feed.dart';
import 'package:bugheist/src/pages/home/issues.dart';
import 'package:bugheist/src/pages/home/leaderboard.dart';
import 'package:bugheist/src/pages/home/report_bug.dart';
import 'package:bugheist/src/providers/authstate_provider.dart';
import 'package:bugheist/src/providers/login_provider.dart';
import 'package:bugheist/src/routes/routing.dart';
import 'package:bugheist/src/util/enums/login_type.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../components/appbar.dart';

/// Navigator and drawer provider for the main pages:
/// Issues, Report Bug, Leaderboards and Feed.
class Home extends ConsumerStatefulWidget {
  final int? startingIndex;
  const Home({
    Key? key,
    this.startingIndex,
  }) : super(key: key);

  @override
  ConsumerState<ConsumerStatefulWidget> createState() => _HomeState();
}

class _HomeState extends ConsumerState<Home> {
  late int _selectedIndex;
  late PageController _pageController;

  final List<ConsumerStatefulWidget> _children = [
    // Feed(),
    IssuesPage(),
    ReportBug(),
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

  String buildLogoutText() {
    LoginType loginState = ref.watch(loginProvider);

    return loginState == LoginType.guest ? "Logout (Guest)" : "Logout";
  }

  Widget buildReferralOption() {
    LoginType loginState = ref.watch(loginProvider);

    return loginState == LoginType.user
        ? ListTile(
            title: Text('Invite'),
            onTap: () {
              // Update the state of the app
              // ...
              // Then close the drawer
              Navigator.pushNamed(
                context,
                RouteManager.referralPage,
              );
              // Navigator.pop(context);
            },
          )
        : SizedBox();
  }

  NetworkImage? buildAvatar() {
    LoginType loginState = ref.watch(loginProvider);

    return loginState != LoginType.guest
        ? (currentUser!.pfpLink != null)
            ? NetworkImage(currentUser!.pfpLink!)
            : null
        : NetworkImage(
            currentUser!.pfpLink!,
          );
  }

  Future<void> logout() async {
    await ref.read(authStateNotifier.notifier).logout();
  }

  Future<void> forgetUser() async {
    await ref.read(authStateNotifier.notifier).forgetUser();
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
    return WillPopScope(
      onWillPop: () async {
        logout();
        return true;
      },
      child: Scaffold(
        appBar: buildAppBar(context: context),
        drawer: Drawer(
          child: ListView(
            padding: EdgeInsets.zero,
            children: <Widget>[
              UserAccountsDrawerHeader(
                decoration: BoxDecoration(
                  color: Color(0xFFDC4654),
                ),
                accountName: Text(
                  currentUser!.username!,
                  style: TextStyle(color: Colors.white, fontSize: 20),
                ),
                accountEmail: Text(
                  "",
                  style: TextStyle(
                    color: Colors.white,
                  ),
                ),
                currentAccountPicture: CircleAvatar(
                  backgroundColor: Colors.white,
                  foregroundImage: buildAvatar(),
                  child: Text(
                    currentUser!.username!.substring(0, 2),
                    style: TextStyle(fontSize: 40.0),
                  ),
                  foregroundColor: Color(0xFFDC4654),
                ),
              ),
              ListTile(
                title: Text(buildLogoutText()),
                onTap: () async {
                  // Update trhe state of the app
                  // ...
                  // Then close the drawer
                  await forgetUser();
                  Navigator.pushReplacementNamed(
                    context,
                    RouteManager.welcomePage,
                  );
                  await logout();
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
              ListTile(
                title: Text('Company Dashboard'),
                onTap: () {
                  Navigator.pushNamed(
                    context,
                    RouteManager.companyDashboardPage,
                  );

                  // Update the state of the app
                  // ...
                  // Then close the drawer
                },
              ),
              buildReferralOption(),
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
            // BottomNavigationBarItem(
            //   icon: Icon(Icons.home),
            //   label: 'Home',
            // ),
            BottomNavigationBarItem(
              icon: Icon(Icons.list),
              label: 'Issues',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.bug_report),
              label: 'Report',
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

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }
}
