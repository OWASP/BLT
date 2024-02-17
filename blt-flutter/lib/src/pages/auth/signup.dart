import 'package:blt/src/util/api/auth_api.dart';
import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';

import '../../routes/routing.dart';

/// The signup page for the app.
class SignUpPage extends StatefulWidget {
  const SignUpPage({Key? key}) : super(key: key);

  @override
  State<SignUpPage> createState() => _SignUpPageState();
}

class _SignUpPageState extends State<SignUpPage> {
  @override
  Widget build(BuildContext context) {
    final Size size = MediaQuery.of(context).size;
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: Icon(
            Icons.arrow_back_ios_new_rounded,
            color: Colors.white,
          ),
          onPressed: () {
            Navigator.of(context).pop();
          },
        ),
      ),
      backgroundColor: Colors.transparent,
      extendBodyBehindAppBar: true,
      body: Stack(
        children: [
          Container(
            width: size.width,
            height: size.height,
            color: Color(0xFFDC4654),
            child: Column(
              children: [
                SizedBox(
                  width: size.width,
                  height: size.height * 0.35,
                  child: Padding(
                    padding: EdgeInsets.symmetric(
                      horizontal: 0.125 * size.width,
                      vertical: 0.085 * size.height,
                    ),
                    child: Center(
                      child: SvgPicture.asset(
                        'assets/logo_white.svg',
                        fit: BoxFit.contain,
                        height: 192.0,
                      ),
                    ),
                  ),
                ),
                SizedBox(
                  width: size.width,
                  height: size.height * 0.65,
                ),
              ],
            ),
          ),
          Positioned(
            bottom: 0,
            child: Container(
              width: size.width,
              height: size.height * 0.65,
              decoration: BoxDecoration(
                color: Theme.of(context).canvasColor,
                boxShadow: [
                  BoxShadow(
                    spreadRadius: 10,
                    color: Colors.black.withOpacity(0.1),
                    blurRadius: 50,
                  )
                ],
                borderRadius: BorderRadius.only(
                  topLeft: Radius.circular(50),
                  topRight: Radius.circular(50.0),
                ),
              ),
              child: Center(
                child: SignUpForm(
                  size: size,
                ),
              ),
            ),
          )
        ],
      ),
    );
  }
}

class SignUpForm extends StatefulWidget {
  final Size size;
  const SignUpForm({
    Key? key,
    required this.size,
  }) : super(key: key);

  @override
  State<SignUpForm> createState() => _SignUpFormState();
}

class _SignUpFormState extends State<SignUpForm> {
  bool showPassword = false;
  bool isShowVisible = false;
  final _formKey = GlobalKey<FormState>();

  late TextEditingController _usernameController,
      _emailController,
      _passwordController,
      _cpasswordController;

  @override
  void initState() {
    super.initState();
    _usernameController = TextEditingController();
    _emailController = TextEditingController();
    _passwordController = TextEditingController();
    _cpasswordController = TextEditingController();
  }

  String? validateEmail(String? value) {
    RegExp regex = RegExp(
      r"^[a-zA-Z0-9.a-zA-Z0-9.!#$%&'*+-/=?^_`{|}~]+@[a-zA-Z0-9]+\.[a-zA-Z]+",
    );
    if (value == null || value.isEmpty || !regex.hasMatch(value))
      return AppLocalizations.of(context)!.validEmail;
    else
      return null;
  }

  @override
  Widget build(BuildContext context) {
    return Form(
      key: _formKey,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          SizedBox(
            width: 0.8 * widget.size.width,
            child: TextFormField(
              controller: _usernameController,
              validator: (value) {
                if (value == null || value.isEmpty) {
                  return AppLocalizations.of(context)!.requiredField;
                }
                return null;
              },
              decoration: InputDecoration(
                hintText: AppLocalizations.of(context)!.username,
                prefixIcon: Icon(Icons.person),
                filled: true,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10.0),
                ),
                fillColor: Colors.white.withOpacity(0.35),
              ),
            ),
          ),
          SizedBox(
            height: 0.025 * widget.size.height,
          ),
          SizedBox(
            width: 0.8 * widget.size.width,
            child: TextFormField(
              controller: _emailController,
              validator: validateEmail,
              decoration: InputDecoration(
                hintText: AppLocalizations.of(context)!.email,
                prefixIcon: Icon(Icons.mail),
                filled: true,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10.0),
                ),
                fillColor: Colors.white.withOpacity(0.35),
              ),
            ),
          ),
          SizedBox(
            height: 0.025 * widget.size.height,
          ),
          SizedBox(
            width: 0.8 * widget.size.width,
            child: TextFormField(
              controller: _passwordController,
              validator: (value) {
                if (value == null || value.length < 8) {
                  return AppLocalizations.of(context)!.requiredField;
                }
                return null;
              },
              onChanged: (val) {
                if (!val.isEmpty) {
                  setState(() {
                    isShowVisible = true;
                  });
                } else {
                  setState(() {
                    isShowVisible = false;
                  });
                }
              },
              decoration: InputDecoration(
                hintText: AppLocalizations.of(context)!.password,
                prefixIcon: Icon(Icons.key_rounded),
                filled: true,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10.0),
                  borderSide: BorderSide(
                    color: Color(0xFF737373),
                  ),
                ),
                fillColor: Colors.white.withOpacity(0.35),
              ),
              obscureText: !showPassword,
            ),
          ),
          SizedBox(
            height: 0.025 * widget.size.height,
          ),
          SizedBox(
            width: 0.8 * widget.size.width,
            child: TextFormField(
              controller: _cpasswordController,
              validator: (value) {
                if (value == null || value.isEmpty) {
                  return AppLocalizations.of(context)!.requiredField;
                } else {
                  if (_passwordController.text != _cpasswordController.text) {
                    return AppLocalizations.of(context)!.passwordsDoNotMatch;
                  }
                  return null;
                }
              },
              decoration: InputDecoration(
                hintText: AppLocalizations.of(context)!.confirmPassword,
                prefixIcon: Icon(Icons.password),
                filled: true,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10.0),
                  borderSide: BorderSide(
                    color: Color(0xFF737373),
                  ),
                ),
                fillColor: Colors.white.withOpacity(0.35),
              ),
              obscureText: !showPassword,
            ),
          ),
          SizedBox(
            height: 0.025 * widget.size.height,
          ),
          SizedBox(
            width: 0.8 * widget.size.width,
            height: 50,
            child: TextButton(
              onPressed: () async {
                if (_formKey.currentState!.validate()) {
                  await AuthApiClient.signup(
                    _usernameController.text,
                    _emailController.text,
                    _passwordController.text,
                    context,
                  );
                }
              },
              child: Text(
                AppLocalizations.of(context)!.signUp,
                style: GoogleFonts.ubuntu(
                  textStyle: TextStyle(
                    color: Colors.white,
                    fontSize: 17.5,
                  ),
                ),
              ),
              style: ButtonStyle(
                elevation: MaterialStateProperty.all(8),
                shadowColor: MaterialStateProperty.all(
                  Colors.black.withOpacity(0.5),
                ),
                shape: MaterialStateProperty.all<RoundedRectangleBorder>(
                  RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(15.0),
                  ),
                ),
                backgroundColor: MaterialStateProperty.all(
                  Color(0xFFDC4654),
                ),
              ),
            ),
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                AppLocalizations.of(context)!.existingUser,
              ),
              TextButton(
                onPressed: () {
                  Navigator.of(context).pushReplacementNamed(
                    RouteManager.loginPage,
                  );
                },
                child: Text(AppLocalizations.of(context)!.login),
              )
            ],
          )
        ],
      ),
    );
  }

  @override
  void dispose() {
    _usernameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _cpasswordController.dispose();
    super.dispose();
  }
}
