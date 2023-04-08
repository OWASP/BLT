//import 'dart:async';

import 'package:blt/src/pages/onboarding_main_page.dart';
import 'package:blt/src/routes/routing.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
//import 'package:receive_sharing_intent/receive_sharing_intent.dart';

/// ### The BLT app's root widget
class BLT extends StatefulWidget {
  const BLT({Key? key}) : super(key: key);

  @override
  BLTState createState() => BLTState();
}

class BLTState extends State<BLT> {
  final _messengerKey = GlobalKey<ScaffoldMessengerState>();
  @override
  void initState() {
    super.initState();
  }

  @override
  void dispose() {
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // Intializing riverpod for state management
    return ProviderScope(
      child: GestureDetector(
        onTap: () {
          // This enables focusing out of text field, by touching anywhere
          // outside them
          FocusScopeNode currentScope = FocusScope.of(context);
          if (!currentScope.hasPrimaryFocus && currentScope.hasFocus) {
            FocusManager.instance.primaryFocus!.unfocus();
          }
        },
        child: MaterialApp(
          scaffoldMessengerKey: _messengerKey,
          debugShowCheckedModeBanner: false,
          onGenerateRoute: RouteManager.generateRoute,
          title: 'BLT',
          theme: ThemeData(
            // useMaterial3: true,
            primarySwatch: Colors.red,
            primaryColor: Colors.white,
            visualDensity: VisualDensity.adaptivePlatformDensity,
          ),
          home: Scaffold(body: OnboardingMainPage()),
        ),
      ),
    );
  }
}
