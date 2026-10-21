import 'package:blt/src/pages/pages_import.dart';
import 'package:blt/src/util/brand.dart';

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
              style: BLTFonts.system(
                textStyle: TextStyle(
                  color: BLTColors.primary,
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
              style: BLTFonts.system(
                textStyle: TextStyle(
                  color: BLTColors.textMuted,
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
              style: BLTFonts.system(
                textStyle: TextStyle(
                  color: BLTColors.textMuted,
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
                  style: BLTFonts.system(
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
                    BLTColors.primary,
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
                  style: BLTFonts.system(
                    textStyle: TextStyle(
                      color: BLTColors.primary,
                      fontSize: 20,
                    ),
                  ),
                ),
                style: ButtonStyle(
                  shape: WidgetStateProperty.all<RoundedRectangleBorder>(
                    RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8.0),
                      side: BorderSide(color: BLTColors.primary),
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
