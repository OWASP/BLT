import 'package:bugheist/routes/routing.dart';
import 'package:flutter/material.dart';

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
