import 'dart:async';
import 'package:bugheist/pages/issues.dart';
import 'package:flutter/material.dart';
import 'package:bugheist/pages/login_signup.dart';

class Splash extends StatefulWidget {
  @override
  _SplashState createState() => _SplashState();
}

class _SplashState extends State<Splash> {
  @override
  void initState() {
    super.initState();
    LoginSignUp();
    Timer(
        Duration(seconds: 3),
        () => Navigator.pushReplacement(context,
            MaterialPageRoute(builder: (context) => PaginatedClass())));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Image.asset(
              'logo.png',
              width: 120.0,
              height: 120.0,
            ),
            SizedBox(
              height: 15.0,
            ),
            Text(
              'Bugheist',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 30.0),
            )
          ],
        ),
      ),
    );
  }
}
