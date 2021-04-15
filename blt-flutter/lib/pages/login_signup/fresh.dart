import 'package:bugheist/pages/home.dart';
import 'package:flutter/material.dart';

import 'package:bugheist/data/login_model.dart';

import 'package:bugheist/config/login_signup_structure.dart';

/// Widget main with social networks
class LoginFresh extends StatefulWidget {
  /// color main login
  final Color backgroundColor;

  ///color of card where are the login icons
  final Color cardColor;

  /// color of text in login
  final Color textColor;

  /// url logo main in login
  final String pathLogo;

  ///button when you want to avoid the login and go to the application content
  final bool isExploreApp;

  ///function when you want to avoid the login and go to the application content
  final Function functionExploreApp;

  ///widget to put a footer in your login
  final bool isFooter;

  /// custom widget footer
  final Widget widgetFooter;

  /// list type login import in login
  final List<LoginFreshTypeLoginModel> typeLoginModel;

  /// is signUp in login
  final bool isSignUp;

  ///widget signUp
  final Widget widgetSignUp;

  //model of key words used in login
  LoginFreshWords keyWord;

  LoginFresh(
      {required this.pathLogo,
      required this.typeLoginModel,
      required this.isExploreApp,
      required this.functionExploreApp,
      required this.isSignUp,
      required this.widgetSignUp,
      required this.isFooter,
      required this.widgetFooter,
      required this.backgroundColor,
      required this.cardColor,
      required this.textColor,
      required this.keyWord});

  @override
  _LoginFreshState createState() => _LoginFreshState();
}

class _LoginFreshState extends State<LoginFresh> {
  @override
  Widget build(BuildContext context) {
    widget.keyWord = widget.keyWord;

    return Stack(
      children: [
        Container(
          color: widget.backgroundColor,
          child: Align(
            alignment: Alignment.topCenter,
            child: Container(
              height: MediaQuery.of(context).size.height * 0.45,
              width: MediaQuery.of(context).size.width * 0.60,
              child: Center(
                child: Image.asset(
                  widget.pathLogo,
                  fit: BoxFit.contain,
                ),
              ),
            ),
          ),
        ),
        Align(
            alignment: Alignment.bottomCenter,
            child: Container(
              height: MediaQuery.of(context).size.height * 0.55,
              width: MediaQuery.of(context).size.width,
              decoration: new BoxDecoration(
                  color: widget.cardColor,
                  borderRadius: new BorderRadius.only(
                    topLeft: const Radius.circular(50.0),
                    topRight: const Radius.circular(50.0),
                  )),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                crossAxisAlignment: CrossAxisAlignment.center,
                mainAxisSize: MainAxisSize.max,
                children: [
                  SizedBox(),
                  Column(
                    children: [
                      buildLoginWith(),
                      buildTypeLogin(context),
                      !widget.isExploreApp
                          ? SizedBox()
                          : SizedBox(
                              height: 20,
                            ),
                      buildExploreApp(context),
                      !widget.isSignUp ? SizedBox() : buildSignUp(),
                    ],
                  ),
                  !widget.isFooter ? SizedBox() : widget.widgetFooter
                ],
              ),
            ))
      ],
    );
  }

  GestureDetector buildSignUp() {
    return GestureDetector(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 25, horizontal: 10),
        child: RichText(
          textAlign: TextAlign.center,
          text: TextSpan(children: [
            TextSpan(
                text: widget.keyWord.notAccount + '\n',
                style: TextStyle(
                    color: widget.textColor,
                    fontWeight: FontWeight.normal,
                    fontSize: 15)),
            TextSpan(
                text: widget.keyWord.signUp,
                style: TextStyle(
                    decoration: TextDecoration.underline,
                    color: widget.textColor,
                    fontWeight: FontWeight.bold,
                    fontSize: 16)),
          ]),
        ),
      ),
      onTap: () {
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_buildContext) => widget.widgetSignUp),
        );
      },
    );
  }

  Widget buildExploreApp(BuildContext context) {
    return !widget.isExploreApp
        ? SizedBox()
        : GestureDetector(
            onTap: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_buildContext) => Home(),
                ),
              );
            },
            child: SizedBox(
                height: MediaQuery.of(context).size.height * 0.07,
                width: (widget.typeLoginModel.length > 3)
                    ? MediaQuery.of(context).size.width * 0.90
                    : MediaQuery.of(context).size.width * 0.80,
                child: Card(
                    elevation: 10,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(40),
                    ),
                    color: Colors.white,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 10),
                      child: Center(
                          child: Text(
                        widget.keyWord.exploreApp,
                        style: TextStyle(
                            color: widget.textColor,
                            fontSize: 15,
                            fontWeight: FontWeight.bold),
                      )),
                    ))),
          );
  }

  SizedBox buildTypeLogin(BuildContext context) {
    return SizedBox(
      height: MediaQuery.of(context).size.height * 0.1,
      width: (widget.typeLoginModel.length > 3)
          ? MediaQuery.of(context).size.width * 0.90
          : MediaQuery.of(context).size.width * 0.80,
      child: Card(
        elevation: 10,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(40),
        ),
        color: Colors.white,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10),
          child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              crossAxisAlignment: CrossAxisAlignment.center,
              mainAxisSize: MainAxisSize.max,
              children: this.getCardLogin()),
        ),
      ),
    );
  }

  Padding buildLoginWith() {
    return Padding(
      padding: const EdgeInsets.all(8.0),
      child: Text(widget.keyWord.loginWith,
          style: TextStyle(
              color: widget.textColor,
              fontSize: 16,
              fontWeight: FontWeight.bold)),
    );
  }

  List<Widget> getCardLogin() {
    List<Widget> list = [];

    for (LoginFreshTypeLoginModel tlm in widget.typeLoginModel) {
      list.add(GestureDetector(
        child: Padding(
          padding: const EdgeInsets.all(8.0),
          child: Image(
            image: ExactAssetImage(
              tlm.logo,
            ),
          ),
        ),
        onTap: () {
          tlm.callFunction(context);
        },
      ));
    }

    return list;
  }
}
