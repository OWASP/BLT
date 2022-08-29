import 'package:bugheist/src/components/searchbar.dart';
import 'package:bugheist/src/routes/routing.dart';
import 'package:flutter/material.dart';

/// The app's main Appbar
AppBar buildAppBar({required BuildContext context}) {
  return AppBar(
    title: Image.asset(
      'assets/bugheist_logo.png',
      fit: BoxFit.cover,
      height: 30,
    ),
    actions: <Widget>[
      IconButton(
        icon: Icon(
          Icons.search,
        ),
        onPressed: () {
          showSearch(
            context: context,
            delegate: BugHeistSearchDelegate(),
          );
          // do something
        },
      ),
      IconButton(
        icon: Icon(
          Icons.account_circle,
        ),
        onPressed: () {
          RouteManager.navigateToProfile(context);
          // do something
        },
      )
    ],
    elevation: 0,
    backgroundColor: Theme.of(context).canvasColor,
    iconTheme: IconThemeData(color: Color(0xFFDC4654)),
  );
}
