import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../routes/routing.dart';
import '../components/searchbar.dart';
import '../global/variables.dart';

/// The app's main Appbar
AppBar buildAppBar({required BuildContext context}) {
  return AppBar(
    title: SvgPicture.asset(
      'assets/blt_logo.svg',
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
            delegate: BLTSearchDelegate(),
          );
          // do something
        },
      ),
      IconButton(
        icon: Icon(
          Icons.account_circle,
        ),
        onPressed: () {
          if(currentUser!.id == null){
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: const Text("No profile Found Check Your Connection"),
                  )
                );
                return;
          }
          Navigator.of(context).pushNamed(
            RouteManager.profilePage,
          );
          // do something
        },
      )
    ],
    elevation: 0,
    backgroundColor: Theme.of(context).canvasColor,
    iconTheme: IconThemeData(color: Color(0xFFDC4654)),
  );
}
