import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class ForgotPasswordPage extends StatefulWidget {
  const ForgotPasswordPage({Key? key}) : super(key: key);

  @override
  State<ForgotPasswordPage> createState() => _ForgotPasswordPageState();
}

class _ForgotPasswordPageState extends State<ForgotPasswordPage> {
  @override
  Widget build(BuildContext context) {
    final Size size = MediaQuery.of(context).size;
    return Scaffold(
      backgroundColor: Colors.transparent,
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
                      child: Image.asset(
                        'assets/logo_white.png',
                        fit: BoxFit.contain,
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
                        "On entering the email, you'll receive an email to update password. Available only for accounts created with username and password",
                        textAlign: TextAlign.center,
                      ),
                    ),
                    SizedBox(
                      height: 0.025 * size.height,
                    ),
                    SizedBox(
                      width: 0.8 * size.width,
                      child: TextFormField(
                        decoration: InputDecoration(
                          hintText: "Registered Email",
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
                        onPressed: () {},
                        child: Text(
                          "Login",
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
                          shape:
                              MaterialStateProperty.all<RoundedRectangleBorder>(
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
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
