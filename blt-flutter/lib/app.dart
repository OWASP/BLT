import 'dart:async';

import 'package:bugheist/pages/welcome.dart';
import 'package:bugheist/routes/routing.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:receive_sharing_intent/receive_sharing_intent.dart';

class BugHeist extends StatefulWidget {
  const BugHeist({Key? key}) : super(key: key);

  @override
  BugHeistState createState() => BugHeistState();
}

class BugHeistState extends State<BugHeist> {
  late StreamSubscription _intentDataStreamSubscription;
  late List<SharedMediaFile> _sharedFiles;
  //late String _sharedText;
  final _messangerKey = GlobalKey<ScaffoldMessengerState>();
  @override
  void initState() {
    super.initState();
    // For sharing images coming from outside the app while the app is in the memory
    _intentDataStreamSubscription = ReceiveSharingIntent.getMediaStream()
        .listen((List<SharedMediaFile> value) {
      setState(() {
        print(_sharedFiles);
        _sharedFiles = value;
      });
    }, onError: (err) {
      print("getIntentDataStream error: $err");
    });

    // For sharing images coming from outside the app while the app is closed
    ReceiveSharingIntent.getInitialMedia().then((List<SharedMediaFile> value) {
      setState(() {
        _sharedFiles = value;
      });
    });

    // For sharing or opening urls/text coming from outside the app while the app is in the memory
    _intentDataStreamSubscription =
        ReceiveSharingIntent.getTextStream().listen((String value) {
      setState(() {
        print('detected a link here 1');
        print(value);
        //_sharedText = value;
      });
    }, onError: (err) {
      print("getLinkStream error: $err");
    });

    // For sharing or opening urls/text coming from outside the app while the app is closed
    ReceiveSharingIntent.getInitialText().then((value) {
      setState(() {
        print('detected text here:');
        print(value);
        //_sharedText = value;
      });
    });
  }

  @override
  void dispose() {
    _intentDataStreamSubscription.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ProviderScope(
      child: MaterialApp(
        scaffoldMessengerKey: _messangerKey,
        debugShowCheckedModeBanner: false,
        onGenerateRoute: RouteManager.generateRoute,
        title: 'BugHeist',
        theme: ThemeData(
          primarySwatch: Colors.red,
          primaryColor: Colors.white,
          visualDensity: VisualDensity.adaptivePlatformDensity,
          primaryTextTheme: TextTheme(
            headline1: TextStyle(
                fontSize: 72.0,
                fontWeight: FontWeight.bold,
                color: Colors.black),
            headline6: TextStyle(color: Colors.black),
            button: TextStyle(
              color: Colors.black,
            ),
          ),
        ),
        home: WelcomePage(),
      ),
    );
  }
}
