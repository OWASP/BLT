import 'package:flutter/material.dart';

import 'package:bugheist/config/login_signup_structure.dart';
import 'package:bugheist/pages/login_signup/loading.dart';

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

  LoginFreshUserAndPassword(
      {@required this.callLogin,
      this.backgroundColor,
      this.loginFreshWords,
      this.logo,
      this.isFooter,
      this.widgetFooter,
      this.isResetPassword,
      this.widgetResetPassword,
      this.isSignUp,
      this.signUp,
      this.textColor});

  @override
  _LoginFreshUserAndPasswordState createState() =>
      _LoginFreshUserAndPasswordState();
}

class _LoginFreshUserAndPasswordState extends State<LoginFreshUserAndPassword> {
  TextEditingController _textEditingControllerPassword =
      TextEditingController();
  TextEditingController _textEditingControllerUser = TextEditingController();

  bool isNoVisiblePassword = true;

  bool isRequest = false;

  final focus = FocusNode();

  final bool isLoginRequest = false;

  LoginFreshWords loginFreshWords;

  @override
  Widget build(BuildContext context) {
    loginFreshWords = (widget.loginFreshWords == null)
        ? LoginFreshWords()
        : widget.loginFreshWords;

    return Scaffold(
      appBar: AppBar(
          iconTheme: IconThemeData(color: Colors.white),
          backgroundColor: widget.backgroundColor ?? Color(0xFFE7004C),
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
              color: widget.backgroundColor ?? Color(0xFFE7004C),
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
              child: buildBody(),
            ),
          ),
        ],
      ),
    );
  }

  Widget buildBody() {
    return Column(
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
                  child: TextField(
                      controller: this._textEditingControllerUser,
                      keyboardType: TextInputType.emailAddress,
                      style: TextStyle(
                          color: widget.textColor ?? Color(0xFF0F2E48),
                          fontSize: 14),
                      autofocus: false,
                      onSubmitted: (v) {
                        FocusScope.of(context).requestFocus(focus);
                      },
                      decoration: InputDecoration(
                          prefixIcon: Padding(
                            padding: const EdgeInsets.all(8.0),
                            child: Image.asset(
                              "assets/images_login_fresh_34_/icon_user.png",
                              package: 'login_fresh',
                              width: 15,
                              height: 15,
                            ),
                          ),
                          enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(25),
                              borderSide: BorderSide(color: Color(0xFFAAB5C3))),
                          filled: true,
                          fillColor: Color(0xFFF3F3F5),
                          focusColor: Color(0xFFF3F3F5),
                          focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(25),
                              borderSide: BorderSide(color: Color(0xFFAAB5C3))),
                          border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(25),
                              borderSide: BorderSide(
                                  color: widget.backgroundColor ??
                                      Color(0xFFE7004C))),
                          hintText: this.loginFreshWords.hintLoginUser)),
                ),
                Padding(
                  padding:
                      const EdgeInsets.symmetric(vertical: 5, horizontal: 20),
                  child: TextField(
                      focusNode: focus,
                      controller: this._textEditingControllerPassword,
                      obscureText: this.isNoVisiblePassword,
                      style: TextStyle(
                          color: widget.textColor ?? Color(0xFF0F2E48),
                          fontSize: 14),
                      onSubmitted: (value) {
                        widget.callLogin(
                            context,
                            setIsRequest,
                            this._textEditingControllerUser.text,
                            this._textEditingControllerPassword.text);
                      },
                      decoration: InputDecoration(
                          prefixIcon: Padding(
                            padding: const EdgeInsets.all(8.0),
                            child: Image.asset(
                              "assets/images_login_fresh_34_/icon_password.png",
                              package: 'login_fresh',
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
                                        "assets/images_login_fresh_34_/icon_eye_close.png",
                                        package: 'login_fresh',
                                        width: 15,
                                        height: 15,
                                      ),
                                    )
                                  : Padding(
                                      padding: const EdgeInsets.all(8.0),
                                      child: Image.asset(
                                        "assets/images_login_fresh_34_/icon_eye_open.png",
                                        package: 'login_fresh',
                                        width: 15,
                                        height: 15,
                                      ),
                                    )),
                          enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(25),
                              borderSide: BorderSide(color: Color(0xFFAAB5C3))),
                          filled: true,
                          fillColor: Color(0xFFF3F3F5),
                          focusColor: Color(0xFFF3F3F5),
                          focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(25),
                              borderSide: BorderSide(color: Color(0xFFAAB5C3))),
                          border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(25),
                              borderSide: BorderSide(
                                  color: widget.backgroundColor ??
                                      Color(0xFFE7004C))),
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
                          widget.callLogin(
                              context,
                              setIsRequest,
                              this._textEditingControllerUser.text,
                              this._textEditingControllerPassword.text);
                        },
                        child: SizedBox(
                            height: MediaQuery.of(context).size.height * 0.07,
                            width: MediaQuery.of(context).size.width * 0.7,
                            child: Card(
                                elevation: 10,
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(40),
                                ),
                                color:
                                    widget.backgroundColor ?? Color(0xFFE7004C),
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
                (widget.isResetPassword == null ||
                        widget.isResetPassword == false)
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
                                      color:
                                          widget.textColor ?? Color(0xFF0F2E48),
                                      fontWeight: FontWeight.normal,
                                      fontSize: 15)),
                              TextSpan(
                                  text: this.loginFreshWords.recoverPassword,
                                  style: TextStyle(
                                      decoration: TextDecoration.underline,
                                      color:
                                          widget.textColor ?? Color(0xFF0F2E48),
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
                                color: widget.textColor ?? Color(0xFF0F2E48),
                                fontWeight: FontWeight.normal,
                                fontSize: 15)),
                        TextSpan(
                            text: this.loginFreshWords.signUp,
                            style: TextStyle(
                                decoration: TextDecoration.underline,
                                color: widget.textColor ?? Color(0xFF0F2E48),
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
          child: (widget.isFooter == null || widget.isFooter == false)
              ? SizedBox()
              : widget.widgetFooter,
        ),
      ],
    );
  }

  void setIsRequest(bool isRequest) {
    setState(() {
      this.isRequest = isRequest;
    });
  }
}
