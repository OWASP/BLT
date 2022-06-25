import 'package:flutter/material.dart';

import '../../config/login_signup_structure.dart';
import '../../pages/login_signup/loading.dart';
import '../../routes/routing.dart';
import '../../util/validators.dart';
import 'package:bugheist/providers/auth.dart';
import 'package:provider/provider.dart';
import 'dart:async';
import 'package:bugheist/data/user.dart';
import 'package:bugheist/providers/user_provider.dart';
import 'package:bugheist/config/login_signup_structure.dart';

class LoginFreshUserAndPassword extends StatefulWidget {
  final Color backgroundColor;
  final String logo;
  final Color textColor;

  final bool isFooter;
  final Widget widgetFooter;

  final bool isResetPassword;
  final Widget widgetResetPassword;

  final bool isSignUp;
  final Widget signUp;

  final Function callLogin;

  final LoginFreshWords loginFreshWords;

  const LoginFreshUserAndPassword(
      {Key? key,
      required this.callLogin,
      required this.backgroundColor,
      required this.loginFreshWords,
      required this.logo,
      required this.isFooter,
      required this.widgetFooter,
      required this.isResetPassword,
      required this.widgetResetPassword,
      required this.isSignUp,
      required this.signUp,
      required this.textColor})
      : super(key: key);

  @override
  _LoginFreshUserAndPasswordState createState() =>
      _LoginFreshUserAndPasswordState();
}

class _LoginFreshUserAndPasswordState extends State<LoginFreshUserAndPassword> {
  TextEditingController _textEditingControllerPassword =
      TextEditingController();
  TextEditingController _textEditingControllerEmail = TextEditingController();
  TextEditingController _textEditingControllerUser = TextEditingController();

  final GlobalKey<FormState> formKey = new GlobalKey<FormState>();

  bool isNoVisiblePassword = true;

  bool isRequest = false;

  final focus = FocusNode();

  final bool isLoginRequest = false;

  LoginFreshWords loginFreshWords = LoginFreshWords();

  @override
  Widget build(BuildContext context) {
    loginFreshWords = LoginFreshWords();
    AuthProvider auth = Provider.of<AuthProvider>(context);
    return Scaffold(
      appBar: AppBar(
          iconTheme: IconThemeData(color: Colors.white),
          backgroundColor: widget.backgroundColor,
          centerTitle: true,
          elevation: 0,
          title: Text(
            this.loginFreshWords.login,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
                color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18),
          )),
      body: Stack(
        children: <Widget>[
          Align(
            alignment: Alignment.topCenter,
            child: Container(
              height: MediaQuery.of(context).size.height * 0.7,
              width: MediaQuery.of(context).size.width,
              color: widget.backgroundColor,
              child: Column(
                mainAxisSize: MainAxisSize.max,
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                crossAxisAlignment: CrossAxisAlignment.center,
                children: <Widget>[
                  Column(
                    children: [
                      Padding(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 50, vertical: 3),
                        child: Hero(
                          tag: 'hero-login',
                          child: Image.asset(
                            widget.logo,
                            fit: BoxFit.contain,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          Align(
            alignment: Alignment.bottomCenter,
            child: Container(
              height: MediaQuery.of(context).size.height * 0.7,
              width: MediaQuery.of(context).size.width,
              decoration: new BoxDecoration(
                  color: Color(0xFFF3F3F5),
                  borderRadius: new BorderRadius.only(
                    topLeft: const Radius.circular(50.0),
                    topRight: const Radius.circular(50.0),
                  )),
              child: buildBody(auth),
            ),
          ),
        ],
      ),
    );
  }

  Widget buildBody(AuthProvider auth) {
    return Form(
      key: formKey,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        crossAxisAlignment: CrossAxisAlignment.center,
        mainAxisSize: MainAxisSize.max,
        children: <Widget>[
          SizedBox(
            height: 0,
          ),
          Expanded(
            child: SingleChildScrollView(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                crossAxisAlignment: CrossAxisAlignment.center,
                mainAxisSize: MainAxisSize.max,
                children: <Widget>[
                  SizedBox(
                    height: 30,
                  ),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    child: TextFormField(
                        controller: this._textEditingControllerUser,
                        style: TextStyle(color: widget.textColor, fontSize: 14),
                        autofocus: false,
                        decoration: InputDecoration(
                            prefixIcon: Padding(
                              padding: const EdgeInsets.all(8.0),
                              child: Image.asset(
                                "assets/login_signup/icon_user.png",
                                width: 15,
                                height: 15,
                              ),
                            ),
                            enabledBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(25),
                                borderSide:
                                    BorderSide(color: Color(0xFFAAB5C3))),
                            filled: true,
                            fillColor: Color(0xFFF3F3F5),
                            focusColor: Color(0xFFF3F3F5),
                            focusedBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(25),
                                borderSide:
                                    BorderSide(color: Color(0xFFAAB5C3))),
                            border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(25),
                                borderSide:
                                    BorderSide(color: widget.backgroundColor)),
                            hintText: this.loginFreshWords.hintLoginUser)),
                  ),
                  Padding(
                    padding:
                        const EdgeInsets.symmetric(vertical: 5, horizontal: 20),
                    child: TextFormField(
                        controller: this._textEditingControllerEmail,
                        keyboardType: TextInputType.emailAddress,
                        style: TextStyle(color: widget.textColor, fontSize: 14),
                        autofocus: false,
                        validator: validateEmail,
                        decoration: InputDecoration(
                            prefixIcon: Padding(
                              padding: const EdgeInsets.all(8.0),
                              child: Image.asset(
                                "assets/login_signup/icon_email.png",
                                width: 15,
                                height: 15,
                              ),
                            ),
                            enabledBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(25),
                                borderSide:
                                    BorderSide(color: Color(0xFFAAB5C3))),
                            filled: true,
                            fillColor: Color(0xFFF3F3F5),
                            focusColor: Color(0xFFF3F3F5),
                            focusedBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(25),
                                borderSide:
                                    BorderSide(color: Color(0xFFAAB5C3))),
                            border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(25),
                                borderSide:
                                    BorderSide(color: widget.backgroundColor)),
                            hintText: this.loginFreshWords.hintLoginEmail)),
                  ),
                  Padding(
                    padding:
                        const EdgeInsets.symmetric(vertical: 5, horizontal: 20),
                    child: TextFormField(
                        focusNode: focus,
                        controller: this._textEditingControllerPassword,
                        obscureText: this.isNoVisiblePassword,
                        style: TextStyle(color: widget.textColor, fontSize: 14),
                        decoration: InputDecoration(
                            prefixIcon: Padding(
                              padding: const EdgeInsets.all(8.0),
                              child: Image.asset(
                                "assets/login_signup/icon_password.png",
                                width: 15,
                                height: 15,
                              ),
                            ),
                            suffixIcon: GestureDetector(
                                onTap: () {
                                  setState(() {
                                    if (this.isNoVisiblePassword)
                                      this.isNoVisiblePassword = false;
                                    else
                                      this.isNoVisiblePassword = true;
                                  });
                                },
                                child: (this.isNoVisiblePassword)
                                    ? Padding(
                                        padding: const EdgeInsets.all(8.0),
                                        child: Image.asset(
                                          "assets/login_signup/icon_eye_close.png",
                                          width: 15,
                                          height: 15,
                                        ),
                                      )
                                    : Padding(
                                        padding: const EdgeInsets.all(8.0),
                                        child: Image.asset(
                                          "assets/login_signup/icon_eye_open.png",
                                          width: 15,
                                          height: 15,
                                        ),
                                      )),
                            enabledBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(25),
                                borderSide:
                                    BorderSide(color: Color(0xFFAAB5C3))),
                            filled: true,
                            fillColor: Color(0xFFF3F3F5),
                            focusColor: Color(0xFFF3F3F5),
                            focusedBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(25),
                                borderSide:
                                    BorderSide(color: Color(0xFFAAB5C3))),
                            border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(25),
                                borderSide:
                                    BorderSide(color: widget.backgroundColor)),
                            hintText: this.loginFreshWords.hintLoginPassword)),
                  ),
                  (this.isRequest)
                      ? Padding(
                          padding: const EdgeInsets.all(8.0),
                          child: LoadingLoginFresh(
                            textLoading: this.loginFreshWords.textLoading,
                            colorText: widget.textColor,
                            backgroundColor: widget.backgroundColor,
                            elevation: 0,
                          ),
                        )
                      : GestureDetector(
                          onTap: () {
                            var form = formKey.currentState;
                            if (form != null && form.validate()) {
                              final user = this._textEditingControllerUser.text;
                              final email =
                                  this._textEditingControllerEmail.text;
                              final password =
                                  this._textEditingControllerPassword.text;
                              final Future<Map<String, dynamic>>
                                  successfulMessage =
                                  auth.login(user, password, email);

                              successfulMessage.then((response) {
                                if (response['status']) {
                                  User user = response['user'];
                                  Provider.of<UserProvider>(context,
                                          listen: false)
                                      .setUser(user);
                                  Navigator.of(context).pushNamed(
                                    RouteManager.homePage,
                                  );
                                } else {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text(response['message'][0]),
                                    ),
                                  );
                                }
                              });
                              widget.callLogin(
                                context,
                                setIsRequest,
                              );
                            } else {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(
                                  content: Text("Invalid Form"),
                                ),
                              );
                            }
                          },
                          child: SizedBox(
                              height: MediaQuery.of(context).size.height * 0.07,
                              width: MediaQuery.of(context).size.width * 0.7,
                              child: Card(
                                  elevation: 10,
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(40),
                                  ),
                                  color: widget.backgroundColor,
                                  child: Padding(
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 10),
                                    child: Center(
                                        child: Text(
                                      this.loginFreshWords.login,
                                      style: TextStyle(
                                          color: Colors.white,
                                          fontSize: 15,
                                          fontWeight: FontWeight.bold),
                                    )),
                                  ))),
                        ),
                  widget.isResetPassword == false
                      ? SizedBox()
                      : GestureDetector(
                          child: Padding(
                            padding: const EdgeInsets.only(
                                top: 25, left: 10, right: 10),
                            child: RichText(
                              textAlign: TextAlign.center,
                              text: TextSpan(children: [
                                TextSpan(
                                    text: '',
                                    style: TextStyle(
                                        color: widget.textColor,
                                        fontWeight: FontWeight.normal,
                                        fontSize: 15)),
                                TextSpan(
                                    text: this.loginFreshWords.recoverPassword,
                                    style: TextStyle(
                                        decoration: TextDecoration.underline,
                                        color: widget.textColor,
                                        fontWeight: FontWeight.bold,
                                        fontSize: 16)),
                              ]),
                            ),
                          ),
                          onTap: () {
                            Navigator.of(context).push(MaterialPageRoute(
                              builder: (context) => widget.widgetResetPassword,
                            ));
                          },
                        ),
                  GestureDetector(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                          vertical: 15, horizontal: 10),
                      child: RichText(
                        textAlign: TextAlign.center,
                        text: TextSpan(children: [
                          TextSpan(
                              text: this.loginFreshWords.notAccount + ' \n',
                              style: TextStyle(
                                  color: widget.textColor,
                                  fontWeight: FontWeight.normal,
                                  fontSize: 15)),
                          TextSpan(
                              text: this.loginFreshWords.signUp,
                              style: TextStyle(
                                  decoration: TextDecoration.underline,
                                  color: widget.textColor,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 16)),
                        ]),
                      ),
                    ),
                    onTap: () {
                      Navigator.of(context).push(MaterialPageRoute(
                          builder: (_buildContext) => widget.signUp));
                    },
                  ),
                ],
              ),
            ),
          ),
          Align(
            alignment: Alignment.bottomCenter,
            child: widget.isFooter == false ? SizedBox() : widget.widgetFooter,
          ),
        ],
      ),
    );
  }

  void setIsRequest(bool isRequest) {
    setState(() {
      this.isRequest = isRequest;
    });
  }
}
