import 'package:blt/src/pages/pages_import.dart';

/// This page is thrown in case when a Navigation exception occurs.
class ErrorPage extends StatelessWidget {
  const ErrorPage({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final Size size = MediaQuery.of(context).size;
    return Scaffold(
      body: Container(
        width: size.width,
        height: size.height,
        padding: EdgeInsets.symmetric(horizontal: 20),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              AppLocalizations.of(context)!.error,
              style: GoogleFonts.aBeeZee(
                textStyle: TextStyle(
                  color: Color(0xFFDC4654),
                  fontWeight: FontWeight.bold,
                  fontSize: 30,
                ),
              ),
            ),
            SizedBox(
              height: 16,
            ),
            SvgPicture.asset("assets/pest_control.svg"),
            SizedBox(
              height: 16,
            ),
            Text(
              AppLocalizations.of(context)!.yikes,
              style: GoogleFonts.aBeeZee(
                textStyle: TextStyle(
                  color: Color(0xFF737373),
                  fontWeight: FontWeight.bold,
                  fontSize: 20,
                ),
              ),
            ),
            SizedBox(
              height: 12,
            ),
            Text(
              "${AppLocalizations.of(context)!.foundBugOnBLT}\n${AppLocalizations.of(context)!.reportItOrGoHome}",
              style: GoogleFonts.aBeeZee(
                textStyle: TextStyle(
                  color: Color(0xFF737373),
                ),
              ),
            ),
            SizedBox(
              height: 20,
            ),
            Container(
              width: size.width,
              height: 50,
              child: TextButton(
                child: Text(
                  AppLocalizations.of(context)!.addIssue,
                  style: GoogleFonts.ubuntu(
                    textStyle: TextStyle(
                      color: Colors.white,
                      fontSize: 20,
                    ),
                  ),
                ),
                style: ButtonStyle(
                  shape: WidgetStateProperty.all<RoundedRectangleBorder>(
                    RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8.0),
                    ),
                  ),
                  backgroundColor: WidgetStateProperty.all(
                    Color(0xFFDC4654),
                  ),
                ),
                onPressed: () {
                  Navigator.pushNamed(
                    context,
                    RouteManager.homePage,
                    arguments: 1,
                  );
                },
              ),
            ),
            SizedBox(
              height: 20,
            ),
            Container(
              width: size.width,
              height: 50,
              child: TextButton(
                child: Text(
                  AppLocalizations.of(context)!.home,
                  style: GoogleFonts.ubuntu(
                    textStyle: TextStyle(
                      color: Color(0xFFDC4654),
                      fontSize: 20,
                    ),
                  ),
                ),
                style: ButtonStyle(
                  shape: WidgetStateProperty.all<RoundedRectangleBorder>(
                    RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8.0),
                      side: BorderSide(color: Colors.red),
                    ),
                  ),
                  backgroundColor: WidgetStateProperty.all(
                    Colors.white,
                  ),
                ),
                onPressed: () {
                  Navigator.pushNamed(
                    context,
                    RouteManager.homePage,
                    arguments: 0,
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
