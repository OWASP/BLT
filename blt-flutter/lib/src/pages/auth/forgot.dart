import 'package:blt/src/pages/pages_import.dart';
import 'package:flutter/material.dart';

/// Page for initiating the process for recovering
/// a user's account password.
class ForgotPasswordPage extends StatefulWidget {
  const ForgotPasswordPage({Key? key}) : super(key: key);

  @override
  State<ForgotPasswordPage> createState() => _ForgotPasswordPageState();
}

class _ForgotPasswordPageState extends State<ForgotPasswordPage> {
  late TextEditingController _emailController;
  final _formKey = GlobalKey<FormState>();

  @override
  void initState() {
    super.initState();
    _emailController = TextEditingController();
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
                  height: size.height * 0.4,
                  child: Padding(
                    padding: EdgeInsets.symmetric(
                      horizontal: 0.15 * size.width,
                      vertical: 0.1 * size.height,
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
                  height: size.height * 0.6,
                ),
              ],
            ),
          ),
          Positioned(
            bottom: 0,
            child: Container(
              width: size.width,
              height: size.height * 0.6,
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
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Padding(
                      padding: EdgeInsets.symmetric(
                        horizontal: 0.1 * size.width,
                      ),
                      child: Text(
                        AppLocalizations.of(context)!.emailUpdatePasswordInfo,
                        textAlign: TextAlign.center,
                      ),
                    ),
                    Form(
                      key: _formKey,
                      child: Column(
                        children: [
                          SizedBox(
                            height: 0.025 * size.height,
                          ),
                          SizedBox(
                            width: 0.8 * size.width,
                            child: TextFormField(
                              controller: _emailController,
                              validator: validateEmail,
                              decoration: InputDecoration(
                                hintText: AppLocalizations.of(context)!
                                    .registeredEmail,
                                prefixIcon: Icon(Icons.mail),
                                filled: true,
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(10.0),
                                  borderSide: BorderSide(
                                    color: Color(0xFF737373),
                                  ),
                                ),
                                fillColor: Colors.white.withOpacity(0.35),
                              ),
                            ),
                          ),
                          SizedBox(
                            height: 0.025 * size.height,
                          ),
                          SizedBox(
                            width: 0.8 * size.width,
                            height: 50,
                            child: TextButton(
                              onPressed: () async {
                                if (_formKey.currentState!.validate()) {
                                  await AuthApiClient.resetPassword(
                                    _emailController.text,
                                    context,
                                  );
                                }
                              },
                              child: Text(
                                AppLocalizations.of(context)!.resetPassword,
                                style: GoogleFonts.ubuntu(
                                  textStyle: TextStyle(
                                    color: Colors.white,
                                    fontSize: 17.5,
                                  ),
                                ),
                              ),
                              style: ButtonStyle(
                                elevation: WidgetStateProperty.all(8),
                                shadowColor: WidgetStateProperty.all(
                                  Colors.black.withOpacity(0.5),
                                ),
                                shape: WidgetStateProperty.all<
                                    RoundedRectangleBorder>(
                                  RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(15.0),
                                  ),
                                ),
                                backgroundColor: WidgetStateProperty.all(
                                  Color(0xFFDC4654),
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _emailController.dispose();
    super.dispose();
  }
}
