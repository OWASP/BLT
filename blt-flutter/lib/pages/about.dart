import 'package:bugheist/constants/about_constants.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AboutPage extends StatelessWidget {
  const AboutPage({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: Icon(
            Icons.arrow_back_ios_new_rounded,
          ),
          onPressed: () {
            Navigator.of(context).pop();
          },
        ),
        title: Text("About Us"),
        backgroundColor: Color(0xFFDC4654),
      ),
      body: SingleChildScrollView(
        padding: EdgeInsets.symmetric(horizontal: 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Container(
              padding: EdgeInsets.fromLTRB(0, 36, 0, 24),
              child: Image.asset(
                'assets/bugheist_logo.png',
                width: 169.42,
              ),
            ),
            Container(
              padding: EdgeInsets.fromLTRB(0, 0, 0, 24),
              child: Text(
                aboutBugHeist,
                style: GoogleFonts.aBeeZee(
                  textStyle: TextStyle(
                    color: Color(0xFF737373),
                  ),
                ),
              ),
            ),
            Container(
              padding: EdgeInsets.fromLTRB(0, 0, 0, 16),
              alignment: Alignment.centerLeft,
              child: Text(
                "What's in it for you?",
                style: GoogleFonts.ubuntu(
                  textStyle: TextStyle(
                    color: Color(0xFFDC4654),
                    fontSize: 20,
                  ),
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            Container(
              padding: EdgeInsets.fromLTRB(0, 0, 0, 16),
              child: Text(
                forYou,
                style: GoogleFonts.aBeeZee(
                  textStyle: TextStyle(
                    color: Color(0xFF737373),
                  ),
                ),
              ),
            ),
            Container(
              padding: EdgeInsets.fromLTRB(0, 0, 0, 16),
              alignment: Alignment.centerLeft,
              child: Text(
                "How it works?",
                style: GoogleFonts.ubuntu(
                  textStyle: TextStyle(
                    color: Color(0xFFDC4654),
                    fontSize: 17.5,
                  ),
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            Container(
              padding: EdgeInsets.fromLTRB(0, 0, 0, 12),
              alignment: Alignment.centerLeft,
              child: Text(
                "For Testers",
                style: GoogleFonts.ubuntu(
                  textStyle: TextStyle(
                    color: Color(0xFF737373),
                    fontSize: 15,
                  ),
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            Container(
              padding: EdgeInsets.fromLTRB(0, 0, 0, 16),
              child: Text(
                forTesters,
                style: GoogleFonts.aBeeZee(
                  textStyle: TextStyle(
                    color: Color(0xFF737373),
                  ),
                ),
              ),
            ),
            Container(
              padding: EdgeInsets.fromLTRB(0, 0, 0, 12),
              alignment: Alignment.centerLeft,
              child: Text(
                "For Organizations",
                style: GoogleFonts.ubuntu(
                  textStyle: TextStyle(
                    color: Color(0xFF737373),
                    fontSize: 15,
                  ),
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            Container(
              padding: EdgeInsets.fromLTRB(0, 0, 0, 36),
              child: Text(
                forOrgs,
                style: GoogleFonts.aBeeZee(
                  textStyle: TextStyle(
                    color: Color(0xFF737373),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
