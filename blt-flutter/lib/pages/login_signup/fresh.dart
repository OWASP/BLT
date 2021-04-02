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
      {@required this.pathLogo,
      this.typeLoginModel,
      this.isExploreApp,
      this.functionExploreApp,
      this.isSignUp,
      this.widgetSignUp,
      this.isFooter,
      this.widgetFooter,
      this.backgroundColor,
      this.cardColor,
      this.textColor,
      this.keyWord});

  @override
  _LoginFreshState createState() => _LoginFreshState();
}

class _LoginFreshState extends State<LoginFresh> {
  @override
  Widget build(BuildContext context) {
    widget.keyWord = widget.keyWord ?? LoginFreshWords();

    return Stack(
      children: [
        Container(
          color: widget.backgroundColor ?? Color(0xFFE7004C),
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
                  color: widget.cardColor ?? Color(0xFFF3F3F5),
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
                      (widget.isExploreApp == null ||
                              widget.isExploreApp == false)
                          ? SizedBox()
                          : SizedBox(
                              height: 20,
                            ),
                      buildExploreApp(context),
                      (widget.isSignUp == null || widget.isSignUp == false)
                          ? SizedBox()
                          : buildSignUp(),
                    ],
                  ),
                  (widget.isFooter == null || widget.isFooter == false)
                      ? SizedBox()
                      : widget.widgetFooter
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
                    color: widget.textColor ?? Color(0xFF0F2E48),
                    fontWeight: FontWeight.normal,
                    fontSize: 15)),
            TextSpan(
                text: widget.keyWord.signUp,
                style: TextStyle(
                    decoration: TextDecoration.underline,
                    color: widget.textColor ?? Color(0xFF0F2E48),
                    fontWeight: FontWeight.bold,
                    fontSize: 16)),
          ]),
        ),
      ),
      onTap: () {
        Navigator.of(context).push(
            MaterialPageRoute(builder: (_buildContext) => widget.widgetSignUp));
      },
    );
  }

  Widget buildExploreApp(BuildContext context) {
    return (widget.isExploreApp == null || widget.isExploreApp == false)
        ? SizedBox()
        : GestureDetector(
            onTap: widget.functionExploreApp,
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
                            color: widget.textColor ?? Color(0xFF0F2E48),
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
              color: widget.textColor ?? Color(0xFF0F2E48),
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
              package: (tlm.logo.contains('assets/images_login_fresh_34_/'))
                  ? 'login_fresh'
                  : null,
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
