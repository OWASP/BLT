import 'dart:async';

import 'package:flutter/material.dart';
import 'package:bugheist/pages/login_signup/loading.dart';
import 'package:bugheist/config/login_signup_structure.dart';
import 'package:bugheist/pages/login_signup/user_password.dart';
import 'package:bugheist/data/signup_model.dart';
import 'package:bugheist/util/validators.dart';
import '../../config/login_signup_structure.dart';
import '../../pages/login_signup/loading.dart';
import '../../util/validators.dart';
import 'package:bugheist/providers/auth.dart';
import 'package:provider/provider.dart';
import 'package:bugheist/pages/login_signup.dart';

class LoginFreshSignUp extends StatefulWidget {
  final Color backgroundColor;

  final Color textColor;

  final LoginFreshWords loginFreshWords;

  final Function funSignUp;

  final bool isFooter;

  final Widget widgetFooter;

  final String logo;

  LoginFreshSignUp(
      {required this.funSignUp,
      required this.logo,
      required this.isFooter,
      required this.widgetFooter,
      required this.textColor,
      required this.loginFreshWords,
      required this.backgroundColor});

  @override
  _LoginFreshSignUpState createState() => _LoginFreshSignUpState();
}

class _LoginFreshSignUpState extends State<LoginFreshSignUp> {
  SignUpModel signUpModel = SignUpModel();
  final GlobalKey<FormState> formKey = new GlobalKey<FormState>();

  bool isRequest = false;

  bool isNoVisiblePassword = true;

  LoginFreshWords loginFreshWords = LoginFreshWords();
  TextEditingController _textEditingControllerPassword =
      TextEditingController();
  TextEditingController _textEditingControllerRepeatPassword =
      TextEditingController();
  TextEditingController _textEditingControllerEmail = TextEditingController();
  TextEditingController _textEditingControllerUser = TextEditingController();
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
            this.loginFreshWords.signUp,
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
          Expanded(
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Padding(
                    padding: const EdgeInsets.only(
                        bottom: 5, left: 20, right: 20, top: 20),
                    child: TextFormField(
                        controller: this._textEditingControllerUser,
                        onChanged: (String value) {
                          this.signUpModel.username = value;
                        },
                        style: TextStyle(color: widget.textColor, fontSize: 14),
                        autofocus: false,
                        decoration: InputDecoration(
                            enabledBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(15),
                                borderSide:
                                    BorderSide(color: Color(0xFFAAB5C3))),
                            filled: true,
                            fillColor: Color(0xFFF3F3F5),
                            focusColor: Color(0xFFF3F3F5),
                            focusedBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(15),
                                borderSide:
                                    BorderSide(color: Color(0xFFAAB5C3))),
                            border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(15),
                                borderSide:
                                    BorderSide(color: widget.backgroundColor)),
                            hintText: this.loginFreshWords.hintLoginUser)),
                  ),
                  Padding(
                    padding: const EdgeInsets.only(
                        bottom: 5, left: 20, right: 20, top: 20),
                    child: TextFormField(
                      validator: validateEmail,
                      controller: this._textEditingControllerEmail,
                      onChanged: (String value) {
                        this.signUpModel.email = value;
                      },
                      keyboardType: TextInputType.emailAddress,
                      style: TextStyle(color: widget.textColor, fontSize: 14),
                      autofocus: false,
                      decoration: InputDecoration(
                          enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(15),
                              borderSide: BorderSide(color: Color(0xFFAAB5C3))),
                          filled: true,
                          fillColor: Color(0xFFF3F3F5),
                          focusColor: Color(0xFFF3F3F5),
                          focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(15),
                              borderSide: BorderSide(color: Color(0xFFAAB5C3))),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(15),
                            borderSide:
                                BorderSide(color: widget.backgroundColor),
                          ),
                          hintText: this.loginFreshWords.hintLoginEmail),
                    ),
                  ),
                  Padding(
                    padding:
                        const EdgeInsets.symmetric(vertical: 5, horizontal: 20),
                    child: TextFormField(
                        controller: this._textEditingControllerPassword,
                        onChanged: (String value) {
                          this.signUpModel.password = value;
                        },
                        obscureText: this.isNoVisiblePassword,
                        style: TextStyle(color: widget.textColor, fontSize: 14),
                        decoration: InputDecoration(
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
                                borderRadius: BorderRadius.circular(15),
                                borderSide:
                                    BorderSide(color: Color(0xFFAAB5C3))),
                            filled: true,
                            fillColor: Color(0xFFF3F3F5),
                            focusColor: Color(0xFFF3F3F5),
                            focusedBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(15),
                                borderSide:
                                    BorderSide(color: Color(0xFFAAB5C3))),
                            border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(15),
                                borderSide:
                                    BorderSide(color: widget.backgroundColor)),
                            hintText: this.loginFreshWords.hintLoginPassword)),
                  ),
                  Padding(
                    padding:
                        const EdgeInsets.symmetric(vertical: 5, horizontal: 20),
                    child: TextFormField(
                        controller: this._textEditingControllerRepeatPassword,
                        onChanged: (String value) {
                          this.signUpModel.repeatPassword = value;
                        },
                        obscureText: this.isNoVisiblePassword,
                        style: TextStyle(color: widget.textColor, fontSize: 14),
                        decoration: InputDecoration(
                            enabledBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(15),
                                borderSide:
                                    BorderSide(color: Color(0xFFAAB5C3))),
                            filled: true,
                            fillColor: Color(0xFFF3F3F5),
                            focusColor: Color(0xFFF3F3F5),
                            focusedBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(15),
                                borderSide:
                                    BorderSide(color: Color(0xFFAAB5C3))),
                            border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(15),
                                borderSide:
                                    BorderSide(color: widget.backgroundColor)),
                            hintText:
                                this.loginFreshWords.hintSignUpRepeatPassword)),
                  )
                ],
              ),
            ),
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
                      final email = this._textEditingControllerEmail.text;
                      final password = this._textEditingControllerPassword.text;
                      final repeatPassword =
                          this._textEditingControllerRepeatPassword.text;
                      final Future<Map<String, dynamic>> successfulMessage =
                          auth.register(email, user, password, repeatPassword);

                      successfulMessage.then((response) {
                        if (response['status']) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text(
                                  "Successfully Registered! Please Login in to continue"),
                            ),
                          );
                          LoginSignUpState _loginSignup =
                              new LoginSignUpState();
                          Navigator.of(context).push(
                            MaterialPageRoute(
                              builder: (_buildContext) => _loginSignup
                                  .widgetLoginFreshUserAndPassword(),
                            ),
                          );
                        } else {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text(response['message'][0]),
                            ),
                          );
                        }
                      });
                      widget.funSignUp(
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
                            padding: const EdgeInsets.symmetric(horizontal: 10),
                            child: Center(
                                child: Text(
                              this.loginFreshWords.signUp,
                              style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 15,
                                  fontWeight: FontWeight.bold),
                            )),
                          ))),
                ),
          widget.isFooter == false ? SizedBox() : widget.widgetFooter
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
