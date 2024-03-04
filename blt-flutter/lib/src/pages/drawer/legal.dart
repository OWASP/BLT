import 'package:flutter/material.dart';
import '../pages_import.dart';

/// Page stating the legal Terms and Conditions and Privacy
/// Policy applying to the BLT project.
class LegalPage extends StatelessWidget {
  const LegalPage({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
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
        title: Text(AppLocalizations.of(context)!.termsOfService),
        backgroundColor:
            isDarkMode ? Color.fromRGBO(58, 21, 31, 1) : Color(0xFFDC4654),
      ),
      body: SingleChildScrollView(
        padding: EdgeInsets.symmetric(horizontal: 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Container(
              padding: EdgeInsets.fromLTRB(0, 36, 0, 24),
              child: SvgPicture.asset(
                'assets/blt_logo_dark.svg',
                width: 169.42,
              ),
            ),
            Container(
              padding: EdgeInsets.fromLTRB(0, 0, 0, 24),
              child: Text(
                AppLocalizations.of(context)!.byUsingBLTAppAgree,
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
                AppLocalizations.of(context)!.termsAndConditions,
                style: GoogleFonts.ubuntu(
                  textStyle: TextStyle(
                    color: Color(0xFFDC4654),
                    fontSize: 15,
                  ),
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            Container(
              height: 800,
              padding: EdgeInsets.fromLTRB(10, 0, 10, 24),
              child: FutureBuilder(
                  future: rootBundle.loadString("assets/TnC.md"),
                  builder:
                      (BuildContext context, AsyncSnapshot<String> snapshot) {
                    if (snapshot.hasData) {
                      return Markdown(
                        physics: const NeverScrollableScrollPhysics(),
                        data: snapshot.data!,
                        padding: EdgeInsets.all(0),
                        styleSheet: MarkdownStyleSheet.fromTheme(
                          ThemeData(
                            textTheme: TextTheme(
                              bodyMedium: GoogleFonts.aBeeZee(
                                textStyle: TextStyle(
                                  fontSize: 12,
                                  color: Color(0xFF737373),
                                ),
                              ),
                            ),
                          ),
                        ),
                      );
                    }

                    return Center(
                      child: CircularProgressIndicator(),
                    );
                  }),
            ),
            Container(
              padding: EdgeInsets.fromLTRB(0, 0, 0, 16),
              alignment: Alignment.centerLeft,
              child: Text(
                AppLocalizations.of(context)!.privacyPolicy,
                style: GoogleFonts.ubuntu(
                  textStyle: TextStyle(
                    color: Color(0xFFDC4654),
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
            Container(
              height: 800,
              padding: EdgeInsets.fromLTRB(0, 0, 0, 36),
              child: FutureBuilder(
                  future: rootBundle.loadString("assets/privacy_policy.md"),
                  builder:
                      (BuildContext context, AsyncSnapshot<String> snapshot) {
                    if (snapshot.hasData) {
                      return Markdown(
                        physics: const NeverScrollableScrollPhysics(),
                        data: snapshot.data!,
                        padding: EdgeInsets.all(0),
                        styleSheet: MarkdownStyleSheet.fromTheme(
                          ThemeData(
                            textTheme: TextTheme(
                              bodyMedium: GoogleFonts.aBeeZee(
                                textStyle: TextStyle(
                                  fontSize: 12,
                                  color: Color(0xFF737373),
                                ),
                              ),
                            ),
                          ),
                        ),
                      );
                    }

                    return Center(
                      child: CircularProgressIndicator(),
                    );
                  }),
            ),
          ],
        ),
      ),
    );
  }
}
