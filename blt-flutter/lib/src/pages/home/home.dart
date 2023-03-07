import 'package:blt/src/global/variables.dart';
import 'package:blt/src/pages/home/issues.dart';
import 'package:blt/src/pages/home/leaderboard.dart';
import 'package:blt/src/pages/home/report_bug.dart';
import 'package:blt/src/pages/home/start_hunt.dart';
import 'package:blt/src/providers/authstate_provider.dart';
import 'package:blt/src/providers/login_provider.dart';
import 'package:blt/src/routes/routing.dart';
import 'package:blt/src/util/enums/login_type.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../components/appbar.dart';
import '../../pages/welcome.dart';


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

  // final List<ConsumerStatefulWidget> _children = [
  //   // Feed(),
  //   IssuesPage(),
  //   ReportBug(selectedWidgetName: ""),
  //   LeaderBoard()
  // ];
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

  void startBugHunt(BuildContext context) async {
    LoginType loginState = ref.watch(loginProvider);

    if (loginState == LoginType.guest) {
      await forgetUser();
              Navigator.of(context).pushAndRemoveUntil(MaterialPageRoute(
              builder: (context) => WelcomePage(snackBarMessage:"Only Logged in users can start a Bug Hunt")), (Route route) => false);
      await logout();
    } else {
      _onItemTapped(2);
      Navigator.pop(context);
    }
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
        forgetUser(); 
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
              Navigator.of(context).pushAndRemoveUntil(MaterialPageRoute(
              builder: (context) => WelcomePage()), (Route route) => false);
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
              ListTile(
                title: Container(
                  width: double.infinity,
                  height: 50,
                  child: Builder(
                    builder: (context) {
                      return TextButton(
                        child: Text(
                          "Start Bug Hunt",
                          style: GoogleFonts.ubuntu(
                            textStyle: TextStyle(
                              color: Colors.white,
                              fontSize: 20,
                            ),
                          ),
                        ),
                        style: ButtonStyle(
                          shape: MaterialStateProperty.all<RoundedRectangleBorder>(
                            RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(8.0),
                            ),
                          ),
                          backgroundColor: MaterialStateProperty.all(
                            Color(0xFFDC4654),
                          ),
                        ),
                        onPressed: () async {
                          startBugHunt(context);
                        },
                      );
                    }
                  ),
                ),
              ),
            ],
          ),
        ),
        body: PageView(
            controller: _pageController,
            onPageChanged: (index) {
              setState(() => _selectedIndex = index);
            },
            children: [
              // Feed(),
              IssuesPage(),
              ReportBug(),
              StartHuntPage(),
              LeaderBoard(),
            ]),
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
              icon: Icon(Icons.location_searching),
              label: 'Bug Hunt',
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
